"""
Fully commented Binance liquidations -> TA strategy bot (CCXT + TA-Lib)

Filename: binance_liquidations_ta_bot.py

What this file does (high level):
- Connects to Binance USD-M futures forceOrder streams to capture liquidation events.
- Stores liquidations to a CSV.
- Every loop it examines liquidations in the last 2 minutes and filters symbols that meet the "7 buys/sells" criteria.
- For qualifying symbols it fetches recent OHLCV via CCXT (Binance futures), computes Bollinger Bands via TA-Lib
  and applies the user's multi-step criteria (crosses and candle counts) to decide whether to create a 1x position.
- Orders are created via CCXT but default to dry_run=True to avoid placing live trades unexpectedly.

Requirements (install with pip):
- ccxt
- TA-Lib (binary + python wrapper) -> pip install TA-Lib (on some systems you must install the C library first)
- aiohttp, aiofiles, websockets, asyncio

CAUTION:
- This script includes order placement code. By default it is in dry-run mode. If you switch dry_run=False you
  will place live orders. Make sure to test on Binance testnet or paper accounts first.

"""

# standard library imports
import asyncio                 # asynchronous IO/event loop
import json                    # parse JSON payloads from websocket
import aiofiles                 # async file IO for CSV writes
import aiohttp                  # async HTTP for REST calls (fetch symbols)
import websockets               # websocket client to Binance streams
from datetime import datetime, timedelta  # timestamps and time window arithmetic
import math                     # math helpers

# third-party imports for trading and technicals
import ccxt                      # unified exchange API library
import talib                     # TA-Lib for indicators
import numpy as np               # numeric arrays used by TA-Lib

# --------------------------- Configuration ---------------------------
REST_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"   # Binance USD-M futures exchange info
WS_URL = "wss://fstream.binance.com/stream?streams="         # base websocket multi-stream URL
CSV_FILE = "binance_liquidations.csv"                        # output CSV for liquidations
MAX_STREAMS_PER_CONN = 100                                     # keep well under Binance 200 stream limit
LIQ_WINDOW_SECONDS = 120                                       # 2 minutes window for counting liquidations
MIN_LIQ_COUNT = 7                                              # threshold of buys/sells to consider pair
BOLL_TIMEPERIOD = 20                                           # Bollinger Bands timeperiod
BOLL_NBDEV = 1                                                 # Bollinger bandwidth (nbdevup/nbdevdn)
BOLL_LOOKBACK_CANDLES = 5                                      # search up to 5 candles backwards
BULL_BEAR_THRESHOLD = 0.8                                      # 80% of candles must be bullish/bearish
PROFIT_TARGET_PCT = 0.05                                       # 5% target
STOPLOSS_PCT = 0.03                                            # 3% stop
LEVERAGE = 1                                                   # 1x leverage
DRY_RUN = True                                                  # keep default as dry run to avoid live orders

# ----------- Exchange setup (CCXT) -------------
# Create a CCXT futures (binance) exchange instance. You can switch to 'binanceusdm' for some builds.
# NOTE: put your API keys in environment variables or a separate config file; do NOT hardcode keys here.
exchange = ccxt.binance({
    'enableRateLimit': True,
    # 'apiKey': os.getenv('BINANCE_API_KEY'),
    # 'secret': os.getenv('BINANCE_SECRET'),
    # If you want to use testnet: set 'options': {'defaultType': 'future'}, and set urls to testnet endpoints.
})
# Ensure fetchOHLCV uses futures margin if required. Many ccxt builds use 'binance' and set defaultType to 'future'.
exchange.options['defaultType'] = 'future'

# --------------------------- Utility helpers ---------------------------
async def fetch_symbols():
    """Fetch all USDⓈ-M perpetual symbols from Binance REST.

    Returns:
        list[str]: list of symbol strings like 'BTCUSDT'
    """
    # create an aiohttp session to fetch exchange info asynchronously
    async with aiohttp.ClientSession() as session:
        async with session.get(REST_URL) as resp:
            data = await resp.json()
            # filter symbols where contractType == 'PERPETUAL'
            return [s["symbol"] for s in data["symbols"] if s.get("contractType") == "PERPETUAL"]

async def write_csv_header():
    """Ensure CSV exists and has header row. If file missing create with header.
    Keeps the file asynchronous using aiofiles.
    """
    try:
        # try opening file for reading; if it exists we assume header present
        async with aiofiles.open(CSV_FILE, "r") as f:
            await f.readline()  # noop: will raise if file not exists
    except FileNotFoundError:
        # create file and write header line
        async with aiofiles.open(CSV_FILE, "w") as f:
            await f.write("timestamp,symbol,side,avg_price,filled_qty,usd_value,trade_time_ms\n")

