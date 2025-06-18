import asyncio
import websockets
import json
from datetime import datetime, timezone

BINANCE_WS_URL = "wss://fstream.binance.com/ws/!forceOrder@arr"
MIN_USD_VALUE = 10000  # Minimum liquidation value to display

def format_liquidation(data):
    order = data["o"]
    symbol = order["s"]
    side = order["S"]
    quantity = float(order["q"])      # Base asset (e.g., BTC, ETH)
    price = float(order["ap"])        # Price in USDT
    value = quantity * price          # USD value of the liquidation
    timestamp = int(order["T"]) // 1000
    time_str = datetime.fromtimestamp(timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    return {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
        "value": value,
        "timestamp": time_str
    }

async def listen_liquidations():
    async with websockets.connect(BINANCE_WS_URL) as ws:
        print(f"📡 Listening to Binance Futures Liquidations > ${MIN_USD_VALUE:,}...\n")
        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            liquidation = format_liquidation(data)

            if liquidation["value"] >= MIN_USD_VALUE:
                print(f"[{liquidation['timestamp']}] {liquidation['symbol']} - "
                      f"{liquidation['side']} - {liquidation['quantity']} @ {liquidation['price']} "
                      f"= ${liquidation['value']:,.2f}")

if __name__ == "__main__":
    asyncio.run(listen_liquidations())