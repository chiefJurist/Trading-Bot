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

# Function to calculate Absolute Price Oscillator (APO)
def calculate_apo(df, fast_period=12, slow_period=26):
    # Ensure close column is present
    if 'close' not in df.columns:
        raise ValueError("Missing required 'close' column in DataFrame")
    
    # Calculate the fast and slow EMAs
    fast_ema = ta.EMA(df['close'], timeperiod=fast_period)
    slow_ema = ta.EMA(df['close'], timeperiod=slow_period)
    
    # Calculate APO as the difference between fast and slow EMAs
    apo = fast_ema - slow_ema
    
    # Combine with timestamp and close price in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'apo': apo_value}]
        for idx, (row, apo_value) in enumerate(zip(df.to_dict('records'), apo))
    ]
    
    return result


symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2
limit = 500  # Number of candles to fetch

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe, limit)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2, limit)

# Calculate Absolute Price Oscillator (APO)
apo_result = calculate_apo(ohlcv_data)
apo_result2 = calculate_apo(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - APO")
for entry in apo_result:
    print(entry)
print("")
print("5 MINUTES CHART - APO")
for entry in apo_result2:
    print(entry)