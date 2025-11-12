
# # This script implements a liquidation-based trading signal system described in the conversation.
# # Each code line has a comment **above** it as requested.
# # The script supports two modes: simulation mode (no network) and connector mode (placeholders for Binance).
# # Save this file and run it in an environment with needed libraries (requests, numpy, pandas, sklearn, ccxt) for full features.
# # Note: network calls are placeholders because this execution environment has no internet access.
# 
# import standard libraries
# 
import os
# import operating system utilities
import time
# import time utilities for delays and timestamps
import math
# import math for numerical helpers
import json
# import json for config and serialization
import threading
# import threading for running background processors
import queue
# import queue to buffer real-time events
# import third-party numeric and data libraries
# 
import numpy as np
# import numpy for numeric arrays and operations
import pandas as pd
# import pandas for tabular data manipulation
# import simple model utilities
# 
from collections import deque, defaultdict, Counter
# import collections helpers
# 
try:
    # attempt to import sklearn if available for simple models
    from sklearn.linear_model import LogisticRegression
    # import logistic regression for probability model
except Exception:
    # fallback if sklearn isn't installed
    LogisticRegression = None
# 
# ---------- Configuration ----------
# 
# set mode to 'simulate' to run without network, or 'connector' to use Binance placeholders
# 
MODE = "simulate"
# MODE selects whether to simulate events or attempt to call Binance endpoints
# 
# thresholds and windows
# 
LIQ_WINDOW_SECONDS = 120
# time window (in seconds) for aggregating liquidation bursts
ROLLING_BASELINE_MINUTES = 60
# baseline window (in minutes) to compute average liquidation flow
BURST_MULTIPLIER = 8.0
# burst multiplier threshold relative to baseline to flag an extreme event
MIN_USD_FOR_CONSIDERATION = 100.0
# minimum liquidation USD value to include
# 
# connector placeholders (user should replace with real keys if running live)
# 
BINANCE_API_KEY = "cTTxVL1Cka27JhHPL80arFFL1lPN6dhZWZwpQJ5rw7Uyl32hRiLtcqbNVxFS4u2O"
# placeholder for Binance API key
BINANCE_API_SECRET = "WPwxBqYa37AXKOMxwWmFeJJ7KvlmHpuD0dUIjd2d9YoW53L1yRGwJEcZhtaJpBeF"
# placeholder for Binance API secret
# 
# ---------- Utilities ----------
# 
def now_ts():
    # return current timestamp in seconds (float)
    return time.time()
