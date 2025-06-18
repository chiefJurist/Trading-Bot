import asyncio
import websockets
import json
from datetime import datetime

BINANCE_WS_URL = "wss://fstream.binance.com/ws/!forceOrder@arr"

def format_liquidation(data):
    order = data["o"]
    symbol = order["s"]
    side = order["S"]
    quantity = float(order["q"])
    price = float(order["ap"])
    timestamp = int(order["T"]) // 1000
    time_str = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')

    return {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
        "timestamp": time_str
    }

async def listen_liquidations():
    async with websockets.connect(BINANCE_WS_URL) as ws:
        print("📡 Listening to Binance Futures Liquidations...\n")
        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            # Each message is a liquidation event
            liquidation = format_liquidation(data)

            print(f"[{liquidation['timestamp']}] {liquidation['symbol']} - "
                  f"{liquidation['side']} - {liquidation['quantity']} @ {liquidation['price']}")

if __name__ == "__main__":
    asyncio.run(listen_liquidations())
