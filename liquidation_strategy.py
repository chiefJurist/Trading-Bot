# # Real-time Binance Futures Liquidation Signal System
# # Each line in this file has a comment immediately above it as requested.
# # Save as `liquidation_strategy.py` and run with Python 3.9+ on your VPS.
# # Requirements: `websockets`, `numpy`, `pandas` (optional for saving), installed in your environment.
# # NOTE: For safety, do NOT hardcode API secrets in production; use environment variables.
# 
# import asyncio for async websocket handling and loops
import asyncio
# import json for parsing websocket messages
import json
# import time to get epoch timestamps and sleeping
import time
# import math for numerical helpers like log1p
import math
# import datetime utilities for formatting and timezone handling
from datetime import datetime, timedelta, timezone
# import collections deque and defaultdict for event buffers and minute totals
from collections import deque, defaultdict
# import numpy for baseline averaging and numeric ops
import numpy as np
# import websockets to connect to Binance WebSocket stream
import websockets
# import os to read environment variables for safe API key management
import os
# import signal to gracefully handle stop signals (SIGINT/SIGTERM)
import signal
# import pandas to save logs to csv if you want (optional)
import pandas as pd
# 
# ---------------------- CONFIGURATION ----------------------
# 
# define WebSocket URL for Binance Futures forced orders (liquidations)
BINANCE_LIQ_STREAM = "wss://fstream.binance.com/ws/!forceOrder@arr"
# set rolling window in seconds to aggregate recent liquidations (default 120s)
LIQ_WINDOW_SECONDS = 120
# set baseline averaging window in minutes (default 60 minutes)
ROLLING_BASELINE_MINUTES = 60
# threshold multiplier to call a burst compared to baseline (default 8x)
BURST_MULTIPLIER = 8.0
# minimal liquidation USD value to consider an event (ignore micro events)
MIN_USD_FOR_CONSIDERATION = 100.0
# choose whether to print raw events to console for debugging
PRINT_RAW_EVENTS = False
# path to save signals CSV (optional)
SIGNALS_CSV_PATH = "/mnt/data/live_liq_signals.csv"
# whether to append to the CSV (True) or overwrite (False)
SIGNALS_CSV_APPEND = True
# reconnection backoff base seconds after error
RECONNECT_BACKOFF_SECONDS = 5
# maximum messages to keep in memory for CSV-saving buffer before flushing
CSV_BUFFER_FLUSH_SIZE = 50
# timezone offset hours for output (GMT+1 requested)
OUTPUT_TZ_OFFSET_HOURS = 1
# set a friendly identifier for the "dominant" symbol shown in summaries (optional)
DEFAULT_SYMBOL = "BTCUSDT"
# read Binance API key from environment if needed later (we don't need it for liquidation stream)
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
# read Binance API secret from environment if needed later (we don't need it for liquidation stream)
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
# 
# ---------------------- TIME HELPERS ----------------------
# 
# return current epoch time in seconds as float
def now_ts():
    # use time.time() for sub-second precision
    return time.time()
