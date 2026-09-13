# MERCATURA

An open-source Python trading toolkit and reference implementation for building algorithmic trading systems. It includes TA-Lib technical indicators, pandas-based technical analysis, NumPy calculations, CCXT exchange integration, a live Binance Futures liquidation tracker with signal detection, and reusable strategy boilerplate you can trade with directly.

The goal is to provide a practical collection of trading-related building blocks that can be explored, tested, modified, and used as a foundation for developing custom trading strategies and automated trading systems.

## Features

- **Indicators** (`indicators/`) — standalone TA-Lib/pandas/NumPy indicator scripts (ADX, MA, Bollinger Bands, etc.) that fetch OHLCV data via CCXT and expose a `calculate_*()` function for reuse.
- **Liquidation tracking** (`liquidations/`) — a live Binance Futures liquidation feed collector plus a signal-detection script for spotting one-sided liquidation cascades.
- **Strategy runner** (`pattern.py`) — a working example strategy where you pick indicators, combine them however you like, and place/close real orders via CCXT.
- **Tests** (`tests/`) — pytest coverage for the pure logic (liquidation parsing and signal detection), runnable without a live exchange connection.

---

## 1. Local Setup (Laptop / Dev Machine)

### Prerequisites

- Python 3.10+
- The TA-Lib C library installed on your system (the Python wrapper requires the compiled C library first):
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
pip install -r requirements.txt

# 4. Configure your credentials
cp .env.example .env
# then edit .env and fill in your real API keys/addresses
```

Your `.env` should contain:

```
SPOT_API_KEY=your_spot_api_key
SPOT_SECRET_KEY=your_spot_secret_key

FUTURES_API_KEY=your_futures_api_key
FUTURES_SECRET_KEY=your_futures_secret_key

ADDRESS_ONE=your_address
```

`.env` is already git-ignored — never commit real keys.

### Running things locally

```bash
# Run a single indicator script (prints computed values to console)
python indicators/adx.py

# Run the liquidation collector (streams live, writes to CSV)
python liquidations/binance_liquidations.py

# Run signal detection after you have some liquidation data logged
python liquidations/liquidation_signals.py --window 1
python liquidations/liquidation_signals.py --window 2

# Run your strategy
python pattern.py
```

### Running tests

```bash
pytest tests/
```

This currently covers `parse_force_order()` (liquidation parsing) and `detect_signals()` (signal detection logic) — both pure functions that don't require a live exchange connection.

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

This session keeps the collector streaming Binance Futures forceOrder liquidation events 24/7 and appending them to `binance_liquidations.csv`. Run `liquidation_signals.py` periodically against that CSV — manually inside the same screen, in a second short-lived screen, or via a cron job, since it's a one-shot batch script rather than a long-running process.

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
screen -ls                    # list all running sessions
screen -r <name>               # reattach to a session
screen -X -S <name> quit       # kill a session
```

---

## 3. The Trading Aspect — `pattern.py`

`pattern.py` is a working example strategy you edit and build on. It:

1. Picks any indicator(s) from `indicators/` by name via `load_indicator()`.
2. Combines their outputs however you want inside `check_signal()`.
3. Uses your own timeframe(s) and indicator parameters.
4. Opens a market order via CCXT with an attached take-profit and stop-loss, and closes/flips positions as signals change.

The included example combines three indicators:
- **ADX** — confirms the trend is strong enough to trade (filters out choppy conditions)
- **Fast/slow MA crossover** — picks direction (long or short)
- **Bollinger Bands** — confirms price hasn't already run past the opposite band before entering

### Customizing timeframe and parameters

- `TIMEFRAME` accepts any CCXT-supported string: `'1m'`, `'5m'`, `'15m'`, `'1h'`, `'4h'`, `'1d'`, etc.
- Each indicator function may use different parameter names (e.g. `adx.py`/`ma.py` use `period=`, while `bollinger_bands.py` uses `timeperiod=`, `nbdevup=`, `nbdevdn=`) — always check the indicator file's own function signature before wiring it into `check_signal()`.
- `POSITION_SIZE`, `TP_PCT`, `SL_PCT`, `POLL_SECONDS`, `ADX_THRESHOLD`, `FAST_MA_PERIOD`, `SLOW_MA_PERIOD`, `BB_PERIOD`, and `BB_DEV` are all safe to tune directly at the top of the file without touching the trading logic itself.

