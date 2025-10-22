import asyncio
import json
import aiohttp
import websockets
from datetime import datetime, timedelta

# Binance Futures endpoints
REST_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
WS_URL = "wss://fstream.binance.com/stream?streams="

MAX_STREAMS_PER_CONN = 100
LIQ_WINDOW_MINUTES = 2
SIGNAL_THRESHOLD = 7  # at least 7 liquidations on same side, no opposite side

# In-memory storage of recent liquidations
recent_liqs = []

# ---- Utility Functions ----
async def fetch_symbols():
    async with aiohttp.ClientSession() as session:
        async with session.get(REST_URL) as resp:
            data = await resp.json()
            return [s["symbol"] for s in data["symbols"] if s["contractType"] == "PERPETUAL"]

def parse_force_order(msg_text):
    try:
        data = json.loads(msg_text)
        payload = data.get("data", {})
        o = payload.get("o", {})
        return {
            "symbol": o.get("s"),
            "side": o.get("S"),
            "trade_time": datetime.utcfromtimestamp(int(o.get("T", payload.get("E", 0))) / 1000.0)
        }
    except Exception:
        return None

# ---- Pattern Detection ----
async def analyze_patterns():
    while True:
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=LIQ_WINDOW_MINUTES)

        # Keep only recent data (last 2 minutes)
        active_liqs = [liq for liq in recent_liqs if liq["trade_time"] >= cutoff]

        # Group by symbol
        symbols = {}
        for liq in active_liqs:
            sym = liq["symbol"]
            side = liq["side"]
            if sym not in symbols:
                symbols[sym] = {"BUY": 0, "SELL": 0}
            symbols[sym][side] += 1

        # Detect symbols that match the pattern
        for sym, sides in symbols.items():
            if sides["BUY"] >= SIGNAL_THRESHOLD and sides["SELL"] == 0:
                print(f"{sym} | BUY | {now.strftime('%H:%M')}")
            elif sides["SELL"] >= SIGNAL_THRESHOLD and sides["BUY"] == 0:
                print(f"{sym} | SELL | {now.strftime('%H:%M')}")

        # Remove outdated entries to keep memory light
        recent_liqs[:] = active_liqs

        await asyncio.sleep(60)  # wait one minute before checking again

# ---- WebSocket Stream ----
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
                    recent_liqs.append(liq)  # store in memory only
        except Exception as e:
            print(f"[{datetime.utcnow().isoformat()}] Reconnecting due to: {e}")
            await asyncio.sleep(3)

# ---- Main Entrypoint ----
async def main():
    symbols = await fetch_symbols()
    groups = [symbols[i:i+MAX_STREAMS_PER_CONN] for i in range(0, len(symbols), MAX_STREAMS_PER_CONN)]
    print(f"Tracking {len(symbols)} symbols across {len(groups)} websocket connections...")

    tasks = [handle_ws_stream(g) for g in groups]
    tasks.append(analyze_patterns())
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exited cleanly.")