async def append_to_csv(liq):
    """Append a liquidation dict into CSV asynchronously.

    Args:
        liq (dict): liquidation information with keys symbol, side, avg_price, filled_qty, usd_value, trade_time
    """
    # open file in append mode asynchronously
    async with aiofiles.open(CSV_FILE, "a") as f:
        # convert timestamp milliseconds to ISO UTC string
        ts = datetime.utcfromtimestamp(liq["trade_time"]/1000.0).isoformat()
        # build CSV row and write
        row = f'{ts},{liq["symbol"]},{liq["side"]},{liq["avg_price"]},{liq["filled_qty"]},{liq["usd_value"]},{liq["trade_time"]}\n'
        await f.write(row)

# --------------------------- Parser ---------------------------

def parse_force_order(msg_text):
    """Parse a raw websocket message from Binance 'forceOrder' stream into a liquidation dict.

    Binance forceOrder payload contains an 'o' object with liquidation details (ap, z, s, S, T...).
    We compute usd_value as avg_price * filled_qty and return structured dict. Returns None on failure.
    """
    try:
        data = json.loads(msg_text)           # parse JSON string to dict
        payload = data.get("data", {})      # 'data' contains the event payload
        o = payload.get("o", {})            # 'o' is the order object with liquidation info

        avg_price = float(o.get("ap", 0))   # average price 'ap'
        filled_qty = float(o.get("z", 0))   # filled quantity 'z'
        usd_value = avg_price * filled_qty   # compute USD value

        # return a consistent structure for downstream processing
        return {
            "symbol": o.get("s"),           # symbol, e.g. BTCUSDT
            "side": o.get("S"),             # side 'BUY' or 'SELL'
            "avg_price": avg_price,
            "filled_qty": filled_qty,
            "usd_value": usd_value,
            # trade_time: prefer 'T' (trade time); fallback to event time 'E' if missing
            "trade_time": int(o.get("T", payload.get("E", 0)))
        }
    except Exception as e:
        # on parse problems return None (caller will ignore)
        # optionally you can log e for debugging
        return None

# --------------------------- WebSocket handling ---------------------------

async def handle_ws_stream(symbols, liq_queue):
    """Open a websocket connection tracking the provided symbols and push parsed liquidations
    onto the supplied asyncio.Queue for downstream analysis.

    Args:
        symbols (list[str]): list of symbol strings, e.g. ['BTCUSDT', 'ETHUSDT']
        liq_queue (asyncio.Queue): queue to publish parsed liquidation dicts
    """
    # build stream names like 'btcusdt@forceOrder'
    stream_names = [f"{sym.lower()}@forceOrder" for sym in symbols]
    # join with '/' as required by Binance combined stream endpoint
    url = WS_URL + "/".join(stream_names)

    # keep retrying forever with a short backoff on error
    while True:
        try:
            # connect to websocket with ping settings
            async with websockets.connect(url, ping_interval=60, ping_timeout=10) as ws:
                print(f"[{datetime.utcnow().isoformat()}] Connected to {len(symbols)} symbols.")
                # listen to messages
                async for msg in ws:
                    # parse message to liquidation structure
                    liq = parse_force_order(msg)
                    if not liq:
                        continue

                    # print a human-friendly summary line
                    ts = datetime.utcfromtimestamp(liq["trade_time"]/1000.0).strftime("%H:%M:%S")
                    print(f"{ts} | {liq['symbol']} | {liq['side']} | {liq['filled_qty']:.3f} @ {liq['avg_price']:.3f} → ${liq['usd_value']:.0f}")

                    # write to CSV and publish into analysis queue concurrently
                    await append_to_csv(liq)
                    await liq_queue.put(liq)

        except Exception as e:
            # print error and attempt to reconnect with small delay
            print(f"[{datetime.utcnow().isoformat()}] Reconnecting due to: {e}")
            await asyncio.sleep(3)

# --------------------------- Strategy / Analysis ---------------------------

