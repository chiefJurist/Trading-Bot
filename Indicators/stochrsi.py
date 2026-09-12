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

# Function to calculate STOCHRSI (Stochastic RSI) using TA-Lib
def calculate_stochrsi(df, rsi_period=14, stoch_period=14, smooth_k=3, smooth_d=3):
    # Ensure close column is present
    if 'close' not in df.columns:
        raise ValueError("Missing required 'close' column in DataFrame")

    # Calculate Stochastic RSI using TA-Lib
    stochrsi_k, stochrsi_d = ta.STOCHRSI(df['close'], timeperiod=stoch_period, fastk_period=smooth_k, fastd_period=smooth_d)

    # Combine with timestamp, close price, and Stochastic RSI values in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'stochrsi_k': k, 'stochrsi_d': d}]
        for idx, (row, k, d) in enumerate(zip(df.to_dict('records'), stochrsi_k, stochrsi_d))
    ]
    
    return result

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2)

# Calculate STOCHRSI (Stochastic RSI)
stochrsi_result = calculate_stochrsi(ohlcv_data)
stochrsi_result2 = calculate_stochrsi(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - STOCHRSI")
for entry in stochrsi_result:
    print(entry)
print("")
print("5 MINUTES CHART - STOCHRSI")
for entry in stochrsi_result2:
    print(entry)