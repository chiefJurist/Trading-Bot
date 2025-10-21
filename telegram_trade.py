"""
Binance Futures Liquidation Stream + TA + Auto Paper Trades (Testnet)
--------------------------------------------------------------------
This script:
1. Streams Binance Futures liquidation data.
2. Detects high-volume liquidation clusters (within 2 min).
3. Applies Bollinger Band analysis (via TA-Lib).
4. Auto-executes paper trades on Binance Testnet using CCXT.

Author: Anthony
"""

import asyncio
import json
import aiofiles
import aiohttp
import websockets
import pandas as pd
import numpy as np
import ccxt
import talib
from datetime import datetime, timedelta
from collections import defaultdict, deque

# ---------------- CONFIGURATION ----------------
REST_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
WS_URL = "wss://fstream.binance.com/stream?streams="

MAX_STREAMS_PER_CONN = 100
CSV_FILE = "binance_liquidations.csv"
TIMEFRAME = "5m"
WINDOW_MINUTES = 2
BOLL_PERIOD = 20
BOLL_BANDWIDTH = 1

TARGET_PROFIT = 0.05   # 5%
STOP_LOSS = 0.03       # 3%
TRADE_LEVERAGE = 1     # 1x leverage
TRADE_SIZE_USDT = 50   # size per trade on testnet

# -------------- BINANCE TESTNET SETUP --------------
# Environment variables
api_key = 'cTTxVL1Cka27JhHPL80arFFL1lPN6dhZWZwpQJ5rw7Uyl32hRiLtcqbNVxFS4u2O'
api_secret = 'WPwxBqYa37AXKOMxwWmFeJJ7KvlmHpuD0dUIjd2d9YoW53L1yRGwJEcZhtaJpBeF'

# Connect CCXT client to Binance Futures Testnet
exchange = ccxt.binance({
    "apiKey": api_key,
    "secret": api_secret,
    "options": {"defaultType": "future"},
    "urls": {
        "api": {
            "public": "https://testnet.binancefuture.com/fapi/v1",
            "private": "https://testnet.binancefuture.com/fapi/v1"
        }
    }
})
exchange.set_sandbox_mode(True)

# In-memory data store for recent liquidations
liq_data = defaultdict(lambda: deque(maxlen=1000))

# -------------- UTILITY FUNCTIONS ----------------
async def fetch_symbols():
    """Fetch all USDⓈ-M perpetual futures symbols."""
    async with aiohttp.ClientSession() as session:
        async with session.get(REST_URL) as resp:
            data = await resp.json()
            return [s["symbol"] for s in data["symbols"] if s["contractType"] == "PERPETUAL"]

async def write_csv_header():
    """Create CSV header if not exists."""
    try:
        async with aiofiles.open(CSV_FILE, "r") as f:
            await f.readline()
    except FileNotFoundError:
        async with aiofiles.open(CSV_FILE, "w") as f:
            await f.write("timestamp,symbol,side,avg_price,filled_qty,usd_value\n")

async def append_to_csv(liq):
    """Append liquidation data to CSV."""
    async with aiofiles.open(CSV_FILE, "a") as f:
        ts = datetime.utcfromtimestamp(liq["trade_time"]/1000.0).isoformat()
        row = f'{ts},{liq["symbol"]},{liq["side"]},{liq["avg_price"]},{liq["filled_qty"]},{liq["usd_value"]}\n'
        await f.write(row)

# -------------- PARSE WEBSOCKET EVENTS ----------------
def parse_force_order(msg_text):
    """Parse 'forceOrder' events (liquidations)."""
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

# -------------- TECHNICAL ANALYSIS ----------------
async def analyze_with_bollinger(symbol, direction):
    """Apply Bollinger Band analysis to confirm entry conditions."""
    try:
        # Fetch 30 latest candles
        ohlcv = exchange.fetch_ohlcv(symbol.replace("USDT", "/USDT"), timeframe=TIMEFRAME, limit=30)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

        # Compute Bollinger Bands
        upper, middle, lower = talib.BBANDS(df["close"], timeperiod=BOLL_PERIOD,
                                            nbdevup=BOLL_BANDWIDTH, nbdevdn=BOLL_BANDWIDTH)
        df["upper"], df["middle"], df["lower"] = upper, middle, lower
        recent = df.tail(5)

        # --- Short logic ---
        if direction == "short":
            cross = (recent["close"].iloc[0] > recent["upper"].iloc[0]) and (recent["close"].iloc[-1] < recent["upper"].iloc[-1])
            touch_lower = any(recent["low"] <= recent["lower"])
            bearish_ratio = (recent["close"] < recent["open"]).sum() / len(recent)
            if cross and touch_lower and bearish_ratio >= 0.8:
                print(f"✅ SHORT signal confirmed for {symbol}")
                await execute_paper_trade(symbol, "SELL")

        # --- Long logic ---
        else:
            cross = (recent["close"].iloc[0] < recent["lower"].iloc[0]) and (recent["close"].iloc[-1] > recent["lower"].iloc[-1])
            touch_upper = any(recent["high"] >= recent["upper"])
            bullish_ratio = (recent["close"] > recent["open"]).sum() / len(recent)
            if cross and touch_upper and bullish_ratio >= 0.8:
                print(f"✅ LONG signal confirmed for {symbol}")
                await execute_paper_trade(symbol, "BUY")

    except Exception as e:
        print(f"TA error for {symbol}: {e}")