async def analyze_and_trade(liq_queue, dry_run=True):
    """Continuously read liquidations from queue and every cycle analyze those in the last
    LIQ_WINDOW_SECONDS for candidate symbols for LONG/SHORT based on the user's rules.

    This coroutine:
      - collects liqs into an in-memory buffer
      - periodically prunes buffer to keep only last 2 minutes
      - computes counts and filters symbols meeting first and second criteria
      - fetches OHLCV via CCXT and applies Bollinger criteria
      - if criteria met, calls place_order (respects dry_run)

    Args:
        liq_queue (asyncio.Queue): queue where websocket producers publish liquidations
        dry_run (bool): if True do not place real orders; just log the intended order
    """
    # buffer to hold recent liquidations; each item is a dict as returned by parse_force_order
    buffer = []

    # helper to prune old liquidations beyond the LIQ_WINDOW_SECONDS window
    def prune_buffer():
        cutoff = datetime.utcnow() - timedelta(seconds=LIQ_WINDOW_SECONDS)
        cutoff_ms = int(cutoff.timestamp() * 1000)
        # keep only those with trade_time >= cutoff_ms
        return [l for l in buffer if l["trade_time"] >= cutoff_ms]

    # main loop
    while True:
        try:
            # wait briefly for a new liquidation (timeout lets us run periodic analysis even with low traffic)
            liq = await asyncio.wait_for(liq_queue.get(), timeout=1.0)
            buffer.append(liq)
        except asyncio.TimeoutError:
            # no new liq in last second; continue to analysis step below
            pass

        # prune buffer to 2-minute window
        buffer = prune_buffer()

        # build counts per symbol for BUY and SELL within window
        counts = {}
        for l in buffer:
            sym = l['symbol']
            side = l['side']
            if sym not in counts:
                counts[sym] = {'BUY': 0, 'SELL': 0}
            counts[sym][side] += 1

        # process SHORT candidates: symbols with >= MIN_LIQ_COUNT SELLs and zero BUYs in window
        for sym, c in counts.items():
            # check SHORT first
            if c.get('SELL', 0) >= MIN_LIQ_COUNT and c.get('BUY', 0) == 0:
                # analyze technicals for opening a SHORT
                passed = await analyze_bollinger_and_decide(sym, side='SHORT')
                if passed:
                    await place_order(sym, side='sell', leverage=LEVERAGE, profit_target_pct=PROFIT_TARGET_PCT, stoploss_pct=STOPLOSS_PCT, dry_run=dry_run)

            # check LONG candidates: >= MIN_LIQ_COUNT BUYs and zero SELLs
            if c.get('BUY', 0) >= MIN_LIQ_COUNT and c.get('SELL', 0) == 0:
                passed = await analyze_bollinger_and_decide(sym, side='LONG')
                if passed:
                    await place_order(sym, side='buy', leverage=LEVERAGE, profit_target_pct=PROFIT_TARGET_PCT, stoploss_pct=STOPLOSS_PCT, dry_run=dry_run)

        # small sleep to yield control and avoid tight busy-loop
        await asyncio.sleep(0.01)

