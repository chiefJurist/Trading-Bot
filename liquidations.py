# requirements:
# pip install aiohttp websockets aiofiles
# Python 3.8+

import asyncio
import json
from datetime import datetime
import aiohttp
import aiofiles
import websockets

# Binance Futures REST endpoint to get all trading pairs
EXCHANGE_INFO_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"

# Max number of streams per websocket connection allowed by Binance
MAX_STREAMS_PER_CONN = 200

# Output CSV file (set to None to disable)
CSV_FILE = "all_binance_liquidations.csv"

# Minimum liquidation value in USD to display (optional filter)
MIN_USD_VALUE = 500.0


async def fetch_symbols():
    """Fetch all active USDT futures symbols."""
    async with aiohttp.ClientSession() as session:
        async with session.get(EXCHANGE_INFO_URL) as resp:
            data = await resp.json()
            symbols = [
                s["symbol"].lower()
                for s in data["symbols"]
                if s["status"] == "TRADING" and s["quoteAsset"] == "USDT"
            ]
            print(f"Fetched {len(symbols)} USDT pairs.")
            return symbols


async def write_csv_header_if_needed():
    """Create CSV header if not exists."""
    try:
        async with aiofiles.open(CSV_FILE, mode="r") as f:
            await f.readline()
    except FileNotFoundError:
        async with aiofiles.open(CSV_FILE, mode="w") as f:
            await f.write("timestamp,symbol,side,avg_price,filled_qty,usd_value,order_type\n")


async def append_to_csv(liq):
    """Append liquidation entry to CSV."""
    async with aiofiles.open(CSV_FILE, mode="a") as f:
        ts = datetime.utcfromtimestamp(liq["trade_time"]/1000.0).isoformat()
        row = f'{ts},{liq["symbol"]},{liq["side"]},{liq["avg_price"]},{liq["filled_qty"]},{liq["usd_value"]},{liq["order_type"]}\n'
        await f.write(row)


async def handle_message(message):
    """Parse a single message."""
    msg = json.loads(message)
    data = msg.get("data") or msg

    if not isinstance(data, dict):
        return

    if data.get("e") != "forceOrder":
        return

    o = data.get("o", {})
    try:
        symbol = o.get("s")
        side = o.get("S")
        avg_price = float(o.get("ap") or 0)
        qty = float(o.get("z") or 0)
        price = float(o.get("p") or 0)
        order_type = o.get("o")
        trade_time = int(o.get("T") or data.get("E"))
        usd_value = (avg_price or price) * qty
    except Exception:
        return

    if usd_value < MIN_USD_VALUE:
        return

    t = datetime.utcfromtimestamp(trade_time / 1000.0).strftime("%H:%M:%S")
    print(f"{t} | {symbol} | {side} | {qty:.3f} @ {avg_price:.3f} → ${usd_value:,.0f}")

    if CSV_FILE:
        liq = {
            "symbol": symbol,
            "side": side,
            "avg_price": avg_price,
            "filled_qty": qty,
            "usd_value": usd_value,
            "order_type": order_type,
            "trade_time": trade_time
        }
        await append_to_csv(liq)


async def listen_stream_group(symbols):
    """Listen to a group of symbols (<=200) in one combined stream."""
    streams = "/".join(f"{s}@forceOrder" for s in symbols)
    ws_url = f"wss://fstream.binance.com/stream?streams={streams}"

    while True:
        try:
            async with websockets.connect(ws_url, ping_interval=60) as ws:
                print(f"Connected to {len(symbols)} streams...")
                async for msg in ws:
                    await handle_message(msg)
        except Exception as e:
            print(f"Connection error ({e}) — reconnecting in 3s...")
            await asyncio.sleep(3)


async def main():
    symbols = await fetch_symbols()

    if CSV_FILE:
        await write_csv_header_if_needed()

    # Split symbols into groups of <=200
    groups = [symbols[i:i + MAX_STREAMS_PER_CONN] for i in range(0, len(symbols), MAX_STREAMS_PER_CONN)]
    print(f"Creating {len(groups)} websocket connections...")

    # Run all listeners concurrently
    await asyncio.gather(*(listen_stream_group(g) for g in groups))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")
