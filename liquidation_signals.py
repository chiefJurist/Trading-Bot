import csv
from datetime import datetime, timedelta
from collections import defaultdict

# File paths
SOURCE_FILE = "binance_liquidations.csv"
SIGNALS_FILE = "signals.csv"

# Timezone offset (UTC+1)
TZ_OFFSET = timedelta(hours=1)

def analyze_liquidations():
    grouped = defaultdict(lambda: {"BUY": 0, "SELL": 0})

    # ---- Read the liquidation CSV ----
    with open(SOURCE_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Parse UTC timestamp and convert to UTC+1
                dt_utc = datetime.fromisoformat(row["timestamp"])
                dt_local = dt_utc + TZ_OFFSET

                # Round to the nearest minute (zero out seconds & microseconds)
                minute = dt_local.replace(second=0, microsecond=0)

                key = (minute, row["symbol"])
                side = row["side"].upper().strip()
                grouped[key][side] += 1
            except Exception as e:
                print("Skipping row due to error:", e)

    # ---- Analyze and extract strong signals ----
    results = []
    for (minute, symbol), counts in grouped.items():
        buy_count = counts["BUY"]
        sell_count = counts["SELL"]

        # Check BUY signals
        if buy_count >= 7 and sell_count == 0:
            results.append({
                "date": minute.strftime("%Y-%m-%d"),
                "time": minute.strftime("%H:%M"),
                "pair": symbol,
                "side": "BUY",
                "occurrences": buy_count
            })

        # Check SELL signals
        elif sell_count >= 7 and buy_count == 0:
            results.append({
                "date": minute.strftime("%Y-%m-%d"),
                "time": minute.strftime("%H:%M"),
                "pair": symbol,
                "side": "SELL",
                "occurrences": sell_count
            })

    # ---- Write signals.csv ----
    with open(SIGNALS_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "time", "pair", "side", "occurrences"])
        writer.writeheader()
        writer.writerows(results)

    print(f"✅ Analysis complete. {len(results)} signals saved to {SIGNALS_FILE}")

if __name__ == "__main__":
    analyze_liquidations()