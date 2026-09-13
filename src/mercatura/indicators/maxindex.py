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
def fetch_OHLCV(symbol, timeframe, limit=500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Function to calculate MAXINDEX (Index of Maximum Price over a given period)
def calculate_maxindex(df, period=14):
    # Ensure close column is present
    if 'close' not in df.columns:
        raise ValueError("Missing required columns in DataFrame")
    
    # Calculate MAXINDEX using TA-Lib
    maxindex_values = ta.MAXINDEX(df['close'], timeperiod=period)
    
    # Combine with timestamp, close price, and MAXINDEX value in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'maxindex': max_idx}]
        for idx, (row, max_idx) in enumerate(zip(df.to_dict('records'), maxindex_values))
    ]
    
    return result

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2
limit = 500  # Number of candles to fetch

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe, limit)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2, limit)

# Calculate MAXINDEX (Index of Maximum Price over a given period)
maxindex_result = calculate_maxindex(ohlcv_data)
maxindex_result2 = calculate_maxindex(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - MAXINDEX (Index of Maximum Price)")
for entry in maxindex_result:
    print(entry)
print("")
print("5 MINUTES CHART - MAXINDEX (Index of Maximum Price)")
for entry in maxindex_result2:
    print(entry)