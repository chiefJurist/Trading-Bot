# MERCATURA

This repository is an open-source Python trading toolkit and reference implementation for building algorithmic trading systems. It contains implementations and examples of TA-Lib technical indicators, pandas-based technical analysis, NumPy calculations, CCXT exchange functions, their corresponding outputs and reusable strategy boilerplate.

The goal is to provide a practical collection of trading-related building blocks that can be explored, tested, modified and used as a foundation for developing custom trading strategies and automated trading systems.

## Features

- **Indicators** (`indicators/`) — standalone TA-Lib/pandas/NumPy indicator scripts (ADX, ADXR, MA, etc.) that fetch OHLCV data via CCXT and print computed values per candle.
- **Liquidation tracking** (`liquidations/`) — a live Binance Futures liquidation feed collector plus two downstream signal-detection scripts.
- **Strategy runner** (`pattern.py`) — a boilerplate entrypoint where you pick indicators, combine them however you like, and place/close real orders via CCXT.

---

## 1. Local Setup (Laptop / Dev Machine)

### Prerequisites

- Python 3.10+
- TA-Lib C library installed on your system (the Python wrapper `TA-Lib` requires the compiled C library first):
  - **macOS:** `brew install ta-lib`
  - **Ubuntu/Debian:** `sudo apt-get install libta-lib0-dev` (or build from source if unavailable)
  - **Windows:** install a prebuilt TA-Lib wheel matching your Python version

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/mercatura.git
cd mercatura

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install ccxt pandas numpy TA-Lib python-dotenv aiohttp aiofiles websockets

# 4. Configure your credentials
cp .env.example .env
# then edit .env and fill in your real API keys/addresses
```

Your `.env` should contain:

SPOT_API_KEY=your_spot_api_key
SPOT_SECRET_KEY=your_spot_secret_key

FUTURES_API_KEY=your_futures_api_key
FUTURES_SECRET_KEY=your_futures_secret_key

ADDRESS_ONE=your_address


`.env` is already git-ignored — never commit real keys.

### Running things locally

```bash
# Run a single indicator script (prints computed values to console)
python indicators/adx.py

# Run the liquidation collector (streams live, writes to CSV)
python liquidations/binance_liquidations.py

# Run signal analysis after you have some liquidation data logged
python liquidations/binance_liquidation_signals.py
python liquidations/binance_liquidation_signals_long.py

# Run your strategy
python pattern.py
```

---

## 2. VPS Deployment (with `screen`)

Running these scripts continuously (liquidation streaming, live trading) requires a persistent session that survives SSH disconnects. `screen` is the simplest way to do that.

### Install screen

```bash
sudo apt-get update
sudo apt-get install screen
```

### Set up the repo on the VPS

Follow the same steps as the local setup above (clone, venv, install deps, configure `.env`) directly on the VPS.

### Screen 1 — Liquidations collector

```bash
screen -S liquidations
cd mercatura
source venv/bin/activate
python liquidations/binance_liquidations.py
```

Detach without killing it: `Ctrl+A`, then `D`.
Reattach later: `screen -r liquidations`.

This session keeps `binance_liquidations.py` streaming Binance Futures forceOrder liquidation events 24/7 and appending them to `binance_liquidations.csv`.

You can run the two signal scripts (`binance_liquidation_signals.py` / `_long.py`) periodically against that CSV — either manually inside the same screen, in a second short-lived screen, or via a cron job, since they're one-shot batch scripts rather than long-running processes.

### Screen 2 — Trading (pattern.py)

```bash
screen -S trading
cd mercatura
source venv/bin/activate
python pattern.py
```

Detach: `Ctrl+A`, then `D`. Reattach: `screen -r trading`.

This session runs your live strategy — whichever indicators and order logic you've wired up in `pattern.py` — continuously in the background.

### Useful screen commands

```bash
screen -ls          # list all running sessions
screen -r <name>    # reattach to a session
screen -X -S <name> quit   # kill a session
```

---

## 3. The Trading Aspect — `pattern.py`

`pattern.py` is intentionally empty boilerplate. It's the file you edit to:

1. Pick any indicator(s) from `indicators/` by name.
2. Combine their outputs however you want (e.g. only enter when ADX confirms trend strength AND your MA crossover fires).
3. Set your own timeframe(s) and indicator parameters.
4. Use CCXT to open a market order, then attach a take-profit and stop-loss, and later close the position.

Example to drop into `pattern.py` and edit from there:

```python
import os
import importlib
import time
from dotenv import load_dotenv
import ccxt
import pandas as pd

load_dotenv()

FUTURES_API_KEY = os.getenv('FUTURES_API_KEY')
FUTURES_SECRET_KEY = os.getenv('FUTURES_SECRET_KEY')

binance_futures = ccxt.binanceusdm({
    'apiKey': FUTURES_API_KEY,
    'secret': FUTURES_SECRET_KEY,
})

