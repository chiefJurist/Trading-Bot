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

# Function to calculate MFI (Money Flow Index)
def calculate_mfi(df, period=14):
    # Ensure high, low, close, and volume columns are present
    if not all(col in df.columns for col in ['high', 'low', 'close', 'volume']):
        raise ValueError("Missing required columns in DataFrame")

    # Calculate MFI using TA-Lib
    mfi_values = ta.MFI(df['high'], df['low'], df['close'], df['volume'], timeperiod=period)

    # Combine with timestamp, close price, and MFI value in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'mfi': mfi}]
        for idx, (row, mfi) in enumerate(zip(df.to_dict('records'), mfi_values))
    ]
    
    return result

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2)

# Calculate MFI (Money Flow Index)
mfi_result = calculate_mfi(ohlcv_data)
mfi_result2 = calculate_mfi(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - MFI (Money Flow Index)")
for entry in mfi_result:
    print(entry)
print("")
print("5 MINUTES CHART - MFI (Money Flow Index)")
for entry in mfi_result2:
    print(entry)