# -------------- TRADE EXECUTION ----------------
async def execute_paper_trade(symbol, side):
    """Simulate or place a paper trade on Binance Testnet."""
    try:
        market = symbol.replace("USDT", "/USDT")
        ticker = exchange.fetch_ticker(market)
        current_price = ticker["last"]

        # Calculate position size in base currency
        qty = round(TRADE_SIZE_USDT / current_price, 3)

        # Determine TP/SL levels
        if side == "BUY":
            tp_price = current_price * (1 + TARGET_PROFIT)
            sl_price = current_price * (1 - STOP_LOSS)
        else:
            tp_price = current_price * (1 - TARGET_PROFIT)
            sl_price = current_price * (1 + STOP_LOSS)

        print(f"\n📈 {side} {qty} {symbol} @ {current_price}")
        print(f"🎯 Take-Profit: {tp_price:.4f} | 🛑 Stop-Loss: {sl_price:.4f}")

        # --- Place orders on testnet (market + OCO TP/SL) ---
        exchange.create_market_order(market, side, qty)

        opposite_side = "SELL" if side == "BUY" else "BUY"
        # OCO (One Cancels Other) TP/SL setup
        exchange.create_order(market, "TAKE_PROFIT_MARKET", opposite_side, qty, None, {"stopPrice": tp_price})
        exchange.create_order(market, "STOP_MARKET", opposite_side, qty, None, {"stopPrice": sl_price})

        print("✅ Paper trade executed successfully on Binance Testnet!\n")

    except Exception as e:
        print(f"Trade execution error for {symbol}: {e}")

# -------------- LIQUIDATION ANALYZER ----------------
async def analyze_recent_liquidations():
    """Scan the last 2 minutes of liquidations per symbol."""
    now = datetime.utcnow()

    for symbol, events in liq_data.items():
        recent = [e for e in events if now - e["time"] <= timedelta(minutes=WINDOW_MINUTES)]
        if not recent:
            continue

        buys = sum(1 for e in recent if e["side"] == "BUY")
        sells = sum(1 for e in recent if e["side"] == "SELL")

        # SHORT criteria: 7+ sells, 0 buys
        if sells >= 7 and buys == 0:
            await analyze_with_bollinger(symbol, "short")

        # LONG criteria: 7+ buys, 0 sells
        if buys >= 7 and sells == 0:
            await analyze_with_bollinger(symbol, "long")

# -------------- WEBSOCKET HANDLER ----------------
async def handle_ws_stream(symbols):
    """Stream and store liquidation data for each group of symbols."""
    stream_names = [f"{sym.lower()}@forceOrder" for sym in symbols]
    url = WS_URL + "/".join(stream_names)

    while True:
        try:
            async with websockets.connect(url, ping_interval=60, ping_timeout=10) as ws:
                print(f"[{datetime.utcnow().isoformat()}] Connected to {len(symbols)} symbols.")

                async for msg in ws:
                    liq = parse_force_order(msg)
                    if not liq:
                        continue

                    # Print formatted liquidation
                    ts = datetime.utcfromtimestamp(liq["trade_time"]/1000.0).strftime("%H:%M:%S")
                    print(f"{ts} | {liq['symbol']} | {liq['side']} | {liq['filled_qty']:.3f} @ {liq['avg_price']:.3f} → ${liq['usd_value']:.0f}")

                    # Store for analysis
                    event = {
                        "side": liq["side"],
                        "time": datetime.utcfromtimestamp(liq["trade_time"]/1000.0),
                        "price": liq["avg_price"],
                        "qty": liq["filled_qty"]
                    }
                    liq_data[liq["symbol"]].append(event)
                    await append_to_csv(liq)

        except Exception as e:
            print(f"[{datetime.utcnow().isoformat()}] Reconnecting due to: {e}")
            await asyncio.sleep(3)

# -------------- MAIN ----------------
async def main():
    symbols = await fetch_symbols()
    await write_csv_header()

    # Split into multiple websocket groups
    groups = [symbols[i:i+MAX_STREAMS_PER_CONN] for i in range(0, len(symbols), MAX_STREAMS_PER_CONN)]

    print(f"Tracking {len(symbols)} symbols across {len(groups)} WebSocket connections...")

    async def periodic_analysis():
        """Run the liquidation analyzer every minute."""
        while True:
            await analyze_recent_liquidations()
            await asyncio.sleep(60)

    # Launch WS streams + analyzer
    tasks = [handle_ws_stream(g) for g in groups] + [periodic_analysis()]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exited cleanly.")