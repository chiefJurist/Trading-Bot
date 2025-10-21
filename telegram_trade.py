"""
Fully commented Binance liquidations → TA strategy bot (CCXT + TA-Lib)

Filename: binance_liquidations_ta_bot.py

This script connects to Binance Futures WebSocket streams to monitor liquidation events, applies Bollinger Band-based analysis, and executes trades based on multi-step criteria.

Now includes:
✅ Uses $200 for every trade (TRADE_AMOUNT_USD)
✅ Checks if *any* position is open (across all symbols) before opening a new one
✅ Thoroughly commented for clarity

"""

# --------------------------- IMPORTS ---------------------------
import asyncio                    # For asynchronous I/O
import json                       # To parse JSON messages from Binance WebSocket
import aiofiles                   # For asynchronous file I/O (writing CSV)
import aiohttp                    # For async REST API requests
import websockets                 # For live Binance WebSocket streams
from datetime import datetime, timedelta
import numpy as np                 # For numeric arrays (required by TA-Lib)
import talib                      # Technical indicators library
import ccxt                       # For unified crypto exchange API

# --------------------------- CONFIGURATION ---------------------------
REST_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
WS_URL = "wss://fstream.binance.com/stream?streams="
CSV_FILE = "binance_liquidations.csv"

# Binance connection limits and strategy parameters
MAX_STREAMS_PER_CONN = 100             # Binance allows 200; stay safe with 100
LIQ_WINDOW_SECONDS = 120               # 2-minute liquidation window
MIN_LIQ_COUNT = 7                      # Minimum liquidations (same side) to trigger analysis
BOLL_TIMEPERIOD = 20                   # Bollinger Band period
BOLL_NBDEV = 1                         # Bollinger bandwidth
BOLL_LOOKBACK_CANDLES = 5              # Look back 5 candles for signal confirmation
BULL_BEAR_THRESHOLD = 0.8              # 80% of candles must confirm polarity
PROFIT_TARGET_PCT = 0.05               # 5% Take Profit
STOPLOSS_PCT = 0.03                    # 3% Stop Loss
LEVERAGE = 1                           # Default leverage
DRY_RUN = True                         # Keep True for safety during testing
TRADE_AMOUNT_USD = 200.0               # Use $200 for each trade

# --------------------------- EXCHANGE SETUP ---------------------------
exchange = ccxt.binance({
    'enableRateLimit': True,
    # 'apiKey': os.getenv('BINANCE_API_KEY'),
    # 'secret': os.getenv('BINANCE_SECRET'),
})
exchange.options['defaultType'] = 'future'  # Use Binance Futures (not spot)

# --------------------------- UTILITY FUNCTIONS ---------------------------
async def fetch_symbols():
    """Fetch all perpetual futures trading pairs from Binance."""
    async with aiohttp.ClientSession() as session:
        async with session.get(REST_URL) as resp:
            data = await resp.json()
            return [s["symbol"] for s in data["symbols"] if s.get("contractType") == "PERPETUAL"]

async def write_csv_header():
    """Ensure the liquidation CSV has a header row."""
    try:
        async with aiofiles.open(CSV_FILE, "r") as f:
            await f.readline()
    except FileNotFoundError:
        async with aiofiles.open(CSV_FILE, "w") as f:
            await f.write("timestamp,symbol,side,avg_price,filled_qty,usd_value,trade_time_ms\n")

async def append_to_csv(liq):
    """Append a single liquidation entry to the CSV file."""
    async with aiofiles.open(CSV_FILE, "a") as f:
        ts = datetime.utcfromtimestamp(liq["trade_time"] / 1000.0).isoformat()
        row = f'{ts},{liq["symbol"]},{liq["side"]},{liq["avg_price"]},{liq["filled_qty"]},{liq["usd_value"]},{liq["trade_time"]}\n'
        await f.write(row)

def parse_force_order(msg_text):
    """Parse incoming forceOrder (liquidation) message from Binance WebSocket."""
    try:
        data = json.loads(msg_text)
        payload = data.get("data", {})
        o = payload.get("o", {})
        avg_price = float(o.get("ap", 0))
        filled_qty = float(o.get("z", 0))
        usd_value = avg_price * filled_qty
        return {
            "symbol": o.get("s"),
            "side": o.get("S"),
            "avg_price": avg_price,
            "filled_qty": filled_qty,
            "usd_value": usd_value,
            "trade_time": int(o.get("T", payload.get("E", 0)))
        }
    except Exception:
        return None

