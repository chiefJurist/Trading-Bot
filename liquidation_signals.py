import asyncio
import json
import aiofiles
import aiohttp
import websockets
from datetime import datetime, timedelta

# Binance Futures endpoints
REST_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
WS_URL = "wss://fstream.binance.com/stream?streams="

# Config
MAX_STREAMS_PER_CONN = 100  # Binance limits 200 per connection
LIQ_WINDOW_SECONDS = 120     # 2 minutes
MIN_LIQ_COUNT = 7            # threshold of buys/sells to consider a signal
CSV_FILE = "binance_liquidations.csv"

# ---- Utility Functions ----
async def fetch_symbols():
    """Fetch all USDⓈ-M futures trading pairs."""
    async with aiohttp.ClientSession() as session:
        async with session.get(REST_URL) as resp:
            data = await resp.json()
            return [s["symbol"] for s in data["symbols"] if s["contractType"] == "PERPETUAL"]

async def write_csv_header():
    """Ensure CSV file has header."""
    try:
        async with aiofiles.open(CSV_FILE, "r") as f:
            await f.readline()
    except FileNotFoundError:
        async with aiofiles.open(CSV_FILE, "w") as f:
            await f.write("timestamp,symbol,side,avg_price,filled_qty,usd_value\n")

async def append_to_csv(liq):
    """Append liquidation info to CSV."""
    async with aiofiles.open(CSV_FILE, "a") as f:
        ts = datetime.utcfromtimestamp(liq["trade_time"]/1000.0).isoformat()
        row = f'{ts},{liq["symbol"]},{liq["side"]},{liq["avg_price"]},{liq["filled_qty"]},{liq["usd_value"]}\n'
        await f.write(row)

# ---- Core Parser ----
def parse_force_order(msg_text):
    """Extract liquidation data from forceOrder event."""
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

# ---- WebSocket Handling ----
async def handle_ws_stream(symbols, liq_queue):
    """Track liquidations for a batch of symbols and push them to a queue."""
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

                    # append to CSV
                    await append_to_csv(liq)
                    # push into in-memory queue for analysis
                    await liq_queue.put(liq)

        except Exception as e:
            print(f"[{datetime.utcnow().isoformat()}] Reconnecting due to: {e}")
            await asyncio.sleep(3)

# ---- Analysis ----
async def analyze_liquidations(liq_queue):
    """Analyze liquidations every second for long/short signals."""
    buffer = []

    while True:
        try:
            # wait for a new liquidation, with timeout to allow periodic analysis
            liq = await asyncio.wait_for(liq_queue.get(), timeout=1.0)
            buffer.append(liq)
        except asyncio.TimeoutError:
            pass

        # prune buffer to last 2 minutes
        cutoff = datetime.utcnow() - timedelta(seconds=LIQ_WINDOW_SECONDS)
        cutoff_ms = int(cutoff.timestamp() * 1000)
        buffer = [l for l in buffer if l["trade_time"] >= cutoff_ms]

        # count BUY/SELL per symbol
        counts = {}
        for l in buffer:
            sym = l["symbol"]
            side = l["side"]
            if sym not in counts:
                counts[sym] = {"BUY": 0, "SELL": 0}
            counts[sym][side] += 1

        now_str = datetime.utcnow().strftime("%H:%M:%S")

        # analyze short signals (SELL)
        for sym, c in counts.items():
            if c.get("SELL", 0) >= MIN_LIQ_COUNT and c.get("BUY", 0) == 0:
                # no buy orders in timeframe => signal qualified
                print(f"{sym}, Sell, {now_str}")

        # analyze long signals (BUY)
        for sym, c in counts.items():
            if c.get("BUY", 0) >= MIN_LIQ_COUNT and c.get("SELL", 0) == 0:
                # no sell orders in timeframe => signal qualified
                print(f"{sym}, Buy, {now_str}")

        await asyncio.sleep(1)  # small delay to avoid busy loop

# ---- Main Entrypoint ----
async def main():
    symbols = await fetch_symbols()
    await write_csv_header()

    liq_queue = asyncio.Queue()

    # split symbols for multiple websocket connections
    groups = [symbols[i:i+MAX_STREAMS_PER_CONN] for i in range(0, len(symbols), MAX_STREAMS_PER_CONN)]
    print(f"Tracking {len(symbols)} symbols across {len(groups)} websocket connections...")

    # start websocket producers
    producer_tasks = [asyncio.create_task(handle_ws_stream(g, liq_queue)) for g in groups]
    # start analysis consumer
    consumer_task = asyncio.create_task(analyze_liquidations(liq_queue))

    await asyncio.gather(*producer_tasks, consumer_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exited cleanly.")