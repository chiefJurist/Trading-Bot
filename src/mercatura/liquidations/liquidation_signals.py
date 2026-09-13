import argparse
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import aiofiles

INPUT_FILE = "binance_liquidations.csv"
TIME_OFFSET = timedelta(hours=1)
THRESHOLD = 7


def parse_timestamp(ts):
    dt = datetime.fromisoformat(ts)
    return dt.replace(second=0, microsecond=0)


async def load_liquidations():
    minutes = defaultdict(list)

    async with aiofiles.open(INPUT_FILE, "r") as f:
        await f.readline()
        async for line in f:
            parts = line.strip().split(",")
            if len(parts) < 6:
                continue
            ts, symbol, side, avg_price, qty, usd_value = parts
            minute = parse_timestamp(ts)
            minutes[minute].append({"symbol": symbol, "side": side})

    return minutes


def detect_signals(minutes, window_minutes, threshold, time_offset):
    """Pure function: {minute: [{symbol, side}, ...]} -> list of signal dicts. No I/O."""
    sorted_minutes = sorted(minutes.keys())
    signals = []

    for i in range(window_minutes - 1, len(sorted_minutes)):
        window_keys = sorted_minutes[i - (window_minutes - 1): i + 1]
        combined = [row for key in window_keys for row in minutes[key]]

        counts = Counter((row["symbol"], row["side"]) for row in combined)

        for (symbol, side), count in counts.items():
            if count < threshold:
                continue

            opposite_side = "BUY" if side == "SELL" else "SELL"
            has_opposite = any(
                r["symbol"] == symbol and r["side"] == opposite_side
                for r in combined
            )
            if has_opposite:
                continue

            local_time = sorted_minutes[i] + time_offset
            signals.append({
                "date": str(local_time.date()),
                "time": local_time.time().strftime('%H:%M'),
                "pair": symbol,
                "side": side,
                "occurrences": count
            })

    return signals


async def analyze_liquidations(window_minutes, output_file):
    minutes = await load_liquidations()
    signals = detect_signals(minutes, window_minutes, THRESHOLD, TIME_OFFSET)

    async with aiofiles.open(output_file, "w") as out:
        await out.write("date,time,pair,side,occurrences\n")
        for s in signals:
            await out.write(f"{s['date']},{s['time']},{s['pair']},{s['side']},{s['occurrences']}\n")

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