See `example_orders.md` for what the raw CCXT order objects (`open_position`/`close_position`) actually look like under the hood.

---

## 4. The Liquidations Aspect

The `liquidations/` folder tracks forced liquidations across every USDⓈ-M perpetual on Binance Futures in real time, logs every single one, and turns that raw feed into actionable signals — with both the fetching and the signal criteria fully under your control.

### `binance_liquidations.py` — fetch and log every liquidation

- Fetches every active USDⓈ-M perpetual symbol from Binance.
- Opens multiple WebSocket connections (batched under Binance's per-connection stream limit) subscribed to each symbol's `forceOrder` stream.
- Parses every liquidation event (symbol, side, average fill price, filled quantity, USD value, timestamp) and appends it to `binance_liquidations.csv`.
- Automatically reconnects on drops.

This gives you a continuously growing, timestamped ledger of every liquidation happening across the entire futures market — something no single exchange UI exposes in bulk.

### `liquidation_signals.py` — turn the raw log into signals

A single script, two modes, controlled by `--window`:

- `--window 1` (default) — strict per-minute signal: fires when 7+ same-side liquidations occur within a single minute with zero opposite-side liquidations in that minute. Tight timing, but can miss cascades that straddle a minute boundary.
- `--window 2` — rolling two-minute signal: same rule, but grouped over the current minute plus the one before it. Catches cascades split across a minute boundary (e.g. 4 liquidations at 12:00:50 and 4 more at 12:01:05) that the 1-minute mode would miss, at the cost of slightly looser timing.

```bash
python liquidations/liquidation_signals.py --window 1   # → signals.csv
python liquidations/liquidation_signals.py --window 2   # → signals_combined.csv
python liquidations/liquidation_signals.py --window 2 --output my_signals.csv   # custom filename
```

**Why this matters:** a cluster of same-side liquidations with no counter-liquidations usually means forced closes are cascading in one direction (e.g. a wave of longs getting stopped out), which often marks a short-term local extreme or exhaustion point — useful as a contrarian/reversal signal. Running both windows together gives you high-confidence, tightly-timed signals (`--window 1`) alongside more complete coverage of cascades that straddle a minute mark (`--window 2`).

### Editing to your own taste

Nothing here is fixed — the constants at the top of `liquidation_signals.py` are meant to be tuned:

- `THRESHOLD` — minimum same-side liquidations required to qualify as a signal (default: 7). Lower it for more sensitivity, raise it to filter for only the largest cascades.
- `TIME_OFFSET` — timezone offset applied to output timestamps (default: UTC+1). Change to match your own timezone.
- `--window` — 1 or 2 minutes, as above.

Run either mode (or both) periodically against `binance_liquidations.csv` — cron, a loop in the same VPS screen session, or manually — to keep signal files up to date as new liquidations stream in.

---

## 5. Development

### Requirements

Install everything the toolkit needs (including TA-Lib's Python bindings — make sure the C library prerequisite above is installed first):

```bash
pip install -r requirements.txt
```

### Tests

```bash
pytest tests/
```

Current coverage: `parse_force_order()` (liquidation event parsing) and `detect_signals()` (signal detection logic) — both pure functions, tested without any live exchange connection. Coverage for `pattern.py`'s `check_signal()` and the indicator files is planned but not yet added.

### CI

Every push and pull request to `main` runs the test suite automatically via GitHub Actions (`.github/workflows/tests.yml`).

---

## Roadmap

- [ ] Multi-exchange support for the liquidation tracker (currently Binance Futures only)
- [ ] Additional indicator coverage


## License

MIT — see `LICENSE`.

## Disclaimer

This project is for educational and development purposes. The included strategies, indicators, and signal logic do not constitute financial advice or guarantee profitable trading. Use at your own risk.