# 
# convert epoch seconds to integer minute bucket
def ts_to_min(ts):
    # floor divide by 60
    return int(ts // 60)
# 
# format epoch seconds to human readable string in GMT+1 as requested
def format_gmt_plus(offset_hours, ts):
    # create tzinfo for given offset
    tz = timezone(timedelta(hours=offset_hours))
    # convert and format
    return datetime.fromtimestamp(ts, tz).strftime("%Y-%m-%d %H:%M:%S")
# 
# ---------------------- LIQUIDATION PROCESSOR ----------------------
# 
# class to ingest liquidation events and produce rolling aggregates
class LiquidationProcessor:
    # initialize processor with a rolling event window and minute-based baseline storage
    def __init__(self, window_seconds=LIQ_WINDOW_SECONDS, baseline_minutes=ROLLING_BASELINE_MINUTES):
        # set rolling window size in seconds
        self.window_seconds = window_seconds
        # set baseline history length in minutes
        self.baseline_minutes = baseline_minutes
        # deque to store recent events as dictionaries
        self.events = deque()
        # dict-like mapping minute -> total USD in that minute
        self.minute_totals = defaultdict(float)
    # ingest a single event {'ts':..., 'symbol':..., 'side': 'LONG'|'SHORT', 'usd': ...}
    def ingest(self, event):
        # append the incoming event to the events deque
        self.events.append(event)
        # compute minute bucket for baseline accounting
        minute = ts_to_min(event["ts"])
        # add this event's USD amount to the minute bucket
        self.minute_totals[minute] += event["usd"]
        # trim the old events outside the rolling window
        self._trim_events()
        # trim older minute buckets outside baseline window
        self._trim_minute_totals()
    # internal: drop events older than the configured rolling window
    def _trim_events(self):
        # compute cutoff timestamp
        cutoff = now_ts() - self.window_seconds
        # pop left while oldest event is older than cutoff
        while self.events and self.events[0]["ts"] < cutoff:
            # remove the oldest event
            self.events.popleft()
    # internal: drop minute buckets older than baseline history length
    def _trim_minute_totals(self):
        # compute cutoff minute
        cutoff_min = ts_to_min(now_ts() - self.baseline_minutes * 60)
        # gather keys to delete to avoid runtime modification during iteration
        to_delete = [m for m in self.minute_totals.keys() if m < cutoff_min]
        # delete them
        for m in to_delete:
            # remove entry from the dict
            del self.minute_totals[m]
    # produce aggregated buy and sell totals in the current rolling window
    def aggregate_window(self):
        # initialize totals
        L_buy = 0.0
        L_sell = 0.0
        # iterate events in the deque
        for ev in self.events:
            # treat 'SHORT' liquidations as forced buys (shorts getting liquidated -> buys)
            if ev["side"].upper() == "SHORT":
                # add usd to buy-side total
                L_buy += ev["usd"]
            else:
                # treat 'LONG' liquidations as forced sells (longs getting liquidated -> sells)
                L_sell += ev["usd"]
        # return tuple of (buy_total, sell_total)
        return L_buy, L_sell
    # compute baseline average liquidation (USD per minute) over stored minutes
    def baseline_average(self):
        # if no minute data, return a tiny epsilon to avoid division by zero
        if not self.minute_totals:
            # small number rather than zero
            return 1e-6
        # compute numpy mean across minute totals
        vals = list(self.minute_totals.values())
        # return float mean
        return float(np.mean(vals))
# 
# ---------------------- SIGNAL GENERATOR ----------------------
# 
# class to compute signal details from aggregated liquidation metrics
class SignalGenerator:
    # initialize with burst multiplier
    def __init__(self, burst_multiplier=BURST_MULTIPLIER):
        # store multiplier used to compare to baseline
        self.burst_multiplier = burst_multiplier
    # evaluate current aggregated values and return a signal dictionary
    def evaluate(self, symbol, L_buy, L_sell, baseline_avg):
        # compute net liquidation (positive => more forced buys, negative => more forced sells)
        liq_net = L_buy - L_sell
        # compute total liquidation volume
        liq_total = L_buy + L_sell
        # compute imbalance ratio safely
        imbalance_ratio = abs(liq_net) / liq_total if liq_total > 0 else 0.0
        # decide if this constitutes a burst compared to baseline and minimum threshold
        is_burst = liq_total > max(MIN_USD_FOR_CONSIDERATION, baseline_avg * self.burst_multiplier)
        # compute a heuristic score from magnitude for mapping to probability
        score = 0.0
        # add magnitude-based score if burst
        if is_burst:
            # use log1p to compress dynamic range
            score += math.log1p(liq_total) / 10.0
        # map imbalance and score into a probability [0.0, 0.98]
        prob = min(0.98, 0.5 + 0.5 * imbalance_ratio + min(0.48, score / 5.0))
        # determine trade direction: net negative => more sells => expect LONG reversal
        if liq_net < 0:
            # suggest LONG when net < 0
            direction = "LONG"
        elif liq_net > 0:
            # suggest SHORT when net > 0
            direction = "SHORT"
        else:
            # no clear direction
            direction = "NONE"
        # construct signal payload with key details
        signal = {
            # symbol name
            "symbol": symbol,
            # total forced buys (short liquidations)
            "liq_buy": L_buy,
            # total forced sells (long liquidations)
            "liq_sell": L_sell,
            # total liquidation USD in window
            "liq_total": liq_total,
            # net (buy - sell)
            "liq_net": liq_net,
            # whether burst
            "is_burst": is_burst,
            # imbalance ratio
            "imbalance_ratio": imbalance_ratio,
            # direction suggestion
            "direction": direction,
            # heuristic probability
            "probability": prob,
            # timestamp when evaluated
            "timestamp": now_ts()
        }
        # return the signal dictionary
        return signal
# 
# ---------------------- CSV LOGGING HELPERS ----------------------
# 
# function to append signals to a CSV buffer and flush periodically
class CSVLogger:
    # initialize CSV logger with path and append behavior
    def __init__(self, path=SIGNALS_CSV_PATH, append=SIGNALS_CSV_APPEND, flush_size=CSV_BUFFER_FLUSH_SIZE):
        # store path
        self.path = path
        # store append flag
        self.append = append
        # in-memory buffer list
        self.buffer = []
        # flush threshold
        self.flush_size = flush_size
    # add a signal dict to buffer and flush if needed
    def log(self, signal):
        # prepare flattened record
        rec = {
            "ts": signal["timestamp"],
            "local_time": format_gmt_plus(OUTPUT_TZ_OFFSET_HOURS, signal["timestamp"]),
            "symbol": signal["symbol"],
            "liq_total": signal["liq_total"],
            "liq_net": signal["liq_net"],
            "liq_buy": signal["liq_buy"],
            "liq_sell": signal["liq_sell"],
            "imbalance_ratio": signal["imbalance_ratio"],
            "direction": signal["direction"],
            "probability": signal["probability"]
        }
        # push to buffer
        self.buffer.append(rec)
        # flush if buffer large enough
        if len(self.buffer) >= self.flush_size:
            # call flush
            self.flush()
    # flush buffer to disk
    def flush(self):
        # if no records, nothing to do
        if not self.buffer:
            # return early
            return
        # create DataFrame for writing
        df = pd.DataFrame(self.buffer)
        # try to write, if append and file exists then append without header
        try:
            if self.append and os.path.exists(self.path):
                # append to existing file without header
                df.to_csv(self.path, mode="a", header=False, index=False)
            else:
                # write new file with header
                df.to_csv(self.path, index=False)
        except Exception as e:
            # print error but continue
            print(f"[CSVLogger] Error writing CSV: {e}")
        # clear buffer after flush
        self.buffer = []
# 
# ---------------------- MAIN LIVE LISTENER ----------------------
# 
# graceful stop flag set by signal handler
STOP_REQUESTED = False
# handle termination signals to set STOP_REQUESTED
def _signal_handler(sig_num, frame):
    # set the global stop flag
    global STOP_REQUESTED
    # indicate stop was requested
    STOP_REQUESTED = True
# register SIGINT and SIGTERM to our handler
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)
# 
# primary coroutine: connects to Binance liquidation stream and processes messages forever
async def run_live_forever():
    # instantiate processor and signal generator
    processor = LiquidationProcessor()
    # instantiate generator with configured burst multiplier
    siggen = SignalGenerator(burst_multiplier=BURST_MULTIPLIER)
    # instantiate CSV logger (optional)
    csv_logger = CSVLogger()
    # track consecutive reconnect attempts
    reconnect_attempts = 0
    # loop until user requested stop
    while not STOP_REQUESTED:
        # try-except around websocket connection so we can reconnect on error
        try:
            # open a websocket connection to the Binance forced-order stream
            async with websockets.connect(BINANCE_LIQ_STREAM, ping_interval=20, ping_timeout=20) as ws:
                # reset reconnect attempts on successful connect
                reconnect_attempts = 0
                # print connection success line with local time in GMT+1
                print(f"[{format_gmt_plus(OUTPUT_TZ_OFFSET_HOURS, now_ts())}] Connected to Binance liquidation stream.")
                # listen indefinitely for messages until an error or stop occurs
                async for raw_msg in ws:
                    # break if stop requested
                    if STOP_REQUESTED:
                        # break out of for-loop to close connection cleanly
                        break
                    # optionally print raw messages for debugging
                    if PRINT_RAW_EVENTS:
                        # print raw message content (be careful with large volumes)
                        print(raw_msg)
                    # attempt to parse JSON payload
                    try:
                        # parse JSON string into Python object
                        parsed = json.loads(raw_msg)
                    except Exception as e:
                        # print parsing error and skip message
                        print(f"[{format_gmt_plus(OUTPUT_TZ_OFFSET_HOURS, now_ts())}] JSON parse error: {e}")
                        # continue to next message
                        continue
                    # Binance may send dicts or lists; handle both
                    # if parsed is a dict and contains 'o' -> single event
                    if isinstance(parsed, dict) and "o" in parsed:
                        # wrap into a single-element list for uniform processing
                        events_list = [parsed]
                    # if parsed is a list -> treat each element as an event object
                    elif isinstance(parsed, list):
                        # use the list directly
                        events_list = parsed
                    # if parsed is a dict but contains 'data' key with 'o' (some wrapped formats)
                    elif isinstance(parsed, dict) and "data" in parsed and isinstance(parsed["data"], dict) and "o" in parsed["data"]:
                        # wrap the inner 'data' object
                        events_list = [parsed["data"]]
                    else:
                        # unknown format; skip it
                        continue
                    # process each event object in the list
                    for item in events_list:
                        # safety: ensure object has 'o' field which holds order details
                        if not isinstance(item, dict) or "o" not in item:
                            # skip unexpected structure
                            continue
                        # extract order sub-object
                        order = item["o"]
                        # extract symbol (string)
                        symbol = order.get("s") or order.get("S") or DEFAULT_SYMBOL
                        # extract side letter (BID/ASK) as string; default to 'SELL' if missing
                        side_letter = order.get("S", "SELL")
                        # extract executed quantity (q) and average price (ap)
                        q_raw = order.get("q", "0")
                        ap_raw = order.get("ap", "0")
                        # attempt to cast to float safely
                        try:
                            qty = float(q_raw)
                        except Exception:
                            # skip if quantity invalid
                            continue
                        try:
                            avg_price = float(ap_raw)
                        except Exception:
                            # skip if price invalid
                            continue
                        # compute USD notional for this liquidation event
                        usd_value = qty * avg_price
                        # skip if event is below our minimal consideration threshold
                        if usd_value < MIN_USD_FOR_CONSIDERATION:
                            # skip small liquidation
                            continue
                        # map Binance side letter to our internal 'LONG'|'SHORT' label:
                        # Binance 'SELL' indicates a long position was closed (forced sell) -> LONG liquidation
                        mapped_side = "LONG" if side_letter.upper() == "SELL" else "SHORT"
                        # event timestamp: Binance sends 'T' in ms inside 'o' frequently, fallback to current ts
                        ts_ms = order.get("T")
                        # compute epoch seconds from ms if present, else use now
                        event_ts = (ts_ms / 1000.0) if isinstance(ts_ms, (int, float)) else now_ts()
                        # construct normalized event dict
                        event = {"ts": event_ts, "symbol": symbol, "side": mapped_side, "usd": usd_value}
                        # ingest event into processor
                        processor.ingest(event)
                        # after ingesting, aggregate current window totals
                        L_buy, L_sell = processor.aggregate_window()
                        # compute baseline average per minute
                        baseline = processor.baseline_average()
                        # evaluate a signal for a representative symbol (you can compute per-symbol too)
                        sig = siggen.evaluate(DEFAULT_SYMBOL, L_buy, L_sell, baseline)
                        # print detailed readable output whenever a burst is detected
                        if sig["is_burst"]:
                            # print header separator
                            print("------------------------------------------------------------")
                            # print GMT+1 timestamp
                            print(f"Time (GMT+1): {format_gmt_plus(OUTPUT_TZ_OFFSET_HOURS, sig['timestamp'])}")
                            # print which symbol the aggregated signal was computed for
                            print(f"Signal Symbol: {sig['symbol']}")
                            # print basic numeric summaries
                            print(f"Total Liquidation (USD): {sig['liq_total']:.2f}")
                            # print net direction of the liquidation flow
                            print(f"Net Liquidation USD (buy - sell): {sig['liq_net']:.2f}")
                            # print breakdown
                            print(f"Buy Liquidations (shorts->forced buys): {sig['liq_buy']:.2f}")
                            print(f"Sell Liquidations (longs->forced sells): {sig['liq_sell']:.2f}")
                            # print imbalance ratio and confidence
                            print(f"Imbalance Ratio: {sig['imbalance_ratio']:.3f}")
                            print(f"Suggested Direction: {sig['direction']}")
                            print(f"Confidence (heuristic): {sig['probability']:.3f}")
                            # print baseline context
                            print(f"Baseline (USD/min): {baseline:.2f}  |  Burst Threshold: {max(MIN_USD_FOR_CONSIDERATION, baseline * BURST_MULTIPLIER):.2f}")
                            # print footer separator
                            print("------------------------------------------------------------")
                            # log to CSV asynchronously by adding to logger buffer
                            try:
                                # call csv_logger.log with the computed signal
                                csv_logger.log(sig)
                            except Exception as e:
                                # print any csv logger errors but continue
                                print(f"[{format_gmt_plus(OUTPUT_TZ_OFFSET_HOURS, now_ts())}] CSV log error: {e}")
                        # otherwise, for non-bursts, optionally you may still print a concise live line
                        else:
                            # print a compact live summary line (uncomment the next line to enable)
                            # print(f"{format_gmt_plus(OUTPUT_TZ_OFFSET_HOURS, now_ts())} {symbol} live: L_buy={L_buy:.2f} L_sell={L_sell:.2f} baseline={baseline:.2f} ")
                            pass
                    # end for each item in events_list
                # end async for messages
            # end async with websocket
        except Exception as e:
            # compute reconnect delay with simple backoff
            reconnect_attempts += 1
            delay = min(60, RECONNECT_BACKOFF_SECONDS * reconnect_attempts)
            # print error with GMT+1 timestamp
            print(f"[{format_gmt_plus(OUTPUT_TZ_OFFSET_HOURS, now_ts())}] Connection error: {e}")
            # attempt to flush CSV buffer if we have any
            try:
                csv_logger.flush()
            except Exception:
                # ignore CSV flush errors
                pass
            # if stop requested, break out instead of reconnecting
            if STOP_REQUESTED:
                # print stopping message
                print(f"[{format_gmt_plus(OUTPUT_TZ_OFFSET_HOURS, now_ts())}] Stop requested, exiting loop.")
                # break main loop
                break
            # otherwise wait for delay seconds before reconnect attempt
            print(f"[{format_gmt_plus(OUTPUT_TZ_OFFSET_HOURS, now_ts())}] Reconnecting in {delay} seconds...")
            # sleep asynchronously
            await asyncio.sleep(delay)
    # final flush of any remaining CSV buffer before exiting
    try:
        csv_logger.flush()
    except Exception:
        # print if flush fails
        print(f"[{format_gmt_plus(OUTPUT_TZ_OFFSET_HOURS, now_ts())}] Final CSV flush failed.")
# 
# ---------------------- ENTRYPOINT ----------------------
# 
# if run as script, start the asyncio loop and run forever until interrupted
if __name__ == "__main__":
    # print startup banner with local time
    print(f"[{format_gmt_plus(OUTPUT_TZ_OFFSET_HOURS, now_ts())}] Starting live liquidation strategy...")
    # start asyncio run loop for the main coroutine
    try:
        # run the main coroutine until it completes or is cancelled
        asyncio.run(run_live_forever())
    # allow user to stop with keyboard interrupt
    except KeyboardInterrupt:
        # print a graceful stop message
        print(f"[{format_gmt_plus(OUTPUT_TZ_OFFSET_HOURS, now_ts())}] KeyboardInterrupt received, shutting down...")
    # generic exception handler to make sure script prints when unexpected errors occur
    except Exception as e:
        # print unexpected exception detail
        print(f"[{format_gmt_plus(OUTPUT_TZ_OFFSET_HOURS, now_ts())}] Fatal error: {e}")
    # print shutdown complete message
    print(f"[{format_gmt_plus(OUTPUT_TZ_OFFSET_HOURS, now_ts())}] Liquidation strategy stopped.")