import asyncio
import json
import aiohttp
import websockets
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# Binance Futures endpoints
REST_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
WS_URL = "wss://fstream.binance.com/stream?streams="

# Config
MAX_STREAMS_PER_CONN = 100  # Binance allows up to 200; 100 for stability
LIQ_WINDOW_MINUTES = 2
MIN_COUNT = 7
LOCAL_TZ = timezone(timedelta(hours=1))  # UTC+1

# ---- Fetch all perpetual futures symbols ----
async def fetch_symbols():
    async with aiohttp.ClientSession() as session:
        async with session.get(REST_URL) as resp:
            data = await resp.json()
            return [s["symbol"] for s in data["symbols"] if s["contractType"] == "PERPETUAL"]

# ---- Parse each liquidation message ----
def parse_force_order(msg_text):
    try:
        data = json.loads(msg_text)
        payload = data.get("data", {})
        o = payload.get("o", {})

        trade_time = datetime.fromtimestamp(o.get("T", payload.get("E", 0)) / 1000.0, LOCAL_TZ)
        return {
            "symbol": o.get("s"),
            "side": o.get("S"),
            "trade_time": trade_time
        }
    except Exception:
        return None

# ---- WebSocket handler for a batch of symbols ----
async def handle_ws_stream(symbols):
    stream_names = [f"{sym.lower()}@forceOrder" for sym in symbols]
    url = WS_URL + "/".join(stream_names)
    liq_buffer = []
    last_checked = datetime.now(LOCAL_TZ)

    while True:
        try:
            async with websockets.connect(url, ping_interval=60, ping_timeout=10) as ws:
                print(f"[{datetime.now(LOCAL_TZ).isoformat()}] Connected to {len(symbols)} symbols.")
                async for msg in ws:
                    liq = parse_force_order(msg)
                    if not liq:
                        continue
                    liq_buffer.append(liq)

                    # Run analysis once per minute
                    now = datetime.now(LOCAL_TZ)
                    if (now - last_checked).total_seconds() >= 60:
                        cutoff = now - timedelta(minutes=LIQ_WINDOW_MINUTES)
                        recent_liqs = [l for l in liq_buffer if l["trade_time"] >= cutoff]
                        liq_buffer = recent_liqs  # keep buffer only for last 2 mins

                        # Group by (symbol, side)
                        counts = defaultdict(int)
                        sides_by_symbol = defaultdict(set)
                        for l in recent_liqs:
                            counts[(l["symbol"], l["side"])] += 1
                            sides_by_symbol[l["symbol"]].add(l["side"])

                        # Analyze results
                        for (sym, side), count in counts.items():
                            # Only print if >=7 same-side signals, and no opposite side
                            if count >= MIN_COUNT and len(sides_by_symbol[sym]) == 1:
                                print(f"{sym} | {side} | {now.strftime('%H:%M')}")

                        last_checked = now

        except Exception as e:
            print(f"[{datetime.now(LOCAL_TZ).isoformat()}] Reconnecting due to error: {e}")
            await asyncio.sleep(3)

# ---- Main entrypoint ----
async def main():
    symbols = await fetch_symbols()
    groups = [symbols[i:i + MAX_STREAMS_PER_CONN] for i in range(0, len(symbols), MAX_STREAMS_PER_CONN)]

    print(f"Tracking {len(symbols)} symbols across {len(groups)} websocket connections...")
    tasks = [handle_ws_stream(group) for group in groups]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exited cleanly.")