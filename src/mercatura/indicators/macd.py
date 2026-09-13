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

# Function to calculate MACD (Moving Average Convergence Divergence)
def calculate_macd(df, fastperiod=12, slowperiod=26, signalperiod=9):
    # Ensure close column is present
    if 'close' not in df.columns:
        raise ValueError("Missing required columns in DataFrame")
    
    # Calculate MACD using TA-Lib
    macd, macdsignal, macdhist = ta.MACD(df['close'], fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)
    
    # Combine with timestamp, close price, MACD, MACD Signal, and MACD Histogram in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'macd': m, 'macdsignal': ms, 'macdhist': mh}]
        for idx, (row, m, ms, mh) in enumerate(zip(df.to_dict('records'), macd, macdsignal, macdhist))
    ]
    
    return result

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2)

# Calculate MACD (Moving Average Convergence Divergence)
macd_result = calculate_macd(ohlcv_data)
macd_result2 = calculate_macd(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - MACD (Moving Average Convergence Divergence)")
for entry in macd_result:
    print(entry)
print("")
print("5 MINUTES CHART - MACD (Moving Average Convergence Divergence)")
for entry in macd_result2:
    print(entry)