# --------------------------- WEBSOCKET HANDLER ---------------------------
async def handle_ws_stream(symbols, liq_queue):
    """Listen to Binance WebSocket streams for given symbols and enqueue liquidations."""
    stream_names = [f"{sym.lower()}@forceOrder" for sym in symbols]
    url = WS_URL + "/".join(stream_names)

    while True:
        try:
            async with websockets.connect(url, ping_interval=60, ping_timeout=10) as ws:
                print(f"Connected to {len(symbols)} symbols.")
                async for msg in ws:
                    liq = parse_force_order(msg)
                    if not liq:
                        continue
                    ts = datetime.utcfromtimestamp(liq["trade_time"] / 1000.0).strftime("%H:%M:%S")
                    print(f"{ts} | {liq['symbol']} | {liq['side']} | {liq['filled_qty']:.3f} @ {liq['avg_price']:.3f} → ${liq['usd_value']:.0f}")
                    await append_to_csv(liq)
                    await liq_queue.put(liq)
        except Exception as e:
            print(f"Reconnecting due to: {e}")
            await asyncio.sleep(3)

# --------------------------- ANALYSIS AND SIGNALS ---------------------------
async def analyze_and_trade(liq_queue, dry_run=True):
    """Main strategy loop: collect liquidations and trigger analysis when thresholds are met."""
    buffer = []  # stores recent liquidations

    def prune_buffer():
        cutoff = datetime.utcnow() - timedelta(seconds=LIQ_WINDOW_SECONDS)
        cutoff_ms = int(cutoff.timestamp() * 1000)
        return [l for l in buffer if l["trade_time"] >= cutoff_ms]

    while True:
        try:
            liq = await asyncio.wait_for(liq_queue.get(), timeout=1.0)
            buffer.append(liq)
        except asyncio.TimeoutError:
            pass

        buffer = prune_buffer()

        # Count BUY/SELL occurrences per symbol
        counts = {}
        for l in buffer:
            sym = l['symbol']
            side = l['side']
            if sym not in counts:
                counts[sym] = {'BUY': 0, 'SELL': 0}
            counts[sym][side] += 1

        # Evaluate trade signals
        for sym, c in counts.items():
            if c.get('SELL', 0) >= MIN_LIQ_COUNT and c.get('BUY', 0) == 0:
                passed = await analyze_bollinger_and_decide(sym, side='SHORT')
                if passed:
                    await place_order(sym, side='sell', dry_run=dry_run)
            if c.get('BUY', 0) >= MIN_LIQ_COUNT and c.get('SELL', 0) == 0:
                passed = await analyze_bollinger_and_decide(sym, side='LONG')
                if passed:
                    await place_order(sym, side='buy', dry_run=dry_run)

        await asyncio.sleep(0.01)

