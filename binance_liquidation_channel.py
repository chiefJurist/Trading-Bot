import asyncio
import json
import aiohttp
import websockets
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# Binance Futures endpoints
REST_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
WS_URL = "wss://fstream.binance.com/stream?streams="

# Telegram Config
TELEGRAM_BOT_TOKEN = "8567226515:AAGq-HYbDTk-oKZAzy6mRmAdvPDKWM1OWNY"
TELEGRAM_CHAT_ID = "@binance_liqs"

# Config
MAX_STREAMS_PER_CONN = 100
FLUSH_INTERVAL = 60  # seconds
LOCAL_TZ = timezone(timedelta(hours=1))  # adjust offset if needed
MAX_TELEGRAM_LENGTH = 3900  # keep safe margin from 4096 char limit


# ---- Utility ----
async def fetch_symbols():
    """Fetch all USDⓈ-M perpetual futures symbols."""
    async with aiohttp.ClientSession() as session:
        async with session.get(REST_URL) as resp:
            data = await resp.json()
            return [s["symbol"] for s in data["symbols"] if s["contractType"] == "PERPETUAL"]


# ---- Telegram ----
async def send_telegram_message(text: str):
    """Send message to Telegram channel."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                print(f"Telegram error: {resp.status}")


async def send_long_message(full_text: str):
    """Automatically split long text into multiple Telegram messages."""
    if len(full_text) <= MAX_TELEGRAM_LENGTH:
        await send_telegram_message(full_text)
        return

    # Split intelligently by paragraph
    chunks = []
    current_chunk = ""

    for line in full_text.split("\n\n"):
        if len(current_chunk) + len(line) + 2 > MAX_TELEGRAM_LENGTH:
            chunks.append(current_chunk.strip())
            current_chunk = line + "\n\n"
        else:
            current_chunk += line + "\n\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Send each chunk sequentially
    for i, chunk in enumerate(chunks, 1):
        suffix = f"\n\n📄 Part {i}/{len(chunks)}"
        await send_telegram_message(chunk + suffix)
        await asyncio.sleep(1)


# ---- Parser ----
def parse_force_order(msg_text: str):
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
        """Send all collected liquidations once per minute."""
        while True:
            await asyncio.sleep(FLUSH_INTERVAL)
            if not pending_msgs:
                continue

            # Process and clear pending messages
            for minute_key, msgs in list(pending_msgs.items()):
                if not msgs:
                    continue

                local_time = datetime.strptime(minute_key, "%H:%M").strftime("%I:%M %p")
                header = f"🔥 <b>Binance Liquidations</b> 🔥\n\n🕒 <b>{local_time} Local Time</b>\n\n\n"
                text = header + "\n\n".join(msgs)
                del pending_msgs[minute_key]

                await send_long_message(text)
                await asyncio.sleep(2)

    asyncio.create_task(flush_messages())

    while True:
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                print(f"[{datetime.now().isoformat()}] Connected to {len(symbols)} symbols.")
                async for msg in ws:
                    liq = parse_force_order(msg)
                    if not liq:
                        continue

                    # Convert to local time and group by minute
                    ts = datetime.fromtimestamp(liq["trade_time"] / 1000.0, tz=LOCAL_TZ)
                    minute_key = ts.strftime("%H:%M")

                    # Message format
                    if liq['side'] == 'SELL':
                        text = (
                            f"💥🔴 <b>{liq['symbol']}</b> | SELL\n"
                            f"Qty: <b>{liq['filled_qty']:.3f}</b>\n"
                            f"Price: <b>{liq['avg_price']:.4f}</b>\n"
                            f"Value: <b>${liq['usd_value']:.0f}</b>"
                        )
                    else:
                        text = (
                            f"💥🟢 <b>{liq['symbol']}</b> | BUY\n"
                            f"Qty: <b>{liq['filled_qty']:.3f}</b>\n"
                            f"Price: <b>{liq['avg_price']:.4f}</b>\n"
                            f"Value: <b>${liq['usd_value']:.0f}</b>"
                        )

                    pending_msgs[minute_key].append(text)

        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Reconnecting due to: {e}")
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