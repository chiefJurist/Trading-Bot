import os
import time
import importlib
from datetime import datetime
from dotenv import load_dotenv
import ccxt
import pandas as pd

load_dotenv()

# ---- Credentials ----
FUTURES_API_KEY = os.getenv('FUTURES_API_KEY')
FUTURES_SECRET_KEY = os.getenv('FUTURES_SECRET_KEY')

binance_futures = ccxt.binanceusdm({
    'apiKey': FUTURES_API_KEY,
    'secret': FUTURES_SECRET_KEY,
})

# ---- Strategy Config (edit freely) ----
SYMBOL = 'ETH/USDT'
TIMEFRAME = '5m'            # <- change this to any CCXT-supported timeframe: '1m', '15m', '1h', '4h', etc.
POSITION_SIZE = 0.011       # contracts
TP_PCT = 0.015              # 1.5% take profit
SL_PCT = 0.005              # 0.5% stop loss
POLL_SECONDS = 60

ADX_THRESHOLD = 25          # trend strength filter
FAST_MA_PERIOD = 9
SLOW_MA_PERIOD = 21
BB_PERIOD = 20
BB_DEV = 1                  # matches nbdevup/nbdevdn in bollinger_bands.py

# ---- State ----
current_position = None    # None | "LONG" | "SHORT"


def load_indicator(name):
    """Dynamically import any file from indicators/ by filename (no .py)."""
    return importlib.import_module(f"indicators.{name}")


def fetch_ohlcv(symbol, timeframe, limit=1500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df


def check_signal(df):
    """
    Combine indicators however you want here.
    Current logic:
      - ADX confirms the trend is strong enough to trade
      - Fast/slow MA crossover picks direction
      - Bollinger Bands confirms price is at a reasonable entry point
        (not already extended past the opposite band)

    Note: not every indicator file uses the same parameter name.
    adx.py / ma.py use `period=`, but bollinger_bands.py uses `timeperiod=`,
    `nbdevup=`, `nbdevdn=` — check each indicator file's function signature
    before wiring it in here.
    """
    adx_mod = load_indicator("adx")
    ma_mod = load_indicator("ma")
    bb_mod = load_indicator("bollinger_bands")

    adx_values = adx_mod.calculate_adx(df, period=14)
    fast_ma_values = ma_mod.calculate_ma(df, period=FAST_MA_PERIOD)
    slow_ma_values = ma_mod.calculate_ma(df, period=SLOW_MA_PERIOD)
    bb_values = bb_mod.calculate_bollinger_bands(
        df, timeperiod=BB_PERIOD, nbdevup=BB_DEV, nbdevdn=BB_DEV
    )

    latest_adx = adx_values[-1][2]['adx']
    fast_ma = fast_ma_values[-1][2]['ma']
    slow_ma = slow_ma_values[-1][2]['ma']
    prev_fast_ma = fast_ma_values[-2][2]['ma']
    prev_slow_ma = slow_ma_values[-2][2]['ma']

    latest_close = bb_values[-1][2]['close']
    upperband = bb_values[-1][2]['upperband']
    lowerband = bb_values[-1][2]['lowerband']

    if latest_adx < ADX_THRESHOLD:
        return None  # trend too weak, sit out

    crossed_up = prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma
    crossed_down = prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma

    # Only go long if price hasn't already run up past the upper band,
    # only go short if it hasn't already dropped past the lower band.
    if crossed_up and latest_close < upperband:
        return "long"
    if crossed_down and latest_close > lowerband:
        return "short"
    return None


def open_position(symbol, side, amount):
    order_side = 'buy' if side == 'long' else 'sell'
    position_side = 'LONG' if side == 'long' else 'SHORT'

    order = binance_futures.create_order(
        symbol=symbol, type='market', side=order_side, amount=amount,
        params={'positionSide': position_side}
    )
    entry_price = order['average']

    if side == 'long':
        tp_price = round(entry_price * (1 + TP_PCT), 2)
        sl_price = round(entry_price * (1 - SL_PCT), 2)
        exit_side = 'sell'
    else:
        tp_price = round(entry_price * (1 - TP_PCT), 2)
        sl_price = round(entry_price * (1 + SL_PCT), 2)
        exit_side = 'buy'

    binance_futures.create_order(
        symbol=symbol, type='limit', side=exit_side, amount=amount, price=tp_price,
        params={'positionSide': position_side, 'reduceOnly': True}
    )
    binance_futures.create_order(
        symbol=symbol, type='STOP_MARKET', side=exit_side, amount=amount,
        params={'positionSide': position_side, 'reduceOnly': True, 'stopPrice': sl_price}
    )

    print(f"[{datetime.utcnow().isoformat()}] Opened {position_side} on {symbol} @ {entry_price} "
          f"(TP {tp_price} / SL {sl_price})")
    return position_side


def close_position(symbol, amount, position_side):
    close_side = 'sell' if position_side == 'LONG' else 'buy'
    order = binance_futures.create_order(
        symbol=symbol, type='market', side=close_side, amount=amount,
        params={'positionSide': position_side, 'reduceOnly': True}
    )
    print(f"[{datetime.utcnow().isoformat()}] Closed {position_side} on {symbol}")
    return order


def main():
    global current_position

    print(f"Starting pattern runner on {SYMBOL} ({TIMEFRAME})...")

    while True:
        try:
            df = fetch_ohlcv(SYMBOL, TIMEFRAME)
            signal = check_signal(df)

            if signal == "long" and current_position != "LONG":
                if current_position == "SHORT":
                    close_position(SYMBOL, POSITION_SIZE, "SHORT")
                current_position = open_position(SYMBOL, "long", POSITION_SIZE)

            elif signal == "short" and current_position != "SHORT":
                if current_position == "LONG":
                    close_position(SYMBOL, POSITION_SIZE, "LONG")
                current_position = open_position(SYMBOL, "short", POSITION_SIZE)

        except Exception as e:
            print(f"[{datetime.utcnow().isoformat()}] Error: {e}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exited cleanly.")