async def analyze_bollinger_and_decide(symbol, side='SHORT'):
    """Fetch OHLCV, compute Bollinger Bands and apply the user's three-part criteria.

    Returns True if the pair meets the criteria to open a position in the requested side.
    """
    try:
        # CCXT expects symbol format e.g. 'BTC/USDT' for spot; for futures many implementations
        # accept the same 'BTC/USDT' or 'BTC/USDT:USDT' depending on exchange. ccxt's binance future
        # often works with 'BTC/USDT'. We'll use symbol.replace('USDT','/USDT') to match ccxt format.
        ccxt_symbol = symbol.replace('USDT', '/USDT')

        # fetch at least (BOLL_TIMEPERIOD + BOLL_LOOKBACK_CANDLES + 5) candles to be safe
        limit = BOLL_TIMEPERIOD + BOLL_LOOKBACK_CANDLES + 10
        # timeframe we analyze - let's use 1m candles for responsiveness (you can change to '5m' or '15m')
        timeframe = '1m'

        # fetch OHLCV from exchange (open, high, low, close, volume)
        ohlcv = exchange.fetch_ohlcv(ccxt_symbol, timeframe=timeframe, limit=limit)
        if len(ohlcv) < BOLL_TIMEPERIOD + 1:
            print(f"Not enough candles for {symbol}. needed {BOLL_TIMEPERIOD+1}, got {len(ohlcv)}")
            return False

        # convert to numpy arrays for TA-Lib
        closes = np.array([c[4] for c in ohlcv], dtype=float)
        opens = np.array([c[1] for c in ohlcv], dtype=float)
        highs = np.array([c[2] for c in ohlcv], dtype=float)
        lows = np.array([c[3] for c in ohlcv], dtype=float)

        # compute Bollinger Bands using TA-Lib
        upper, middle, lower = talib.BBANDS(closes, timeperiod=BOLL_TIMEPERIOD, nbdevup=BOLL_NBDEV, nbdevdn=BOLL_NBDEV, matype=0)

        # We will search backwards up to BOLL_LOOKBACK_CANDLES for the specified cross
        # The cross rules differ for LONG vs SHORT. We'll search for an index where the cross happened.
        # cross from above to below (SHORT): price was above band on previous candle and then closed below
        # cross from below to above (LONG): price was below band and then closed above

        # determine the last index to consider (end of arrays)
        last_idx = len(closes) - 1

        # search window start index
        start_idx = max(0, last_idx - BOLL_LOOKBACK_CANDLES)

        cross_idx = None  # index where cross happened (the candle that closed crossing)

        # scan backwards to find the first cross occurrence within lookback
        for i in range(last_idx, start_idx - 1, -1):
            if side == 'SHORT':
                # we consider a cross of upper OR lower band from above to below
                # check previous candle index
                prev = i - 1
                if prev < 0:
                    continue
                # price relation to bands at prev and current close
                prev_close = closes[prev]
                cur_close = closes[i]
                # if prev_close was above upper or lower and current close is below that same band
                if (prev_close > upper[prev] and cur_close < upper[i]) or (prev_close > lower[prev] and cur_close < lower[i]):
                    cross_idx = i
                    break
            else:  # LONG
                prev = i - 1
                if prev < 0:
                    continue
                prev_close = closes[prev]
                cur_close = closes[i]
                # cross from below to above either band
                if (prev_close < upper[prev] and cur_close > upper[i]) or (prev_close < lower[prev] and cur_close > lower[i]):
                    cross_idx = i
                    break

        # if no cross found in the lookback window => fail
        if cross_idx is None:
            print(f"{symbol}: No qualifying cross found for {side} within {BOLL_LOOKBACK_CANDLES} candles")
            return False

        # check sub-criteria ii) there was a candle touching the relevant band in last BOLL_LOOKBACK_CANDLES
        # For SHORT: "A candle was above the lowerband or had contact with it" -> we interpret as at least one candle with low <= lower
        # For LONG: "A candle was above the upperband or had contact with it" -> at least one candle with high >= upper

        touched = False
        # examine candles from cross_idx going backwards up to BOLL_LOOKBACK_CANDLES
        examine_start = max(0, cross_idx - BOLL_LOOKBACK_CANDLES)
        examine_end = cross_idx  # inclusive
        for j in range(examine_start, examine_end + 1):
            if side == 'SHORT':
                if lows[j] <= lower[j]:
                    touched = True
                    break
            else:
                if highs[j] >= upper[j]:
                    touched = True
                    break

        if not touched:
            print(f"{symbol}: Touch/contact sub-criteria failed for {side}")
            return False

        # sub-criteria iii) At least 80% of candles from cross_idx onwards (to the most recent) are bearish (SHORT) or bullish (LONG)
        # define the slice from cross_idx to last_idx inclusive
        slice_opens = opens[cross_idx:last_idx + 1]
        slice_closes = closes[cross_idx:last_idx + 1]
        total = len(slice_closes)
        if total == 0:
            print(f"{symbol}: No candles after cross to evaluate bullish/bearish ratio")
            return False

        bearish_count = float(np.sum(slice_closes < slice_opens))
        bullish_count = float(np.sum(slice_closes > slice_opens))

        if side == 'SHORT':
            ratio = bearish_count / total
            if ratio < BULL_BEAR_THRESHOLD:
                print(f"{symbol}: Not enough bearish candles after cross ({ratio:.2f} < {BULL_BEAR_THRESHOLD})")
                return False
        else:
            ratio = bullish_count / total
            if ratio < BULL_BEAR_THRESHOLD:
                print(f"{symbol}: Not enough bullish candles after cross ({ratio:.2f} < {BULL_BEAR_THRESHOLD})")
                return False

        # if all sub-criteria passed, we consider the symbol qualified
        print(f"{symbol}: Passed all Bollinger criteria for {side} (cross_idx={cross_idx}, ratio={ratio:.2f})")
        return True

    except ccxt.BaseError as e:
        print(f"CCXT error fetching ohlcv for {symbol}: {e}")
        return False
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return False

# --------------------------- Order placement ---------------------------