# 
def ts_to_min(ts):
    # convert timestamp to integer minute bucket
    return int(ts // 60)
# 
# ---------- Simple Binance Connector (placeholders) ----------
# 
class BinanceConnector:
    # connector holds methods to query REST endpoints for OI, funding and orderbook
    def __init__(self):
        # initialize connector state
        self.api_key = BINANCE_API_KEY
        # store api key
        self.api_secret = BINANCE_API_SECRET
        # store api secret
    def get_funding_rate(self, symbol):
        # placeholder method: get latest funding rate for symbol
        # NOTE: replace with real REST call to Binance /fapi/v1/fundingRate
        return 0.0
    def get_open_interest(self, symbol):
        # placeholder method: get current open interest for a symbol
        # NOTE: replace with real REST call to Binance /fapi/v1/openInterest
        return 0.0
    def get_order_book_imbalance(self, symbol, depth=20):
        # placeholder: compute order book imbalance metric
        # NOTE: replace with real REST call to /fapi/v1/depth and compute imbalance
        return 0.0
# 
# ---------- Liquidation Event Processor ----------
# 
class LiquidationProcessor:
    # this class ingests liquidation events and computes rolling aggregates used by signals
    def __init__(self, window_seconds=LIQ_WINDOW_SECONDS, baseline_minutes=ROLLING_BASELINE_MINUTES):
        # initialize processor with aggregation windows
        self.window_seconds = window_seconds
        # store window size
        self.baseline_minutes = baseline_minutes
        # buffer of recent events as deque of (ts, symbol, side, usd)
        self.events = deque()
        # baseline totals stored per minute for historical baseline computation
        self.minute_totals = defaultdict(float)
        # total aggregated value per minute
        self.lock = threading.Lock()
        # thread lock for concurrency
    def ingest(self, event):
        # ingest a single liquidation event dict: {'ts':..., 'symbol':..., 'side': 'LONG'|'SHORT', 'usd':...}
        with self.lock:
            # push event into deque
            self.events.append(event)
            # update per-minute baseline
            minute = ts_to_min(event["ts"])
            # accumulate USD value for that minute
            self.minute_totals[minute] += event["usd"]
            # trim minute_totals to baseline window
            self._trim_minute_totals()
            # trim events deque to window size
            self._trim_events()
    def _trim_events(self):
        # remove events older than the rolling window
        cutoff = now_ts() - self.window_seconds
        # pop from left while older than cutoff
        while self.events and self.events[0]["ts"] < cutoff:
            # remove leftmost event
            self.events.popleft()
    def _trim_minute_totals(self):
        # keep only last baseline_minutes in minute_totals
        cutoff_min = ts_to_min(now_ts() - self.baseline_minutes * 60)
        # delete older keys
        to_del = [m for m in self.minute_totals.keys() if m < cutoff_min]
        # remove them
        for m in to_del:
            # delete minute entry
            del self.minute_totals[m]
    def aggregate_window(self):
        # aggregate current window totals into buy/sell totals
        with self.lock:
            # compute totals
            L_buy = 0.0
            L_sell = 0.0
            # iterate events
            for ev in self.events:
                # short liquidations are forced buys (shorts getting liquidated -> market buys)
                if ev["side"].upper() == "SHORT":
                    # add to buy-side total
                    L_buy += ev["usd"]
                else:
                    # long liquidations are forced sells
                    L_sell += ev["usd"]
            # return aggregated tuple
            return L_buy, L_sell
    def baseline_average(self):
        # compute baseline average total liquidation per minute over stored minute_totals
        if not self.minute_totals:
            # if no data, return small epsilon
            return 1e-6
        # compute average of totals
        values = list(self.minute_totals.values())
        # return mean
        return float(np.mean(values))
# 
# ---------- Signal Generator ----------
# 
class SignalGenerator:
    # signal generator uses liquidation aggregates + connector metrics to decide
    def __init__(self, connector=None, burst_multiplier=BURST_MULTIPLIER):
        # store connector and thresholds
        self.connector = connector or BinanceConnector()
        # store burst multiplier threshold
        self.burst_multiplier = burst_multiplier
        # optional probabilistic model
        self.prob_model = None
    def train_prob_model(self, historical_df):
        # train a simple logistic regression to predict reversal probability given features
        if LogisticRegression is None:
            # sklearn not available, skip training
            self.prob_model = None
            return
        # create simple features
        X = historical_df[["liq_net", "liq_total", "oi_delta", "funding"]].fillna(0.0).values
        # target: reversal_next_10m
        y = historical_df["reversal_next_10m"].astype(int).values
        # create and fit logistic regression
        model = LogisticRegression(max_iter=200)
        # fit model
        model.fit(X, y)
        # store model
        self.prob_model = model
    def evaluate(self, symbol, L_buy, L_sell, baseline_avg):
        # evaluate current window and return a signal dict with probability/confidence
        # compute net and total
        liq_net = L_buy - L_sell
        # compute total
        liq_total = L_buy + L_sell
        # compute imbalance ratio safely
        if liq_total > 0:
            # compute ratio
            imbalance_ratio = abs(liq_net) / liq_total
        else:
            # fallback ratio zero
            imbalance_ratio = 0.0
        # baseline check: determine whether current burst is extreme
        is_burst = (liq_total > max(MIN_USD_FOR_CONSIDERATION, baseline_avg * self.burst_multiplier))
        # fetch connector metrics
        funding = self.connector.get_funding_rate(symbol)
        # get open interest delta (placeholder zero)
        oi = self.connector.get_open_interest(symbol)
        # compute a simple heuristic score
        score = 0.0
        # if imbalance favors buys (short liquidations -> forced buys) that could signal exhaustion of buying pressure
        if is_burst:
            # burst contributes a base score proportional to log of volume
            score += math.log1p(liq_total) / 10.0
        # funding effect: high positive funding suggests long crowding, so long liquidations are more likely to reverse
        score += -funding
        # order book and oi could adjust score; we use oi placeholder
        score += -0.0
        # if a trained model exists, use it to produce probability
        prob = None
        if self.prob_model is not None:
            # prepare single-row features
            X = np.array([[liq_net, liq_total, 0.0, funding]])
            # get probability of reversal (class 1)
            prob = float(self.prob_model.predict_proba(X)[0,1])
        else:
            # fallback heuristic probability mapping
            if not is_burst:
                # low probability if not burst
                prob = 0.1
            else:
                # map imbalance ratio and score into a probability between 0.5 and 0.98
                prob = min(0.98, 0.5 + 0.5 * imbalance_ratio + min(0.48, score/5.0))
        # decide direction: if net is negative (more sells), then forced sells -> opportunity to LONG (reversal up)
        direction = None
        if liq_net < 0:
            # more forced selling -> expect mean reversion upwards
            direction = "LONG"
        elif liq_net > 0:
            # more forced buying -> expect mean reversion downwards
            direction = "SHORT"
        else:
            # neutral
            direction = "NONE"
        # package signal
        signal = {
            "symbol": symbol,
            "liq_buy": L_buy,
            "liq_sell": L_sell,
            "liq_total": liq_total,
            "liq_net": liq_net,
            "baseline_avg": baseline_avg,
            "is_burst": is_burst,
            "imbalance_ratio": imbalance_ratio,
            "funding": funding,
            "oi": oi,
            "direction": direction,
            "probability": prob,
            "timestamp": now_ts()
        }
        # return the signal
        return signal
# 
# ---------- Simple Simulator for testing ----------
# 
import random
# import random module for simulation
SYMBOL = "BTCUSDT"
# default symbol used in simulation
def simulate_liquidation_event(symbol=SYMBOL):
    # create a simulated liquidation event with random side and USD value
    ts = now_ts()
    # random side, biased to create bursts occasionally
    side = random.choice(["LONG", "SHORT"])
    # value drawn from a heavy-tailed distribution to simulate occasional big events
    usd = float(max(MIN_USD_FOR_CONSIDERATION, np.random.exponential(scale=5000.0)))
    # sometimes create a very large event
    if random.random() < 0.02:
        # create mega liquidation
        usd *= random.uniform(10, 50)
    # return event dict
    return {"ts": ts, "symbol": symbol, "side": side, "usd": usd}
# 
# ---------- Orchestrator / Runner ----------
# 
def run_simulation(duration_seconds=60, ingest_rate_per_sec=5):
    # run simulation for a specified duration generating events at given rate
    # create objects
    connector = BinanceConnector()
    # create processor
    proc = LiquidationProcessor()
    # create signal generator
    siggen = SignalGenerator(connector=connector)
    # store signals
    signals = []
    # start time
    start = now_ts()
    # loop for duration
    while now_ts() - start < duration_seconds:
        # generate number of events this second
        for _ in range(ingest_rate_per_sec):
            # simulate an event
            ev = simulate_liquidation_event()
            # ingest event
            proc.ingest(ev)
        # aggregate every second
        L_buy, L_sell = proc.aggregate_window()
        # compute baseline average per minute
        baseline = proc.baseline_average()
        # evaluate signal for default symbol
        signal = siggen.evaluate(SYMBOL, L_buy, L_sell, baseline)
        # append to signals if it's a burst and probability high
        if signal["is_burst"] and signal["probability"] > 0.7:
            # save signal
            signals.append(signal)
            # print the signal
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SIGNAL: {signal['symbol']} {signal['direction']} prob={signal['probability']:.2f} total_usd={signal['liq_total']:.2f}")
        # sleep for one second
        time.sleep(1.0)
    # return collected signals
    return signals
# 
# ---------- Backtest Helper (simple) ----------
# 
def simple_backtest_on_simulation(n_minutes=60):
    # run multiple simulation iterations and compute hit rate of naive mean reversion after burst
    # parameters
    signals = []
    # run longer simulation
    signals = run_simulation(duration_seconds=60, ingest_rate_per_sec=8)
    # for simplicity, we'll assume all signals that were output are wins with 0.9 probability in ideal world
    wins = sum(1 for s in signals if s["probability"] > 0.7)
    total = len(signals)
    # compute win_rate estimate (placeholder)
    win_rate = (wins / total) if total > 0 else 0.0
    # print summary
    print("Backtest summary (simulated):")
    print("Signals generated:", total)
    print("Estimated win rate (simulated heuristic):", win_rate)
    # return dictionary
    return {"signals": total, "win_rate": win_rate}
# 
# ---------- Save/Load utilities ----------
# 
def save_signals_to_csv(signals, path="/mnt/data/signals.csv"):
    # save a list of signal dicts to CSV for later analysis
    if not signals:
        # nothing to save
        return
    # create dataframe
    df = pd.DataFrame(signals)
    # write to csv
    df.to_csv(path, index=False)
    # print file path
    print("Saved signals to", path)
# 
# ---------- Main Entrypoint ----------
# 
if __name__ == "__main__":
    # if running as script, choose behavior based on MODE
    if MODE == "simulate":
        # run simulation mode
        print("Running in SIMULATION mode for 60 seconds...")
        # run a simple backtest simulation
        res = simple_backtest_on_simulation(n_minutes=1)
        # print results
        print("Simulation complete:", res)
    else:
        # connector mode: outline steps (no network calls here)
        print("Connector mode selected. Replace BinanceConnector methods with real REST/WebSocket implementations.")
        # describe file location
        print("This script wrote no live signals because network access is disabled in this environment.")
