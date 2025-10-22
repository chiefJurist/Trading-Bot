import asyncio
import json
import aiofiles
import aiohttp
import websockets
import pandas as pd
from datetime import datetime, timedelta
from collections import deque

# Binance Futures endpoints
REST_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
WS_URL = "wss://fstream.binance.com/stream?streams="

# Config
MAX_STREAMS_PER_CONN = 100
CSV_FILE = "binance_liquidations.csv"
WRITE_QUEUE = deque()  # Thread-safe queue for writes

# ---- Utility Functions ----
async def fetch_symbols():
    async with aiohttp.ClientSession() as session:
        async with session.get(REST_URL) as resp:
            data = await resp.json()
            return [s["symbol"] for s in data["symbols"] if s["contractType"] == "PERPETUAL"]

async def write_csv_header():
    try:
        async with aiofiles.open(CSV_FILE, "r") as f:
            await f.readline()
    except FileNotFoundError:
        async with aiofiles.open(CSV_FILE, "w") as f:
            await f.write("timestamp,symbol,side,avg_price,filled_qty,usd_value\n")

async def csv_writer():
    """Background task to safely write queued rows."""
    while True:
        if WRITE_QUEUE:
            row = WRITE_QUEUE.popleft()
            async with aiofiles.open(CSV_FILE, "a") as f:
                await f.write(row + "\n")
        await asyncio.sleep(0.1)  # Poll queue

def queue_csv_row(liq):
    ts = datetime.utcfromtimestamp(liq["trade_time"]/1000.0).isoformat()
    row = f'{ts},{liq["symbol"]},{liq["side"]},{liq["avg_price"]},{liq["filled_qty"]},{liq["usd_value"]}'
    WRITE_QUEUE.append(row)

# ---- Core Parser (Fixed with Validation) ----
def parse_force_order(msg_text):
    try:
        data = json.loads(msg_text)
        payload = data.get("data", {})
        if not payload:  # Skip empty payloads (e.g., pings)
            return None
        o = payload.get("o", {})
        # Validate required fields
        symbol = o.get("s")
        side = o.get("S")
        trade_time = int(o.get("T", payload.get("E", 0)))
        if not all([symbol, side in ["BUY", "SELL"], trade_time > 0]):  # Strict checks
            return None  # Skip invalid/noise
        avg_price = float(o.get("ap", 0))
        filled_qty = float(o.get("z", 0))
        if avg_price <= 0 or filled_qty <= 0:  # Basic sanity
            return None
        usd_value = avg_price * filled_qty
        return {
            "symbol": symbol,
            "side": side,
            "avg_price": avg_price,
            "filled_qty": filled_qty,
            "usd_value": usd_value,
            "trade_time": trade_time
        }
    except Exception:
        return None

# ---- WebSocket Handling ----
async def handle_ws_stream(symbols):
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
                    ts = datetime.utcfromtimestamp(liq["trade_time"]/1000.0).strftime("%H:%M:%S")
                    print(f"{ts} | {liq['symbol']} | {liq['side']} | {liq['filled_qty']:.3f} @ {liq['avg_price']:.3f} → ${liq['usd_value']:.0f}")
                    queue_csv_row(liq)
        except Exception as e:
            print(f"[{datetime.utcnow().isoformat()}] Reconnecting due to: {e}")
            await asyncio.sleep(3)

# ---- Pattern Analysis (Fixed Time Filtering) ----
async def analyze_patterns():
    await asyncio.sleep(10)  # Initial buffer
    while True:
        try:
            now = datetime.utcnow()
            # Sleep to next minute boundary for precise timing
            next_minute = (now.replace(second=0, microsecond=0) + timedelta(minutes=1))
            await asyncio.sleep((next_minute - now).total_seconds())

            now = datetime.utcnow()  # Refresh after sleep
            current_time = now.strftime("%H:%M")
            window_start = now - timedelta(minutes=2)

            if not pd.io.common.file_exists(CSV_FILE):
                continue

            df = pd.read_csv(CSV_FILE)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Precise filter: last 2 full minutes (your spec: ignore seconds, but exact window)
            recent = df[(df['timestamp'] >= window_start) & (df['timestamp'] < now)]

            results = []
            for symbol, group in recent.groupby('symbol'):
                sides = group['side'].value_counts()
                if len(sides) > 1:  # Both sides present
                    continue
                for side, count in sides.items():
                    if count >= 7:
                        results.append([symbol, side, current_time])

            if results:
                print("\nPattern Detected:")
                for r in results:
                    print(r)
            # else: print(f"[{current_time}] No matching patterns.")  # Uncomment for verbose

        except Exception as e:
            print(f"[Pattern Error] {e}")
            await asyncio.sleep(60)

# ---- Main Entrypoint ----
async def main():
    symbols = await fetch_symbols()
    await write_csv_header()

    groups = [symbols[i:i+MAX_STREAMS_PER_CONN] for i in range(0, len(symbols), MAX_STREAMS_PER_CONN)]
    print(f"Tracking {len(symbols)} symbols across {len(groups)} websocket connections...")

    tasks = [handle_ws_stream(g) for g in groups]
    tasks.append(analyze_patterns())
    tasks.append(csv_writer())  # Background writer
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exited cleanly.")