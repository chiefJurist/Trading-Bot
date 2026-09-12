import csv
import asyncio
import aiofiles
from datetime import datetime, timedelta
from collections import defaultdict

SOURCE_FILE = "binance_liquidations.csv"
SIGNALS_FILE = "signals.csv"

TZ_OFFSET = timedelta(hours=1)


async def analyze_liquidations():
    grouped = defaultdict(lambda: {"BUY": 0, "SELL": 0})

    # Read CSV asynchronously
    async with aiofiles.open(SOURCE_FILE, "r") as f:
        header = await f.readline()

        async for line in f:
            try:
                row = next(csv.DictReader([line], fieldnames=[
                    "timestamp",
                    "symbol",
                    "side",
                    "avg_price",
                    "filled_qty",
                    "usd_value"
                ]))

                dt_utc = datetime.fromisoformat(row["timestamp"])
                dt_local = dt_utc + TZ_OFFSET

                minute = dt_local.replace(second=0, microsecond=0)

                key = (minute, row["symbol"])
                side = row["side"].upper().strip()

                grouped[key][side] += 1

            except Exception as e:
                print("Skipping row due to error:", e)

    results = []

    for (minute, symbol), counts in grouped.items():
        buy_count = counts["BUY"]
        sell_count = counts["SELL"]

        if buy_count >= 7 and sell_count == 0:
            results.append({
                "date": minute.strftime("%Y-%m-%d"),
                "time": minute.strftime("%H:%M"),
                "pair": symbol,
                "side": "BUY",
                "occurrences": buy_count
            })

        elif sell_count >= 7 and buy_count == 0:
            results.append({
                "date": minute.strftime("%Y-%m-%d"),
                "time": minute.strftime("%H:%M"),
                "pair": symbol,
                "side": "SELL",
                "occurrences": sell_count
            })

    # Write asynchronously
    async with aiofiles.open(SIGNALS_FILE, "w") as f:
        await f.write("date,time,pair,side,occurrences\n")

        for result in results:
            await f.write(
                f'{result["date"]},'
                f'{result["time"]},'
                f'{result["pair"]},'
                f'{result["side"]},'
                f'{result["occurrences"]}\n'
            )

    print(f"Analysis complete. {len(results)} signals saved to {SIGNALS_FILE}")


if __name__ == "__main__":
    asyncio.run(analyze_liquidations())