SYMBOL = 'ETH/USDT'
TIMEFRAME = '5m'
POSITION_SIZE = 0.011   # contracts
TP_PCT = 0.015          # 1.5% take profit
SL_PCT = 0.005          # 0.5% stop loss


def fetch_ohlcv(symbol, timeframe, limit=1500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df


def load_indicator(name):
    """Dynamically import any script from indicators/ by filename (no .py)."""
    return importlib.import_module(f"indicators.{name}")


def check_signal(df):
    # Load whichever indicators you want and combine them freely.
    adx_mod = load_indicator("adx")
    adxr_mod = load_indicator("adxr")

    adx_values = adx_mod.calculate_adx(df)
    adxr_values = adxr_mod.calculate_adxr(df)

    latest_adx = adx_values[-1][2]['adx']
    latest_adxr = adxr_values[-1][2]['adxr']

    # Example combined rule — edit this however you like
    if latest_adx > 25 and latest_adxr > 20:
        return "long"
    return None


def open_long(symbol, amount):
    order = binance_futures.create_order(
        symbol=symbol, type='market', side='buy', amount=amount,
        params={'positionSide': 'LONG'}
    )
    entry_price = order['average']

    tp_price = round(entry_price * (1 + TP_PCT), 2)
    sl_price = round(entry_price * (1 - SL_PCT), 2)

    binance_futures.create_order(
        symbol=symbol, type='limit', side='sell', amount=amount, price=tp_price,
        params={'positionSide': 'LONG', 'reduceOnly': True}
    )
    binance_futures.create_order(
        symbol=symbol, type='STOP_MARKET', side='sell', amount=amount,
        params={'positionSide': 'LONG', 'reduceOnly': True, 'stopPrice': sl_price}
    )
    return order


def close_position(symbol, amount, side='LONG'):
    close_side = 'sell' if side == 'LONG' else 'buy'
    return binance_futures.create_order(
        symbol=symbol, type='market', side=close_side, amount=amount,
        params={'positionSide': side, 'reduceOnly': True}
    )


def main():
    while True:
        df = fetch_ohlcv(SYMBOL, TIMEFRAME)
        signal = check_signal(df)

        if signal == "long":
            open_long(SYMBOL, POSITION_SIZE)
            print(f"Opened LONG on {SYMBOL}")

        time.sleep(60)


if __name__ == "__main__":
    main()
```

Swap `load_indicator("adx")` / `load_indicator("adxr")` for any file in `indicators/` by name — the loader works with any of them since they all expose a `calculate_*` function taking a DataFrame. Stack as many as you want inside `check_signal()`.

---

## 4. The Liquidations Aspect

The `liquidations/` folder tracks forced liquidations across every USDⓈ-M perpetual on Binance Futures in real time and turns the raw feed into actionable signals.

### `binance_liquidations.py` — the collector

- Fetches every active USDⓈ-M perpetual symbol from Binance.
- Opens multiple WebSocket connections (batched under Binance's per-connection stream limit) subscribed to each symbol's `forceOrder` stream.
- Parses every liquidation event (symbol, side, average fill price, filled quantity, USD value, timestamp) and appends it to `binance_liquidations.csv`.
- Automatically reconnects on drops.

This gives you a continuously growing, timestamped ledger of every liquidation happening across the entire futures market — something no single exchange UI exposes in bulk.

### `binance_liquidation_signals.py` — strict per-minute signal

- Groups liquidations into 1-minute buckets per symbol.
- Fires a signal only when **7 or more liquidations on one side occur within the same single minute with zero liquidations on the opposite side**.
- Writes qualifying signals to `signals.csv`.

**Why this matters:** a cluster of same-side liquidations with no counter-liquidations usually means forced closes are cascading in one direction (e.g. a wave of longs getting stopped out), which often marks a short-term local extreme or exhaustion point — useful as a contrarian/reversal signal.

### `binance_liquidation_signals_long.py` — rolling 2-minute signal

- Same logic, but combines each minute with the minute before it into a rolling 2-minute window before counting.
- Catches cascades that straddle a minute boundary (e.g. 4 liquidations at 12:00:50 and 4 more at 12:01:05) that the strict per-minute version above would miss entirely, since neither minute alone hits the threshold of 7.
- Writes results to `signals_combined.csv`.

**Advantage of running both:** the strict version gives you high-confidence, tightly-timed signals; the rolling version catches the same underlying event even when it straddles a minute mark, giving you more complete coverage of genuine liquidation cascades at the cost of slightly looser timing.

Run these two scripts against `binance_liquidations.csv` at whatever cadence you like (cron, manual, or looped inside the same VPS screen) to keep `signals.csv` and `signals_combined.csv` up to date.

---

## Disclaimer

This project is for educational and development purposes. The included strategies, indicators, and signal logic do not constitute financial advice or guarantee profitable trading. Use at your own risk.