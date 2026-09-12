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

# Function to calculate T3 (Triple Exponential Moving Average)
def calculate_t3(df, timeperiod=14, vfactor=0.7):
    # Ensure the 'close' column is present
    if 'close' not in df.columns:
        raise ValueError("Missing 'close' column in DataFrame")

    # Calculate T3 using TA-Lib
    t3_values = ta.T3(df['close'], timeperiod=timeperiod, vfactor=vfactor)

    # Combine with timestamp, close price, and T3 value in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 't3': t3_value}]
        for idx, (row, t3_value) in enumerate(zip(df.to_dict('records'), t3_values))
    ]
    
    return result

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2)

# Calculate T3 indicator
t3_result = calculate_t3(ohlcv_data)
t3_result2 = calculate_t3(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - T3")
for entry in t3_result:
    print(entry)
print("")
print("5 MINUTES CHART - T3")
for entry in t3_result2:
    print(entry)