from telethon import TelegramClient

# === Replace with your own ===
api_id = 1234567                   # from my.telegram.org
api_hash = "your_api_hash_here"
channel_name = "name_of_private_channel"  # e.g. the invite link handle, or the internal name

client = TelegramClient("my_session", api_id, api_hash)

async def main():
    await client.start()  # First run will ask for your phone and a login code

    # Fetch the most recent 50 messages
    async for msg in client.iter_messages(channel_name, limit=50):
        if msg.text:
            print(msg.text)

with client:
    client.loop.run_until_complete(main())