# liquidation_sniper.py
import asyncio
import csv
import json
import os
from datetime import datetime, timezone, timedelta
import ccxt.async_support as ccxt          # ← Your free ccxt (perfect)
import pandas as pd
import talib                               # ← Your working TA-Lib 0.6.8
import logging

# ========================= CONFIG =========================
LEVERAGE = 10
PRICE_MOVE_PCT = 0.05          # 5% price move = 0.5% real profit at 10x
TIMEFRAME = '1m'
SIGNALS_FILE = 'signals.csv'
POSITION_FILE = 'current_position.json'
CHECK_INTERVAL = 7
MAX_WAIT_CANDLES = 12

API_KEY = 'YOUR_API_KEY_HERE'
API_SECRET = 'YOUR_API_SECRET_HERE'

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
log = logging.getLogger(__name__)

exchange = None
current_position = None
candidates = {}
last_line = 0

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

# ========================= READ SIGNALS =========================
def get_new_signals():
    global last_line
    signals = []
    if not os.path.exists(SIGNALS_FILE):
        return signals
    with open(SIGNALS_FILE) as f:
        lines = f.readlines()
    if len(lines) <= last_line:
        return signals

    reader = csv.DictReader(lines[last_line:])
    for row in reader:
        try:
            # signals.csv is in UTC+1 → convert back to UTC
            dt_local = datetime.strptime(f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M")
            signal_time = (dt_local - timedelta(hours=1)).replace(tzinfo=timezone.utc)
            signals.append({
                'symbol': row['pair'],
                'side': row['side'].upper(),   # BUY = many shorts liquidated → go LONG
                'time': signal_time
            })
        except:
            continue
    last_line = len(lines)
    return signals

# ========================= FETCH CANDLES =========================
async def fetch_candles(symbol, limit=100):
    try:
        raw = await exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=limit)
        df = pd.DataFrame(raw, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        return df
    except Exception as e:
        log.error(f"Fetch failed {symbol}: {e}")
        return None

# ========================= ENTRY + TP =========================
async def enter_trade(symbol, go_long: bool):
    try:
        await exchange.set_leverage(LEVERAGE, symbol)
        ticker = await exchange.fetch_ticker(symbol)
        price = ticker['last']
        amount = 150 / price                     # ~$150 position size

        # Market entry
        order = await exchange.create_market_buy_order(symbol, amount) if go_long \
                else await exchange.create_market_sell_order(symbol, amount)
        entry = float(order.get('average') or order.get('price') or price)
        tp_price = round(entry * (1 + PRICE_MOVE_PCT if go_long else 1 - PRICE_MOVE_PCT), 8)

        # Take-profit limit order
        await exchange.create_limit_sell_order(symbol, amount, tp_price, {'reduceOnly': True}) if go_long \
            else await exchange.create_limit_buy_order(symbol, amount, tp_price, {'reduceOnly': True})

        log.info(f"""
        SNIPED
        {symbol} → {'LONG' if go_long else 'SHORT'}
        Entry: {entry:.6f} │ TP: {tp_price:.6f} (+5% price → 0.5% real profit)
        """)

        save_position({'symbol': symbol, 'side': 'LONG' if go_long else 'SHORT', 'entry': entry, 'tp': tp_price})
        candidates.clear()

    except Exception as e:
        log.error(f"Entry failed {symbol}: {e}")

# ========================= MAIN SCANNER =========================
async def scanner():
    global candidates

    while True:
        # No new trades if already in position
        if current_position:
            await asyncio.sleep(CHECK_INTERVAL)
            continue

        # New liquidation clusters?
        for sig in get_new_signals():
            sym = sig['symbol']
            if sym in candidates:
                continue
            direction = 'LONG' if sig['side'] == 'BUY' else 'SHORT'
            candidates[sym] = {
                'time': sig['time'],
                'direction': direction,
                'step3_passed': False
            }
            log.info(f"New candidate → {sym} | Expecting {direction}")

        # Check every candidate
        for sym, c in list(candidates.items()):
            df = await fetch_candles(sym, 60)
            if df is None or len(df) < 30:
                continue

            signal_candle = df[df['timestamp'] == c['time']]
            if signal_candle.empty:
                continue
            idx = signal_candle.index[0]
            closes = df['close'].values.astype(float)

            # Step 3: Break of BB(20, 4.0)
            if not c['step3_passed']:
                upper4, _, lower4 = talib.BBANDS(closes, timeperiod=20, nbdevup=4.0, nbdevdn=4.0)
                high = df.iloc[idx]['high']
                low = df.iloc[idx]['low']

                if (c['direction'] == 'LONG' and high > upper4[idx]) or \
                    (c['direction'] == 'SHORT' and low < lower4[idx]):
                    c['step3_passed'] = True
                else:
                    candidates.pop(sym, None)
                    continue

            # Step 4: Wait for 2 closes back inside BB(20, 1.0)
            upper1, _, lower1 = talib.BBANDS(closes, timeperiod=20, nbdevup=1.0, nbdevdn=1.0)
            count = 0
            for i in range(idx + 1, min(idx + 1 + MAX_WAIT_CANDLES, len(df))):
                close = df.iloc[i]['close']
                band = lower1[i] if c['direction'] == 'LONG' else upper1[i]
                if (c['direction'] == 'LONG' and close > band) or \
                    (c['direction'] == 'SHORT' and close < band):
                    count += 1
                    if count >= 2:
                        await enter_trade(sym, c['direction'] == 'LONG')
                        break
            else:
                if i - idx >= MAX_WAIT_CANDLES:
                    candidates.pop(sym, None)

        await asyncio.sleep(CHECK_INTERVAL)

# ========================= START =========================
async def main():
    global exchange
    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True,
        'options': {'defaultType': 'future'},
    })
    load_position()
    log.info("LIQUIDATION REVERSAL SNIPER IS LIVE – Hunting 5% moves (0.5% real profit)")
    await scanner()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot stopped by user.")