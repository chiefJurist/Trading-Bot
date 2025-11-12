# ===========================================================
# REAL-TIME BINANCE FUTURES LIQUIDATION STRATEGY
# ===========================================================
# This script connects directly to Binance's live WebSocket stream for liquidations.
# It processes all real-time liquidation events, aggregates them in rolling windows,
# and generates trading signals when liquidation bursts occur.
# Each line has a comment above it for clarity.
# Time outputs are shown in GMT+1.
# ===========================================================

# import standard libraries
import asyncio  # for async websocket event handling
import json     # for parsing JSON from websocket
import time     # for timestamps and sleeping
import math     # for numerical computations
from datetime import datetime, timedelta, timezone  # for timestamp formatting
from collections import deque, defaultdict          # for event storage

# import numpy for averages and numerical work
import numpy as np

# import websockets library to connect to Binance stream
import websockets

# -----------------------------------------------------------
# Configuration Section
# -----------------------------------------------------------

# Binance Futures WebSocket endpoint for liquidation events
BINANCE_LIQ_STREAM = "wss://fstream.binance.com/ws/!forceOrder@arr"

# define the time window for recent liquidations (in seconds)
LIQ_WINDOW_SECONDS = 120  # 2-minute rolling window

# define how many minutes to use for the rolling baseline average
ROLLING_BASELINE_MINUTES = 60

# define threshold for burst detection relative to baseline
BURST_MULTIPLIER = 8.0

# define minimum liquidation USD value to include
MIN_USD_FOR_CONSIDERATION = 100.0

# -----------------------------------------------------------
# Utility functions
# -----------------------------------------------------------

# return current timestamp in seconds
def now_ts():
    return time.time()

