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

# Function to calculate CDL3INSIDE (Three Inside Up/Down candlestick pattern)
def calculate_cdl3inside(df):
    # Ensure open, high, low, and close columns are present
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        raise ValueError("Missing required columns in DataFrame")
    
    # Calculate the CDL3INSIDE pattern using TA-Lib
    cdl3inside = ta.CDL3INSIDE(df['open'], df['high'], df['low'], df['close'])
    
    # Combine with timestamp and close price in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'cdl3inside': pattern}]
        for idx, (row, pattern) in enumerate(zip(df.to_dict('records'), cdl3inside))
    ]
    
    return result

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2
limit = 500  # Number of candles to fetch

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe, limit)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2, limit)

# Calculate CDL3INSIDE (Three Inside Up/Down candlestick pattern)
cdl3inside_result = calculate_cdl3inside(ohlcv_data)
cdl3inside_result2 = calculate_cdl3inside(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - CDL3INSIDE (Three Inside Up/Down)")
for entry in cdl3inside_result:
    print(entry)
print("")
print("5 MINUTES CHART - CDL3INSIDE (Three Inside Up/Down)")
for entry in cdl3inside_result2:
    print(entry)