# --------------------------- BOLLINGER ANALYSIS ---------------------------
async def analyze_bollinger_and_decide(symbol, side='SHORT'):
    """Apply Bollinger Band rules and return True if all criteria are met."""
    try:
        ccxt_symbol = symbol.replace('USDT', '/USDT')
        limit = BOLL_TIMEPERIOD + BOLL_LOOKBACK_CANDLES + 10
        timeframe = '1m'
        ohlcv = exchange.fetch_ohlcv(ccxt_symbol, timeframe=timeframe, limit=limit)
        if len(ohlcv) < BOLL_TIMEPERIOD + 1:
            return False

        closes = np.array([c[4] for c in ohlcv], dtype=float)
        opens = np.array([c[1] for c in ohlcv], dtype=float)
        highs = np.array([c[2] for c in ohlcv], dtype=float)
        lows = np.array([c[3] for c in ohlcv], dtype=float)

        upper, middle, lower = talib.BBANDS(closes, BOLL_TIMEPERIOD, BOLL_NBDEV, BOLL_NBDEV, 0)

        # Step 1: detect recent cross
        last_idx = len(closes) - 1
        start_idx = max(0, last_idx - BOLL_LOOKBACK_CANDLES)
        cross_idx = None
        for i in range(last_idx, start_idx - 1, -1):
            prev = i - 1
            if prev < 0:
                continue
            prev_close = closes[prev]
            cur_close = closes[i]
            if side == 'SHORT':
                if prev_close > upper[prev] and cur_close < upper[i]:
                    cross_idx = i
                    break
            else:
                if prev_close < lower[prev] and cur_close > lower[i]:
                    cross_idx = i
                    break
        if cross_idx is None:
            return False

        # Step 2: check band touch
        touched = False
        for j in range(max(0, cross_idx - BOLL_LOOKBACK_CANDLES), cross_idx + 1):
            if side == 'SHORT' and lows[j] <= lower[j]:
                touched = True
            if side == 'LONG' and highs[j] >= upper[j]:
                touched = True
        if not touched:
            return False

        # Step 3: polarity (80% rule)
        slice_opens = opens[cross_idx:last_idx + 1]
        slice_closes = closes[cross_idx:last_idx + 1]
        total = len(slice_closes)
        if total == 0:
            return False
        bullish = np.sum(slice_closes > slice_opens)
        bearish = np.sum(slice_closes < slice_opens)

        if side == 'SHORT' and bearish / total < BULL_BEAR_THRESHOLD:
            return False
        if side == 'LONG' and bullish / total < BULL_BEAR_THRESHOLD:
            return False

        print(f"{symbol}: Passed Bollinger criteria for {side}")
        return True

    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return False

# --------------------------- ORDER PLACEMENT ---------------------------
async def place_order(symbol, side='buy', leverage=1, dry_run=True):
    """Place a trade only if NO positions are currently open anywhere."""

    print(f"Preparing {side.upper()} trade for {symbol} (dry_run={dry_run})")

    # 1️⃣ --- Check if ANY position is open ---
    try:
        positions = exchange.fapiPrivate_get_positionrisk()
        open_positions = [p for p in positions if float(p["positionAmt"]) != 0]
        if open_positions:
            print("Skipping trade — a position is already open on another symbol.")
            return
    except Exception as e:
        print(f"Could not check open positions: {e}")

    # 2️⃣ --- If in dry-run mode ---
    if dry_run:
        try:
            ticker = exchange.fetch_ticker(symbol.replace('USDT', '/USDT'))
            price = float(ticker['last'])
            amount = TRADE_AMOUNT_USD / price
            print(f"[DRY RUN] Would open {side.upper()} ${TRADE_AMOUNT_USD} ({amount:.4f} {symbol}) at {price}")
        except Exception as e:
            print(f"Dry run error: {e}")
        return

    # 3️⃣ --- Live order placement (use testnet first!) ---
    try:
        ticker = exchange.fetch_ticker(symbol.replace('USDT', '/USDT'))
        price = float(ticker['last'])
        amount = TRADE_AMOUNT_USD / price

        # Apply leverage
        exchange.fapiPrivate_post_leverage({'symbol': symbol, 'leverage': int(leverage)})

        # Create market order
        order = exchange.create_order(symbol.replace('USDT', '/USDT'), 'market', side, amount)
        print(f"Opened order: {order}")

    except Exception as e:
        print(f"Error placing order: {e}")

# --------------------------- MAIN ENTRY ---------------------------
async def main():
    """Main entry point — sets up WebSocket producers and analysis consumer."""
    symbols = await fetch_symbols()
    await write_csv_header()
    liq_queue = asyncio.Queue()

    # Split symbols into safe groups for WebSocket connections
    groups = [symbols[i:i+MAX_STREAMS_PER_CONN] for i in range(0, len(symbols), MAX_STREAMS_PER_CONN)]
    print(f"Tracking {len(symbols)} symbols across {len(groups)} connections.")

    # Launch WebSocket producers and strategy consumer
    producer_tasks = [asyncio.create_task(handle_ws_stream(g, liq_queue)) for g in groups]
    consumer_task = asyncio.create_task(analyze_and_trade(liq_queue, dry_run=DRY_RUN))
    await asyncio.gather(*producer_tasks, consumer_task)

# --------------------------- PROGRAM START ---------------------------
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exited cleanly.")