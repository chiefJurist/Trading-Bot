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

# Function to calculate ROCR100 (Rate of Change Ratio 100)
def calculate_rocr100(df, timeperiod=10):
    # Ensure close column is present
    if 'close' not in df.columns:
        raise ValueError("Missing required columns in DataFrame")

    # Calculate ROCR100 using TA-Lib
    rocr100_values = ta.ROCR100(df['close'], timeperiod=timeperiod)

    # Combine with timestamp, close price, and ROCR100 value in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'rocr100': rocr100}]
        for idx, (row, rocr100) in enumerate(zip(df.to_dict('records'), rocr100_values))
    ]
    
    return result

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2
limit = 500  # Number of candles to fetch

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe, limit)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2, limit)

# Calculate ROCR100 (Rate of Change Ratio 100)
rocr100_result = calculate_rocr100(ohlcv_data)
rocr100_result2 = calculate_rocr100(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - ROCR100")
for entry in rocr100_result:
    print(entry)
print("")
print("5 MINUTES CHART - ROCR100")
for entry in rocr100_result2:
    print(entry)