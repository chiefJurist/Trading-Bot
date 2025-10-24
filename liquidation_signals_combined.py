import csv
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import aiofiles
import asyncio

INPUT_FILE = "binance_liquidations.csv"
OUTPUT_FILE = "signals_combined.csv"
TIME_OFFSET = timedelta(hours=1)  # UTC+1

def parse_timestamp(ts):
    """Convert timestamp string to minute-based datetime."""
    dt = datetime.fromisoformat(ts)
    return dt.replace(second=0, microsecond=0)

async def analyze_liquidations():
    # Step 1: Read all rows
    minutes = defaultdict(list)
    
    async with aiofiles.open(INPUT_FILE, "r") as f:
        header = await f.readline()  # skip header
        async for line in f:
            parts = line.strip().split(",")
            if len(parts) < 6:
                continue
            ts, symbol, side, avg_price, qty, usd_value = parts
            minute = parse_timestamp(ts)
            minutes[minute].append({"symbol": symbol, "side": side})

    # Step 2: Sort minute keys
    sorted_minutes = sorted(minutes.keys())

    # Step 3: Prepare output CSV
    async with aiofiles.open(OUTPUT_FILE, "w") as out:
        await out.write("date,time,pair,side,occurrences\n")

        # Step 4: Loop through each minute (skip the first one)
        for i in range(1, len(sorted_minutes)):
            pre_min = sorted_minutes[i - 1]
            main_min = sorted_minutes[i]

            # Combine both minutes' signals
            combined = minutes[pre_min] + minutes[main_min]

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
                        # Apply UTC+1 offset
                        local_time = main_min + TIME_OFFSET
                        await out.write(
                            f"{local_time.date()},{local_time.time().strftime('%H:%M')},{symbol},{side},{count}\n"
                        )

    print(f"Analysis complete. Results saved in {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(analyze_liquidations())