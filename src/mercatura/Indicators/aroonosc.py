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

# Function to calculate Aroon Oscillator (AroonOsc)
def calculate_aroonosc(df, period=14):
    # Ensure high and low columns are present
    if not all(col in df.columns for col in ['high', 'low']):
        raise ValueError("Missing required columns in DataFrame")
    
    # Calculate the Aroon Up and Aroon Down using TA-Lib
    aroon_up, aroon_down = ta.AROON(df['high'], df['low'], timeperiod=period)
    
    # Calculate the Aroon Oscillator as the difference between Aroon Up and Aroon Down
    aroon_osc = aroon_up - aroon_down
    
    # Combine with timestamp and close price in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'aroon_osc': osc}]
        for idx, (row, osc) in enumerate(zip(df.to_dict('records'), aroon_osc))
    ]
    
    return result


symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2)

# Calculate Aroon Oscillator (AroonOsc)
aroonosc_result = calculate_aroonosc(ohlcv_data)
aroonosc_result2 = calculate_aroonosc(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - Aroon Oscillator")
for entry in aroonosc_result:
    print(entry)
print("")
print("5 MINUTES CHART - Aroon Oscillator")
for entry in aroonosc_result2:
    print(entry)