import asyncio
import json
import aiohttp
import websockets
from datetime import datetime
from collections import defaultdict

# Binance Futures endpoints
REST_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
WS_URL = "wss://fstream.binance.com/stream?streams="

# Telegram Config
TELEGRAM_BOT_TOKEN = "8567226515:AAGq-HYbDTk-oKZAzy6mRmAdvPDKWM1OWNY"
TELEGRAM_CHAT_ID = "@binance_liqs"  # or numeric ID like -100xxxxxxxxxx

# Config
MAX_STREAMS_PER_CONN = 100
BATCH_INTERVAL = 30  # seconds between grouped Telegram sends


# ---- Utility ----
async def fetch_symbols():
    """Fetch all USDⓈ-M perpetual futures symbols."""
    async with aiohttp.ClientSession() as session:
        async with session.get(REST_URL) as resp:
            data = await resp.json()
            return [s["symbol"] for s in data["symbols"] if s["contractType"] == "PERPETUAL"]


# ---- Telegram ----
async def send_telegram_message(text):
    """Send message to Telegram channel."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                print(f"Telegram error: {resp.status}")


# ---- Parser ----
def parse_force_order(msg_text):
    """Extract liquidation data from Binance forceOrder events."""
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
            "trade_time": int(o.get("T", payload.get("E", 0))),
        }
    except Exception:
        return None


# ---- WebSocket Handler ----
async def handle_ws_stream(symbols):
    stream_names = [f"{sym.lower()}@forceOrder" for sym in symbols]
    url = WS_URL + "/".join(stream_names)
    pending_msgs = defaultdict(list)

    async def flush_messages():
        """Periodically send grouped liquidation messages."""
        while True:
            await asyncio.sleep(BATCH_INTERVAL)
            if not pending_msgs:
                continue

            for key, msgs in list(pending_msgs.items()):
                text = "\n\n".join(msgs[:20])  # limit size
                del pending_msgs[key]
                header = f"🔥 <b>Liquidations ({key} UTC)</b> 🔥\n\n"
                await send_telegram_message(header + text)
                await asyncio.sleep(1)  # small gap to stay below rate limit

    asyncio.create_task(flush_messages())

    while True:
        try:
            async with websockets.connect(url, ping_interval=60, ping_timeout=10) as ws:
                print(f"[{datetime.utcnow().isoformat()}] Connected to {len(symbols)} symbols.")
                async for msg in ws:
                    liq = parse_force_order(msg)
                    if not liq:
                        continue

                    ts = datetime.utcfromtimestamp(liq["trade_time"] / 1000.0)
                    minute_key = ts.strftime("%H:%M")
                    if liq['side'] == 'SELL':
                        text = (
                            f"💥🔴 <b>{liq['symbol']}</b> | {liq['side']}\n"
                            f"Qty: <b>{liq['filled_qty']:.3f}</b>\n"
                            f"Price: <b>{liq['avg_price']:.4f}</b>\n"
                            f"Value: <b>${liq['usd_value']:.0f}</b>"
                        )
                    else:
                        text = (
                            f"💥🟢 <b>{liq['symbol']}</b> | {liq['side']}\n"
                            f"Qty: <b>{liq['filled_qty']:.3f}</b>\n"
                            f"Price: <b>{liq['avg_price']:.4f}</b>\n"
                            f"Value: <b>${liq['usd_value']:.0f}</b>"
                        )
                    pending_msgs[minute_key].append(text)

        except Exception as e:
            print(f"[{datetime.utcnow().isoformat()}] Reconnecting due to: {e}")
            await asyncio.sleep(3)


# ---- Main Entrypoint ----
async def main():
    symbols = await fetch_symbols()
    groups = [symbols[i:i + MAX_STREAMS_PER_CONN] for i in range(0, len(symbols), MAX_STREAMS_PER_CONN)]

    print(f"Tracking {len(symbols)} symbols across {len(groups)} websocket connections...")

    tasks = [handle_ws_stream(g) for g in groups]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exited cleanly.")