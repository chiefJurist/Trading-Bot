import os 
from dotenv import load_dotenv
import ccxt
import pandas as pd
import talib as ta
import time
import math
import numpy as np

load_dotenv()

# The User's API keys and addresses
SPOT_API_KEY = os.getenv('SPOT_API_KEY')
SPOT_SECRET_KEY = os.getenv('SPOT_SECRET_KEY')
FUTURES_API_KEY = os.getenv('FUTURES_API_KEY')
FUTURES_SECRET_KEY = os.getenv('FUTURES_SECRET_KEY')
ADDRESS_ONE = os.getenv('ADDRESS_ONE')

# Initialize the Binance Spot exchange
binance_spot = ccxt.binance({
    'apiKey': SPOT_API_KEY,
    'secret': SPOT_SECRET_KEY,
})

# Initialize the Binance Futures exchange
binance_futures = ccxt.binanceusdm({
    'apiKey': FUTURES_API_KEY,
    'secret': FUTURES_SECRET_KEY,
})

#Function For Fetching OHLCV
def fetch_OHLCV(symbol, timeframe, limit=1500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Function to calculate HT_TRENDMODE (Hilbert Transform - Trend Mode)
def calculate_ht_trendmode(df):
    # Ensure close column is present
    if 'close' not in df.columns:
        raise ValueError("Missing required columns in DataFrame")
    
    # Calculate the HT_TRENDMODE (Hilbert Transform - Trend Mode) using TA-Lib
    trendmode_values = ta.HT_TRENDMODE(df['close'])
    
    # Combine with timestamp and close price in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'ht_trendmode': trendmode}]
        for idx, (row, trendmode) in enumerate(zip(df.to_dict('records'), trendmode_values))
    ]
    
    return result

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2)

# Calculate HT_TRENDMODE (Hilbert Transform - Trend Mode)
ht_trendmode_result = calculate_ht_trendmode(ohlcv_data)
ht_trendmode_result2 = calculate_ht_trendmode(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - HT_TRENDMODE (Hilbert Transform - Trend Mode)")
for entry in ht_trendmode_result:
    print(entry)
print("")
print("5 MINUTES CHART - HT_TRENDMODE (Hilbert Transform - Trend Mode)")
for entry in ht_trendmode_result2:
    print(entry)