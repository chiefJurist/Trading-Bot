import csv
from datetime import datetime
from collections import defaultdict

INPUT_FILE = "binance_liquidations.csv"
OUTPUT_FILE = "signals.csv"

def truncate_to_minute(ts_str):
    """Convert timestamp to YYYY-MM-DD HH:MM (minute precision)."""
    ts = datetime.fromisoformat(ts_str)
    return ts.strftime("%Y-%m-%d %H:%M")

def process_liquidations():
    grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    # Structure: grouped[minute][symbol][side] = count

    # Read the existing liquidation file
    with open(INPUT_FILE, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            minute = truncate_to_minute(row['timestamp'])
            symbol = row['symbol']
            side = row['side'].upper().strip()
            grouped[minute][symbol][side] += 1

    # Write filtered signals
    with open(OUTPUT_FILE, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["date", "time", "pair", "side", "occurrences"])

        for minute, symbols in grouped.items():
            for symbol, sides in symbols.items():
                for side, count in sides.items():
                    if count >= 7:
                        # Check if there's no opposing side in same minute
                        opposite = "BUY" if side == "SELL" else "SELL"
                        if opposite not in sides:
                            date_part, time_part = minute.split(" ")
                            writer.writerow([date_part, time_part, symbol, side, count])

    print(f"✅ Done! Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_liquidations()