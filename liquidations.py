import asyncio
import json
import aiohttp
import aiofiles
import websockets
from datetime import datetime

# Fetch symbol list
EXCHANGE_INFO_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
MAX_STREAMS_PER_CONN = 150  # leave margin for dual streams
CSV_FILE = "combined_liquidations.csv"
MIN_USD = 100.0  # threshold

async def fetch_symbols():
    async with aiohttp.ClientSession() as session:
        async with session.get(EXCHANGE_INFO_URL) as resp:
            data = await resp.json()
            syms = [
                s["symbol"].lower()
                for s in data["symbols"]
                if s["status"] == "TRADING" and s["quoteAsset"] == "USDT"
            ]
            return syms

async def write_csv_header():
    try:
        async with aiofiles.open(CSV_FILE, "r") as f:
            await f.readline()
    except FileNotFoundError:
        async with aiofiles.open(CSV_FILE, "w") as f:
            await f.write("timestamp,type,symbol,side,qty,price,usd_value,extra\n")

async def append_csv(record: dict):
    async with aiofiles.open(CSV_FILE, "a") as f:
        ts = datetime.utcfromtimestamp(record["time"] / 1000).isoformat()
        line = (
            f'{ts},{record["type"]},{record["symbol"]},{record.get("side","")},'
            f'{record.get("qty",0)},{record.get("price",0)},{record.get("usd_value",0)},'
            f'{record.get("extra","")}\n'
        )
        await f.write(line)

async def parse_force_order(msg):
    # msg is a JSON string
    obj = json.loads(msg)
    data = obj.get("data") or obj
    if data.get("e") != "forceOrder":
        return None
    o = data.get("o", {})
    symbol = o.get("s")
    side = o.get("S")
    avg = float(o.get("ap") or 0)
    qty = float(o.get("z") or 0)
    price = float(o.get("p") or 0)
    trade_time = int(o.get("T") or data.get("E") or 0)
    usd = (avg or price) * qty
    if usd < MIN_USD:
        return None
    return {
        "type": "forceOrder",
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": avg or price,
        "usd_value": usd,
        "time": trade_time,
        "extra": ""
    }

def parse_agg_trade(obj):
    # obj is dict (already parsed). We'll detect aggressive side (maker) as possible liquidation
    # fields: e, E, s, a, p, q, f, l, T, m
    if obj.get("e") != "aggTrade":
        return None
    symbol = obj.get("s")
    price = float(obj.get("p") or 0)
    qty = float(obj.get("q") or 0)
    trade_time = int(obj.get("T") or 0)
    m = obj.get("m", False)  # whether buyer is maker
    # Heuristic: if m == False (so buyer is taker) or large qty, treat as possible liquidation
    # This is heuristic — tune as needed
    # We record side = “SELL” if buyer is maker (i.e. liquidation sell), else “BUY”
    side = "BUY" if (not m) else "SELL"
    usd = price * qty
    if usd < MIN_USD:
        return None
    return {
        "type": "aggTrade",
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": price,
        "usd_value": usd,
        "time": trade_time,
        "extra": f"m={m}"
    }

async def handle_ws_stream(streams: list, mode: str):
    """
    mode = "forceOrder" or "aggTrade"
    streams: list of symbols, e.g., ["btcusdt","ethusdt",...]
    """
    # build combined stream string
    stream_names = []
    for s in streams:
        stream_names.append(f"{s}@{mode}")
    combined = "/".join(stream_names)
    url = f"wss://fstream.binance.com/stream?streams={combined}"
    while True:
        try:
            async with websockets.connect(url, ping_interval=60) as ws:
                print(f"[{mode}] connected to {len(streams)} streams")
                async for msg in ws:
                    msgj = json.loads(msg)
                    data = msgj.get("data")
                    # sometimes top-level direct
                    if mode == "forceOrder":
                        rec = await parse_force_order(msg)
                    else:  # aggTrade
                        # msg is wrapper {"stream": "...", "data": {...}}
                        rec = parse_agg_trade(data or msgj)
                    if rec:
                        await append_csv(rec)
                        # print to console
                        t = datetime.utcfromtimestamp(rec["time"] / 1000).strftime("%H:%M:%S")
                        print(f"{t} | {rec['type']} | {rec['symbol']} | {rec['side']} | {rec['qty']} @ {rec['price']} → ${rec['usd_value']:.0f} {rec.get('extra','')}")
        except Exception as e:
            print(f"[{mode}] error {e}, reconnecting in 3s...")
            await asyncio.sleep(3)

async def main():
    syms = await fetch_symbols()
    await write_csv_header()

    # Split symbols into manageable groups
    # We need to run 2 modes, so maybe half for each or duplicate lists
    groups = [syms[i : i + MAX_STREAMS_PER_CONN] for i in range(0, len(syms), MAX_STREAMS_PER_CONN)]

    tasks = []
    for g in groups:
        tasks.append(handle_ws_stream(g, "forceOrder"))
        tasks.append(handle_ws_stream(g, "aggTrade"))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted.")