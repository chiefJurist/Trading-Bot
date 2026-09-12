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

# Function to calculate SMA (Simple Moving Average)
def calculate_sma(df, timeperiod=14):
    # Ensure close column is present
    if 'close' not in df.columns:
        raise ValueError("Missing required 'close' column in DataFrame")

    # Calculate SMA using TA-Lib
    sma_values = ta.SMA(df['close'], timeperiod=timeperiod)

    # Combine with timestamp, close price, and SMA value in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'sma': sma}]
        for idx, (row, sma) in enumerate(zip(df.to_dict('records'), sma_values))
    ]
    
    return result

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2)

# Calculate SMA (Simple Moving Average)
sma_result = calculate_sma(ohlcv_data)
sma_result2 = calculate_sma(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - SMA")
for entry in sma_result:
    print(entry)
print("")
print("5 MINUTES CHART - SMA")
for entry in sma_result2:
    print(entry)