# live_signal_generator.py
import csv
import os
import time
from datetime import datetime, timedelta
from collections import defaultdict

SOURCE_FILE = "binance_liquidations.csv"
SIGNALS_FILE = "signals.csv"
CHECK_EVERY_SECONDS = 15

# Timezone: your local time = UTC+1
TZ_OFFSET = timedelta(hours=1)

# Track last processed file size and current minute state
last_size = 0
current_minute_data = defaultdict(lambda: {"BUY": 0, "SELL": 0})
current_minute = None

def get_file_size():
    return os.path.getsize(SOURCE_FILE) if os.path.exists(SOURCE_FILE) else 0

def append_signal(date_str, time_str, symbol, side, count):
    with open(SIGNALS_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        # Write header only if file is empty
        if os.path.getsize(SIGNALS_FILE) == 0:
            writer.writerow(["date", "time", "pair", "side", "occurrences"])
        writer.writerow([date_str, time_str, symbol, side, count])
    print(f"NEW SIGNAL → {date_str} {time_str} | {symbol} | {side} | {count} liquidations")

def process_new_lines():
    global last_size, current_minute, current_minute_data

    current_size = get_file_size()
    if current_size == last_size:
        return  # No new data

    with open(SOURCE_FILE, "r") as f:
        f.seek(last_size)  # Jump to where we left off
        reader = csv.DictReader(f)
        new_rows = list(reader)

    if not new_rows:
        last_size = current_size
        return

    for row in new_rows:
        try:
            dt_utc = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            dt_local = dt_utc + TZ_OFFSET
            minute = dt_local.replace(second=0, microsecond=0)

            symbol = row["symbol"]
            side = row["side"].upper().strip()

            # If minute changed → check previous minute for signal
            if current_minute and minute != current_minute:
                check_and_emit_signal(current_minute)

            # Update current minute
            current_minute = minute
            current_minute_data[(minute, symbol)][side] += 1

        except Exception as e:
            print("Bad row:", e)

    last_size = current_size

def check_and_emit_signal(minute):
    global current_minute_data
    for (min_time, symbol), counts in current_minute_data.items():
        if min_time != minute:
            continue
        buy = counts["BUY"]
        sell = counts["SELL"]
        if buy >= 7 and sell == 0:
            append_signal(minute.strftime("%Y-%m-%d"), minute.strftime("%H:%M"), symbol, "BUY", buy)
        elif sell >= 7 and buy == 0:
            append_signal(minute.strftime("%Y-%m-%d"), minute.strftime("%H:%M"), symbol, "SELL", sell)
    # Clear data for this minute
    current_minute_data.clear()

print("LIVE SIGNAL GENERATOR STARTED – Watching binance_liquidations.csv → signals.csv")
print("Press Ctrl+C to stop")

# Create signals.csv with header if doesn't exist
if not os.path.exists(SIGNALS_FILE):
    with open(SIGNALS_FILE, "w", newline="") as f:
        csv.writer(f).writerow(["date", "time", "pair", "side", "occurrences"])

last_size = get_file_size()

try:
    while True:
        process_new_lines()
        # Also check every 60 seconds in case the minute rolled over with no new lines
        now_local = datetime.now() + TZ_OFFSET
        now_minute = now_local.replace(second=0, microsecond=0)
        if current_minute and now_minute > current_minute:
            check_and_emit_signal(current_minute)
            current_minute = now_minute

        time.sleep(CHECK_EVERY_SECONDS)
except KeyboardInterrupt:
    print("\nLive signal generator stopped.")