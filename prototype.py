# ultimate_liquidation_sniper.py
import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
import ccxt.async_support as ccxt
import talib
import logging
import aiohttp
import websockets
import pandas as pd

# ========================= CONFIG =========================
LEVERAGE = 10
PRICE_MOVE_PCT = 0.05           # 5% price move = 0.5% real profit
TIMEFRAME = '1m'
CHECK_INTERVAL = 5              # seconds
MAX_WAIT_CANDLES = 12
MIN_LIQS_FOR_SIGNAL = 7
YOUR_TIMEZONE_OFFSET = timedelta(hours=1)  # You use UTC+1

API_KEY = 'YOUR_BINANCE_FUTURES_KEY'
API_SECRET = 'YOUR_BINANCE_FUTURES_SECRET'
POSITION_FILE = 'current_position.json'

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
log = logging.getLogger(__name__)

# ========================= GLOBALS =========================
exchange = None
current_position = None
candidates = {}                 # symbol → tracking data
minute_data = {}                # (minute_utc1, symbol) → {"BUY": 0, "SELL": 0}
last_processed_minute = None

# ========================= POSITION =========================
def load_position():
    global current_position
    if os.path.exists(POSITION_FILE):
        try:
            with open(POSITION_FILE) as f:
                current_position = json.load(f)
            log.info(f"Resumed position → {current_position['symbol']} {current_position['side']}")
        except:
            current_position = None

def save_position(data):
    global current_position
    current_position = data
    with open(POSITION_FILE, 'w') as f:
        json.dump(data, f)

# ========================= FETCH SYMBOLS =========================
async def get_perpetual_symbols():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://fapi.binance.com/fapi/v1/exchangeInfo") as resp:
            data = await resp.json()
            return [s["symbol"] for s in data["symbols"] if s["contractType"] == "PERPETUAL"]

# ========================= LIQUIDATION PROCESSING =========================
def process_liquidation(liq_data):
    global minute_data, last_processed_minute

    if not liq_data or "symbol" not in liq_data:
        return

    # Binance gives trade_time in milliseconds
    ts_ms = liq_data["trade_time"]
    dt_utc = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    dt_local = dt_utc + YOUR_TIMEZONE_OFFSET
    minute_key = dt_local.replace(second=0, microsecond=0)

    symbol = liq_data["symbol"]
    side = liq_data["side"]  # "BUY" or "SELL" (side that got liquidated)

    key = (minute_key, symbol)
    if key not in minute_data:
        minute_data[key] = {"BUY": 0, "SELL": 0}
    minute_data[key][side] += 1

    # Check if this minute just completed
    now_local = datetime.now().replace(microsecond=0) + YOUR_TIMEZONE_OFFSET
    current_minute = now_local.replace(second=0, microsecond=0)

    if last_processed_minute != current_minute:
        check_completed_minutes(current_minute)
        last_processed_minute = current_minute

def check_completed_minutes(current_minute):
    global minute_data
    to_remove = []
    for (min_time, symbol), counts in minute_data.items():
        if min_time >= current_minute:
            continue
        buy = counts["BUY"]
        sell = counts["SELL"]
        if buy >= MIN_LIQS_FOR_SIGNAL and sell == 0:
            trigger_signal(symbol, "BUY", min_time)   # many shorts → go LONG
        elif sell >= MIN_LIQS_FOR_SIGNAL and buy == 0:
            trigger_signal(symbol, "SELL", min_time)  # many longs → go SHORT
        to_remove.append((min_time, symbol))
    for k in to_remove:
        minute_data.pop(k, None)

def trigger_signal(symbol, liq_side, minute_time):
    if current_position:
        return
    # REVERSED LOGIC — THIS IS WHAT YOU WANT
    direction = 'SHORT' if liq_side == 'BUY' else 'LONG'   # ← THIS LINE CHANGED
    candidates[symbol] = {
        'signal_time': minute_time.replace(tzinfo=timezone.utc),
        'direction': direction,
        'step3_passed': False
    }
    log.info(f"SIGNAL → {symbol} | {liq_side} cluster → Going {direction} (reversal play)")

