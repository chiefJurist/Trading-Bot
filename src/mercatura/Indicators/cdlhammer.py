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

# Function to calculate CDLHAMMER (Hammer candlestick pattern)
def calculate_cdlhammer(df):
    # Ensure open, high, low, and close columns are present
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        raise ValueError("Missing required columns in DataFrame")
    
    # Calculate the CDLHAMMER pattern using TA-Lib
    cdlhammer = ta.CDLHAMMER(df['open'], df['high'], df['low'], df['close'])
    
    # Combine with timestamp and close price in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'cdlhammer': pattern}]
        for idx, (row, pattern) in enumerate(zip(df.to_dict('records'), cdlhammer))
    ]
    
    return result

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
# timeframe2 = '5m'  # Example timeframe 2
limit = 1500  # Number of candles to fetch

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe, limit)
# ohlcv_data2 = fetch_OHLCV(symbol, timeframe2, limit)

# Calculate CDLHAMMER (Hammer candlestick pattern)
cdlhammer_result = calculate_cdlhammer(ohlcv_data)
# cdlhammer_result2 = calculate_cdlhammer(ohlcv_data2)

# Print only rows where 'cdlhammer' is nonzero
print("1 MINUTE CHART - CDLHAMMER (Hammer)")
filtered_results = [entry for entry in cdlhammer_result if entry[2]['cdlhammer'] != 0]

for entry in filtered_results:
    print(entry)

# # Print the result
# print("1 MINUTE CHART - CDLHAMMER (Hammer)")
# for entry in cdlhammer_result:
#     print(entry)
# print("")
# print("5 MINUTES CHART - CDLHAMMER (Hammer)")
# for entry in cdlhammer_result2:
#     print(entry)