# convert timestamp to integer minute bucket
def ts_to_min(ts):
    return int(ts // 60)

# convert UNIX timestamp to readable GMT+1 time
def format_gmt1(ts):
    # create timezone offset of +1 hour
    gmt1 = timezone(timedelta(hours=1))
    # return formatted string
    return datetime.fromtimestamp(ts, gmt1).strftime("%Y-%m-%d %H:%M:%S")

# -----------------------------------------------------------
# Liquidation Processor
# -----------------------------------------------------------

class LiquidationProcessor:
    # class to store and process liquidation data in real time
    def __init__(self, window_seconds=LIQ_WINDOW_SECONDS, baseline_minutes=ROLLING_BASELINE_MINUTES):
        # initialize rolling window and baseline history
        self.window_seconds = window_seconds
        self.baseline_minutes = baseline_minutes
        # deque for recent events
        self.events = deque()
        # baseline totals per minute
        self.minute_totals = defaultdict(float)

    # ingest a new liquidation event
    def ingest(self, event):
        # add event to the queue
        self.events.append(event)
        # update baseline totals
        minute = ts_to_min(event["ts"])
        self.minute_totals[minute] += event["usd"]
        # remove old data
        self._trim_events()
        self._trim_minute_totals()

    # trim outdated events from rolling window
    def _trim_events(self):
        cutoff = now_ts() - self.window_seconds
        while self.events and self.events[0]["ts"] < cutoff:
            self.events.popleft()

    # trim old minutes from baseline history
    def _trim_minute_totals(self):
        cutoff_min = ts_to_min(now_ts() - self.baseline_minutes * 60)
        to_del = [m for m in self.minute_totals.keys() if m < cutoff_min]
        for m in to_del:
            del self.minute_totals[m]

    # aggregate total long and short liquidations in current window
    def aggregate_window(self):
        L_buy = 0.0
        L_sell = 0.0
        for ev in self.events:
            # forced sells = long liquidations
            if ev["side"].upper() == "LONG":
                L_sell += ev["usd"]
            else:
                # forced buys = short liquidations
                L_buy += ev["usd"]
        return L_buy, L_sell

    # compute baseline average liquidation per minute
    def baseline_average(self):
        if not self.minute_totals:
            return 1e-6
        values = list(self.minute_totals.values())
        return float(np.mean(values))

# -----------------------------------------------------------
# Signal Generator
# -----------------------------------------------------------

class SignalGenerator:
    # generate buy/sell signals based on liquidation imbalances
    def __init__(self, burst_multiplier=BURST_MULTIPLIER):
        self.burst_multiplier = burst_multiplier

    def evaluate(self, symbol, L_buy, L_sell, baseline_avg):
        # compute net and total liquidation volume
        liq_net = L_buy - L_sell
        liq_total = L_buy + L_sell

        # compute imbalance ratio
        imbalance_ratio = abs(liq_net) / liq_total if liq_total > 0 else 0.0

        # determine whether current burst exceeds baseline
        is_burst = liq_total > max(MIN_USD_FOR_CONSIDERATION, baseline_avg * self.burst_multiplier)

        # compute confidence score based on magnitude and imbalance
        score = 0.0
        if is_burst:
            score += math.log1p(liq_total) / 10.0
        prob = min(0.98, 0.5 + 0.5 * imbalance_ratio + min(0.48, score / 5.0))

        # determine trade direction
        direction = "LONG" if liq_net < 0 else "SHORT" if liq_net > 0 else "NONE"

        # return all signal details
        return {
            "symbol": symbol,
            "liq_buy": L_buy,
            "liq_sell": L_sell,
            "liq_total": liq_total,
            "liq_net": liq_net,
            "is_burst": is_burst,
            "imbalance_ratio": imbalance_ratio,
            "direction": direction,
            "probability": prob,
            "timestamp": now_ts()
        }

# -----------------------------------------------------------
# Main Live Loop
# -----------------------------------------------------------

async def run_live_liquidation_stream():
    # initialize processor and signal generator
    processor = LiquidationProcessor()
    siggen = SignalGenerator()

    print("Connecting to Binance Futures liquidation stream...")
    # open websocket connection
    async with websockets.connect(BINANCE_LIQ_STREAM) as ws:
        print("Connected successfully. Listening for live liquidations...\n")
        # infinite loop for continuous listening
        while True:
            try:
                # receive a JSON message from the websocket
                msg = await ws.recv()
                # parse the message
                data = json.loads(msg)

                # Binance sends an array of liquidation updates
                # loop through each liquidation event
                for entry in data:
                    # extract core info
                    order = entry["o"]
                    symbol = order["s"]
                    side = order["S"]
                    qty = float(order["q"])
                    price = float(order["ap"])
                    usd_value = qty * price
                    ts = order["T"] / 1000

                    # skip small values
                    if usd_value < MIN_USD_FOR_CONSIDERATION:
                        continue

                    # map Binance side to "LONG" or "SHORT"
                    # when side == "SELL", a long was liquidated
                    mapped_side = "LONG" if side == "SELL" else "SHORT"

                    # construct event
                    ev = {"ts": ts, "symbol": symbol, "side": mapped_side, "usd": usd_value}
                    # feed to processor
                    processor.ingest(ev)

                # aggregate last 2 minutes
                L_buy, L_sell = processor.aggregate_window()
                baseline = processor.baseline_average()
                # pick a representative symbol (BTCUSDT dominates)
                symbol = "BTCUSDT"
                # evaluate signal
                sig = siggen.evaluate(symbol, L_buy, L_sell, baseline)

                # if a burst is detected, print detailed output
                if sig["is_burst"]:
                    print("-----------------------------------------------------")
                    print(f"Time (GMT+1): {format_gmt1(sig['timestamp'])}")
                    print(f"Symbol: {sig['symbol']}")
                    print(f"Total USD: {sig['liq_total']:.2f}")
                    print(f"Net USD: {sig['liq_net']:.2f}")
                    print(f"Buy Liqs (shorts): {sig['liq_buy']:.2f}")
                    print(f"Sell Liqs (longs): {sig['liq_sell']:.2f}")
                    print(f"Imbalance Ratio: {sig['imbalance_ratio']:.2f}")
                    print(f"Direction: {sig['direction']}")
                    print(f"Confidence: {sig['probability']:.2f}")
                    print("-----------------------------------------------------\n")

            except Exception as e:
                # print any errors and reconnect after 5 seconds
                print("Error:", e)
                print("Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
                break

# -----------------------------------------------------------
# Script Entrypoint
# -----------------------------------------------------------

if __name__ == "__main__":
    # start asyncio event loop
    try:
        asyncio.run(run_live_liquidation_stream())
    except KeyboardInterrupt:
        print("Stream stopped by user.")