# ========================= CANDLES & TA =========================
async def fetch_candles(symbol, limit=100):
    try:
        raw = await exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=limit)
        df = pd.DataFrame(raw, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        return df
    except:
        return None

# ========================= ENTRY =========================
async def enter_trade(symbol, go_long: bool):
    try:
        await exchange.set_leverage(LEVERAGE, symbol)
        ticker = await exchange.fetch_ticker(symbol)
        price = ticker['last']
        amount = 150 / price

        order = await exchange.create_market_buy_order(symbol, amount) if go_long \
                else await exchange.create_market_sell_order(symbol, amount)
        entry = float(order.get('average') or order.get('price') or price)
        tp_price = round(entry * (1 + PRICE_MOVE_PCT if go_long else 1 - PRICE_MOVE_PCT), 8)

        await exchange.create_limit_sell_order(symbol, amount, tp_price, {'reduceOnly': True}) if go_long \
            else await exchange.create_limit_buy_order(symbol, amount, tp_price, {'reduceOnly': True})

        log.info(f"""
        SNIPED {symbol} → {'LONG' if go_long else 'SHORT'}
        Entry: {entry:.6f} → TP: {tp_price:.6f} (+5%)
        """)
        save_position({'symbol': symbol, 'side': 'LONG' if go_long else 'SHORT', 'entry': entry, 'tp': tp_price})
        candidates.clear()
    except Exception as e:
        log.error(f"Trade failed {symbol}: {e}")

# ========================= SCANNER =========================
async def scanner():
    global candidates
    while True:
        if current_position:
            await asyncio.sleep(CHECK_INTERVAL)
            continue

        for sym, data in list(candidates.items()):
            df = await fetch_candles(sym, 60)
            if df is None or len(df) < 30:
                continue

            sig_candle = df[df['timestamp'] == data['signal_time']]
            if sig_candle.empty:
                continue
            idx = sig_candle.index[0]
            closes = df['close'].values.astype(float)

            if not data['step3_passed']:
                upper4, _, lower4 = talib.BBANDS(closes, 20, 4.0, 4.0)
                if (data['direction'] == 'LONG' and df.iloc[idx]['high'] > upper4[idx]) or \
                    (data['direction'] == 'SHORT' and df.iloc[idx]['low'] < lower4[idx]):
                    data['step3_passed'] = True
                else:
                    candidates.pop(sym, None)
                    continue

            upper1, _, lower1 = talib.BBANDS(closes, 20, 1.0, 1.0)
            count = 0
            for i in range(idx + 1, min(idx + 1 + MAX_WAIT_CANDLES, len(df))):
                close = df.iloc[i]['close']
                band = lower1[i] if data['direction'] == 'LONG' else upper1[i]
                if (data['direction'] == 'LONG' and close > band) or \
                    (data['direction'] == 'SHORT' and close < band):
                    count += 1
                    if count >= 2:
                        await enter_trade(sym, data['direction'] == 'LONG')
                        break
            else:
                if i - idx >= MAX_WAIT_CANDLES:
                    candidates.pop(sym, None)

        await asyncio.sleep(CHECK_INTERVAL)

# ========================= WEBSOCKET LIQUIDATIONS =========================
async def liquidation_stream(symbols_batch):
    streams = [f"{s.lower()}@forceOrder" for s in symbols_batch]
    url = f"wss://fstream.binance.com/stream?streams={'/'.join(streams)}"

    while True:
        try:
            async with websockets.connect(url, ping_interval=60) as ws:
                log.info(f"Liq stream connected → {len(symbols_batch)} symbols")
                async for msg in ws:
                    try:
                        data = json.loads(msg)
                        o = data['data']['o']
                        liq = {
                            "symbol": o['s'],
                            "side": o['S'],
                            "avg_price": float(o['ap']),
                            "filled_qty": float(o['z']),
                            "usd_value": float(o['ap']) * float(o['z']),
                            "trade_time": int(o['T'])
                        }
                        process_liquidation(liq)
                    except:
                        continue
        except Exception as e:
            log.error(f"Liq WS error: {e} → reconnecting...")
            await asyncio.sleep(3)

# ========================= MAIN =========================
async def main():
    global exchange
    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True,
        'options': {'defaultType': 'future'},
    })

    load_position()
    log.info("ULTIMATE LIQUIDATION SNIPER IS LIVE — NO CSV, NO DELAY, NO MERCY")

    symbols = await get_perpetual_symbols()
    batch_size = 100
    batches = [symbols[i:i+batch_size] for i in range(0, len(symbols), batch_size)]

    tasks = [liquidation_stream(batch) for batch in batches] + [scanner()]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Sniper stopped.")