async def place_order(symbol, side='buy', leverage=1, profit_target_pct=0.05, stoploss_pct=0.03, dry_run=True):
    """Place a futures order (1x) with profit target and stoploss. By default this is a dry-run.

    This function demonstrates the required steps: set leverage, open a market position, then create
a take-profit and stop-loss orders (either as OCO or separate orders depending on exchange capability).

    Arguments:
        symbol (str): symbol like 'BTCUSDT'
        side (str): 'buy' or 'sell'
        leverage (int): leverage to set on the symbol (1 means no leverage)
        profit_target_pct (float): target profit as fraction, e.g. 0.05 for 5%
        stoploss_pct (float): stoploss as fraction, e.g. 0.03 for 3%
        dry_run (bool): if True only log the intended orders, do not place
    """
    # simple protective prints for dry-run
    print(f"Preparing to place {side.upper()} position on {symbol} | leverage={leverage} | TP={profit_target_pct*100:.1f}% | SL={stoploss_pct*100:.1f}% | dry_run={dry_run}")

    if dry_run:
        # calculate hypothetical sizes and prices for logging
        # fetch ticker price for size estimate
        try:
            ticker = exchange.fetch_ticker(symbol.replace('USDT', '/USDT'))
            mark_price = float(ticker['last'])
        except Exception:
            mark_price = None

        print(f"DRY RUN: would open market {side} at ~{mark_price}")
        return

    # --- live mode: set leverage and create orders ---
    try:
        # set leverage on the symbol (Binance futures requires uppercase symbol)
        params = {'symbol': symbol, 'leverage': int(leverage)}
        # many ccxt builds expose set_leverage or set_margin. For binance futures set_leverage endpoint is 'fapiPrivate_post_leverage' in raw
        # but ccxt provides a convenience method:
        exchange.fapiPrivate_post_leverage(params)

        # fetch current price to calculate sizes
        ticker = exchange.fetch_ticker(symbol.replace('USDT', '/USDT'))
        price = float(ticker['last'])

        # TODO: size calculation depends on account balance and risk sizing. Here we place a placeholder 0.001 size.
        size = 0.001

        # open market position
        side_ccxt = 'sell' if side.lower() == 'sell' else 'buy'
        order = exchange.create_order(symbol.replace('USDT', '/USDT'), 'market', side_ccxt, size)
        print(f"Opened position: {order}")

        # calculate TP and SL prices (for long TP = price*(1+profit_target_pct), SL = price*(1-stoploss_pct))
        if side.lower() == 'buy':
            tp_price = price * (1 + profit_target_pct)
            sl_price = price * (1 - stoploss_pct)
        else:
            tp_price = price * (1 - profit_target_pct)
            sl_price = price * (1 + stoploss_pct)

        # create limit orders for TP and SL. Some exchanges support OCO; others require manual watch.
        # Example: create take profit limit order
        tp_order = exchange.create_order(symbol.replace('USDT', '/USDT'), 'limit', 'sell' if side=='buy' else 'buy', size, tp_price, {'reduceOnly': True})
        # Example: create stop loss order (stop market)
        sl_order = exchange.create_order(symbol.replace('USDT', '/USDT'), 'stop_market', 'sell' if side=='buy' else 'buy', size, None, {'stopPrice': sl_price, 'reduceOnly': True})

        print(f"TP order: {tp_order}")
        print(f"SL order: {sl_order}")

    except Exception as e:
        print(f"Error placing order for {symbol}: {e}")

# --------------------------- Main Entrypoint ---------------------------

async def main():
    """Main routine: fetch symbols, start websocket producers and a single analyzer consumer.
    This orchestrates multiple websocket connections if needed (groups), and an asyncio.Queue
    that gathers liquidations for the analyzer to consume.
    """
    # fetch all perpetual symbols (async)
    symbols = await fetch_symbols()

    # write CSV header if missing
    await write_csv_header()

    # create a queue for producers -> consumer
    liq_queue = asyncio.Queue()

    # split symbols into groups for multiple websocket connections
    groups = [symbols[i:i+MAX_STREAMS_PER_CONN] for i in range(0, len(symbols), MAX_STREAMS_PER_CONN)]

    print(f"Tracking {len(symbols)} symbols across {len(groups)} websocket connections...")

    # create producer tasks (one websocket handler per group)
    producer_tasks = [asyncio.create_task(handle_ws_stream(g, liq_queue)) for g in groups]

    # create single consumer task that analyzes and optionally places orders
    consumer_task = asyncio.create_task(analyze_and_trade(liq_queue, dry_run=DRY_RUN))

    # await all tasks (they are designed to run forever until cancelled)
    await asyncio.gather(*producer_tasks, consumer_task)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exited cleanly.")