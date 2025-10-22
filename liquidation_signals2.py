import asyncio
import json
import aiohttp
import websockets
from datetime import datetime, timedelta
from collections import defaultdict

# Config
MAX_STREAMS_PER_CONN = 100
LIQ_WINDOW_MINUTES = 2
SIGNAL_THRESHOLD = 7

# GLOBAL in-memory storage (THIS IS KEY)
recent_liqs = []

async def fetch_symbols():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://fapi.binance.com/fapi/v1/exchangeInfo") as resp:
            data = await resp.json()
            return [s["symbol"] for s in data["symbols"] if s["contractType"] == "PERPETUAL"]

def parse_force_order(msg_text):
    try:
        data = json.loads(msg_text)
        payload = data.get("data", {})
        o = payload.get("o", {})
        # KEEP UTC (Binance timestamps are UTC)
        return {
            "symbol": o.get("s"),
            "side": o.get("S"),
            "trade_time": datetime.utcfromtimestamp(int(o.get("T", payload.get("E", 0))) / 1000.0)
        }
    except Exception:
        return None

# GLOBAL ANALYSIS (runs once per minute across ALL data)
async def analyze_patterns():
    while True:
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=LIQ_WINDOW_MINUTES)
        
        # Filter recent data
        active_liqs = [liq for liq in recent_liqs if liq["trade_time"] >= cutoff]
        
        # Group ALL data together
        symbols = defaultdict(lambda: {"BUY": 0, "SELL": 0})
        for liq in active_liqs:
            symbols[liq["symbol"]][liq["side"]] += 1
        
        # Single source of truth
        for sym, sides in symbols.items():
            if sides["BUY"] >= SIGNAL_THRESHOLD and sides["SELL"] == 0:
                print(f"{sym} | BUY | {now.strftime('%H:%M')}")
            elif sides["SELL"] >= SIGNAL_THRESHOLD and sides["BUY"] == 0:
                print(f"{sym} | SELL | {now.strftime('%H:%M')}")
        
        recent_liqs[:] = active_liqs  # Keep memory clean
        await asyncio.sleep(60)

async def handle_ws_stream(symbols):
    stream_names = [f"{sym.lower()}@forceOrder" for sym in symbols]
    url = f"wss://fstream.binance.com/stream?streams={'/'.join(stream_names)}"
    while True:
        try:
            async with websockets.connect(url, ping_interval=60, ping_timeout=10) as ws:
                print(f"[{datetime.utcnow().isoformat()}] Connected to {len(symbols)} symbols.")
                async for msg in ws:
                    liq = parse_force_order(msg)
                    if liq:
                        recent_liqs.append(liq)  # ALL connections feed GLOBAL list
        except Exception as e:
            print(f"[{datetime.utcnow().isoformat()}] Reconnecting: {e}")
            await asyncio.sleep(3)

async def main():
    symbols = await fetch_symbols()
    groups = [symbols[i:i+MAX_STREAMS_PER_CONN] for i in range(0, len(symbols), MAX_STREAMS_PER_CONN)]
    print(f"Tracking {len(symbols)} symbols across {len(groups)} connections...")
    
    tasks = [handle_ws_stream(g) for g in groups]
    tasks.append(analyze_patterns())  # ONE global analyzer
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exited cleanly.")