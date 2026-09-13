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

# Function to calculate TSF (Time Series Forecast)
def calculate_tsf(df, timeperiod=30):
    # Ensure the 'close' column is present
    if 'close' not in df.columns:
        raise ValueError("Missing 'close' column in DataFrame")

    # Calculate TSF using TA-Lib
    tsf_values = ta.TSF(df['close'], timeperiod=timeperiod)

    # Combine with timestamp, close price, and TSF value in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'tsf': ts}]
        for idx, (row, ts) in enumerate(zip(df.to_dict('records'), tsf_values))
    ]
    
    return result

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2
limit = 500  # Number of candles to fetch

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe, limit)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2, limit)

# Calculate TSF indicator
tsf_result = calculate_tsf(ohlcv_data)
tsf_result2 = calculate_tsf(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - TSF")
for entry in tsf_result:
    print(entry)
print("")
print("5 MINUTES CHART - TSF")
for entry in tsf_result2:
    print(entry)