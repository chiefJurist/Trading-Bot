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

# Function to calculate ULTOSC (Ultimate Oscillator)
def calculate_ultosc(df, short_period=7, medium_period=14, long_period=28):
    # Ensure high, low, and close columns are present
    if not all(col in df.columns for col in ['high', 'low', 'close']):
        raise ValueError("Missing required columns in DataFrame")

    # Calculate Ultimate Oscillator using TA-Lib
    ultosc_values = ta.ULTOSC(df['high'], df['low'], df['close'], timeperiod1=short_period, timeperiod2=medium_period, timeperiod3=long_period)

    # Combine with timestamp and Ultimate Oscillator values in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'ultosc': ultosc}]
        for idx, (row, ultosc) in enumerate(zip(df.to_dict('records'), ultosc_values))
    ]
    
    return result

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2)

# Calculate ULTOSC (Ultimate Oscillator)
ultosc_result = calculate_ultosc(ohlcv_data)
ultosc_result2 = calculate_ultosc(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - ULTOSC")
for entry in ultosc_result:
    print(entry)
print("")
print("5 MINUTES CHART - ULTOSC")
for entry in ultosc_result2:
    print(entry)