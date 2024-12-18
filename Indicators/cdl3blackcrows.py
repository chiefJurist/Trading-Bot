import ccxt
import pandas as pd
import talib as ta
import time
import math
import numpy as np

# The User's API keys and addresses
SPOT_API_KEY = 'lwObDP3Fcjia0OxQfombVxtG032NZWuFE4ctgKZPxBJYzblviFUd3ONUFAuOwcJq'
SPOT_SECRET_KEY = 'PIx7RsETsxoqkJUaltX5pssmHnCMSXqUmb0lJv5OHR4RxS9kOtN2UCeYAtqFFAVm'
FUTURES_API_KEY = 'FGqsynCXzPJoBJvcLG28EkQg2HvWlE4ANzt9Q3IIVH1iCqvuZ3jQh4Ipw2SzcpYn'
FUTURES_SECRET_KEY = 'Tg0IcgRO3Xh7PhxfSUs6MfheM46uWa7BIydrLy2Q3ker2VWIQlMvHBmiq566EVEz'
ADDRESS_ONE = '0x9D95d4751fCc02157d55527Ca4D50588bCC80590'

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

# Function to calculate CDL3BLACKCROWS (Three Black Crows candlestick pattern)
def calculate_cdl3blackcrows(df):
    # Ensure open, high, low, and close columns are present
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        raise ValueError("Missing required columns in DataFrame")
    
    # Calculate the CDL3BLACKCROWS pattern using TA-Lib
    cdl3blackcrows = ta.CDL3BLACKCROWS(df['open'], df['high'], df['low'], df['close'])
    
    # Combine with timestamp and close price in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'cdl3blackcrows': pattern}]
        for idx, (row, pattern) in enumerate(zip(df.to_dict('records'), cdl3blackcrows))
    ]
    
    return result

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2
limit = 500  # Number of candles to fetch

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe, limit)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2, limit)

# Calculate CDL3BLACKCROWS (Three Black Crows candlestick pattern)
cdl3blackcrows_result = calculate_cdl3blackcrows(ohlcv_data)
cdl3blackcrows_result2 = calculate_cdl3blackcrows(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - CDL3BLACKCROWS (Three Black Crows)")
for entry in cdl3blackcrows_result:
    print(entry)
print("")
print("5 MINUTES CHART - CDL3BLACKCROWS (Three Black Crows)")
for entry in cdl3blackcrows_result2:
    print(entry)