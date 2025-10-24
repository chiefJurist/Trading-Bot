import csv
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import aiofiles
import asyncio

INPUT_FILE = "binance_liquidations.csv"
OUTPUT_FILE = "signals.csv"

def parse_timestamp(ts):
    """Convert timestamp string to minute-based datetime floored to start of minute."""
    dt = datetime.fromisoformat(ts)
    return dt.replace(second=0, microsecond=0)

async def analyze_liquidations():
    # Step 1: Read all rows and group by minute-start
    minutes = defaultdict(list)

    async with aiofiles.open(INPUT_FILE, "r") as f:
        header = await f.readline()  # skip header
        async for line in f:
            parts = line.strip().split(",")
            if len(parts) < 6:
                continue
            ts, symbol, side, avg_price, qty, usd_value = parts
            minute_start = parse_timestamp(ts)
            minutes[minute_start].append({"symbol": symbol, "side": side})

    # Step 2: Sort minute keys
    sorted_minutes = sorted(minutes.keys())

    # Step 3: Prepare output CSV
    async with aiofiles.open(OUTPUT_FILE, "w") as out:
        await out.write("date,time,pair,side,occurrences\n")

        # Step 4: Loop through each main window (skip the first one, as it lacks a full pre-window)
        for i in range(1, len(sorted_minutes)):
            pre_start = sorted_minutes[i - 1]
            main_start = sorted_minutes[i]

            # Define full 60s windows (no overlap)
            pre_window_start = pre_start
            pre_window_end = pre_start + timedelta(minutes=1)
            main_window_start = main_start
            main_window_end = main_start + timedelta(minutes=1)

            # Collect events in pre-window
            pre_events = []
            for minute_key in sorted_minutes:
                if pre_window_start <= minute_key < pre_window_end:
                    pre_events.extend(minutes[minute_key])

            # Collect events in main-window
            main_events = []
            for minute_key in sorted_minutes:
                if main_window_start <= minute_key < main_window_end:
                    main_events.extend(minutes[minute_key])

            # Combine both windows' signals
            combined = pre_events + main_events

            # Count occurrences per (symbol, side)
            counts = Counter((row["symbol"], row["side"]) for row in combined)

            # Step 5: Check for qualifying signals
            for (symbol, side), count in counts.items():
                if count >= 7:
                    # Check for any opposing side in same period
                    opposite_side = "BUY" if side == "SELL" else "SELL"
                    has_opposite = any(
                        r["symbol"] == symbol and r["side"] == opposite_side
                        for r in combined
                    )
                    if not has_opposite:
                        # Use main window's start for output
                        await out.write(
                            f"{main_start.date()},{main_start.time().strftime('%H:%M')},{symbol},{side},{count}\n"
                        )

    print(f"✅ Analysis complete. Results saved in {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(analyze_liquidations())