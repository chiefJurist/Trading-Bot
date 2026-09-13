import argparse
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import aiofiles

INPUT_FILE = "binance_liquidations.csv"
TIME_OFFSET = timedelta(hours=1)  # UTC+1 — adjust to your local timezone
THRESHOLD = 7                     # minimum same-side liquidations to qualify as a signal


def parse_timestamp(ts):
    """Convert timestamp string to minute-based datetime (drops seconds/microseconds)."""
    dt = datetime.fromisoformat(ts)
    return dt.replace(second=0, microsecond=0)


async def load_liquidations():
    """Read the raw liquidation CSV into {minute: [ {symbol, side}, ... ]}."""
    minutes = defaultdict(list)

    async with aiofiles.open(INPUT_FILE, "r") as f:
        await f.readline()  # skip header
        async for line in f:
            parts = line.strip().split(",")
            if len(parts) < 6:
                continue
            ts, symbol, side, avg_price, qty, usd_value = parts
            minute = parse_timestamp(ts)
            minutes[minute].append({"symbol": symbol, "side": side})

    return minutes


async def analyze_liquidations(window_minutes, output_file):
    """
    Group liquidations into rolling windows of `window_minutes` and flag
    any (symbol, side) combination that hits THRESHOLD occurrences with
    zero opposite-side activity in the same window.

    window_minutes=1 -> strict single-minute signal (tight timing, may miss
                         cascades that straddle a minute boundary)
    window_minutes=2 -> rolling two-minute signal (catches cascades that
                         straddle a minute boundary, at the cost of looser timing)
    """
    minutes = await load_liquidations()
    sorted_minutes = sorted(minutes.keys())

    async with aiofiles.open(output_file, "w") as out:
        await out.write("date,time,pair,side,occurrences\n")

        for i in range(window_minutes - 1, len(sorted_minutes)):
            window_keys = sorted_minutes[i - (window_minutes - 1): i + 1]
            combined = [row for key in window_keys for row in minutes[key]]

            counts = Counter((row["symbol"], row["side"]) for row in combined)

            for (symbol, side), count in counts.items():
                if count < THRESHOLD:
                    continue

                opposite_side = "BUY" if side == "SELL" else "SELL"
                has_opposite = any(
                    r["symbol"] == symbol and r["side"] == opposite_side
                    for r in combined
                )
                if has_opposite:
                    continue

                local_time = sorted_minutes[i] + TIME_OFFSET
                await out.write(
                    f"{local_time.date()},{local_time.time().strftime('%H:%M')},"
                    f"{symbol},{side},{count}\n"
                )

    print(f"Analysis complete ({window_minutes}-minute window). Results saved in {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Detect one-sided liquidation cascades.")
    parser.add_argument(
        "--window", type=int, choices=[1, 2], default=1,
        help="Grouping window in minutes: 1 = strict per-minute, 2 = rolling two-minute (default: 1)"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output CSV filename (default: signals.csv for window=1, signals_combined.csv for window=2)"
    )
    args = parser.parse_args()

    output_file = args.output or ("signals.csv" if args.window == 1 else "signals_combined.csv")
    asyncio.run(analyze_liquidations(args.window, output_file))


if __name__ == "__main__":
    main()