# requirements:
# pip install websockets aiofiles
# Python 3.8+

import asyncio
import json
import csv
from datetime import datetime
import aiofiles
import websockets

# websocket endpoint for USDⓈ-M futures market (all-market liquidation stream)
WS_URL = "wss://fstream.binance.com/ws/!forceOrder@arr"

# keep N most recent liquidations in memory
MAX_HISTORY = 1000

# optional: minimum liquidation USD value to print/store
MIN_USD_VALUE = 1000.0

# output CSV file (set to None to disable file writing)
CSV_FILE = "binance_liquidations.csv"

recent_liqs = []

def parse_message(msg_text):
    """Parse incoming websocket message. Returns list of liquidation dicts (sometimes wrapped)."""
    data = json.loads(msg_text)

    # handle combined stream wrapper {"stream": "...", "data": {...}}
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict) and data["data"].get("e") == "forceOrder":
        payload = data["data"]
    # direct payload {"e":"forceOrder", "E":..., "o":{...}}
    elif isinstance(data, dict) and data.get("e") == "forceOrder":
        payload = data
    # there may be other wrapper shapes (safety)
    else:
        # try scanning for forceOrder inside
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, dict) and v.get("e") == "forceOrder":
                    payload = v
                    break
            else:
                return []
        else:
            return []

    o = payload.get("o", {})  # the order object
    # fields: s (symbol), ps (pair), S (side), p (price), ap (avg price), q, l, z, T (tradeTime)
    try:
        symbol = o.get("s")
        pair = o.get("ps")
        side = o.get("S")
        order_type = o.get("o")
        avg_price = float(o.get("ap") or 0)
        filled_qty = float(o.get("z") or 0)      # z: filled accumulated qty
        last_fill_qty = float(o.get("l") or 0)   # l: last filled qty
        price = float(o.get("p") or 0)
        trade_time = int(o.get("T") or payload.get("E") or 0)
    except Exception:
        return []

    usd_value = avg_price * filled_qty if avg_price and filled_qty else price * filled_qty

    liq = {
        "event_time": payload.get("E"),
        "trade_time": trade_time,
        "symbol": symbol,
        "pair": pair,
        "side": side,
        "order_type": order_type,
        "price": price,
        "avg_price": avg_price,
        "filled_qty": filled_qty,
        "last_fill_qty": last_fill_qty,
        "usd_value": usd_value
    }
    return [liq]

async def write_csv_header_if_needed(path):
    # ensure header exists
    try:
        async with aiofiles.open(path, mode="r") as f:
            await f.readline()
    except FileNotFoundError:
        async with aiofiles.open(path, mode="w") as f:
            await f.write("timestamp,symbol,side,avg_price,filled_qty,usd_value,order_type\n")

async def append_to_csv(path, liq):
    async with aiofiles.open(path, mode="a") as f:
        ts = datetime.utcfromtimestamp(liq["trade_time"]/1000.0).isoformat()
        row = f'{ts},{liq["symbol"]},{liq["side"]},{liq["avg_price"]},{liq["filled_qty"]},{liq["usd_value"]},{liq["order_type"]}\n'
        await f.write(row)

async def consumer_handler():
    global recent_liqs
    # reconnect loop
    while True:
        try:
            async with websockets.connect(WS_URL, ping_interval=60, ping_timeout=10) as ws:
                print(f"[{datetime.utcnow().isoformat()}] Connected to Binance futures liquidation stream.")
                # prepare CSV
                if CSV_FILE:
                    await write_csv_header_if_needed(CSV_FILE)

                async for message in ws:
                    liqs = parse_message(message)
                    if not liqs:
                        continue
                    for liq in liqs:
                        # filter by min usd value
                        if liq["usd_value"] < MIN_USD_VALUE:
                            # ignore small liquidations (optional)
                            continue

                        # push to in-memory list (bounded)
                        recent_liqs.append(liq)
                        if len(recent_liqs) > MAX_HISTORY:
                            recent_liqs = recent_liqs[-MAX_HISTORY:]

                        # print nicely
                        t = datetime.utcfromtimestamp(liq["trade_time"]/1000.0).strftime("%Y-%m-%d %H:%M:%S")
                        print(f"{t} {liq['symbol']} {liq['side']} {liq['filled_qty']:.4f} @ avg {liq['avg_price']:.2f} -> ${liq['usd_value']:.2f}")

                        # append to CSV if enabled
                        if CSV_FILE:
                            await append_to_csv(CSV_FILE, liq)

        except Exception as e:
            print(f"[{datetime.utcnow().isoformat()}] Connection error / exception: {e}. Reconnecting in 2s...")
            await asyncio.sleep(2)

def get_recent_liquidations(limit=50):
    # helper to expose recent liquidations (call from other coroutine / endpoints)
    return recent_liqs[-limit:]

if __name__ == "__main__":
    try:
        asyncio.run(consumer_handler())
    except KeyboardInterrupt:
        print("Interrupted — exiting")