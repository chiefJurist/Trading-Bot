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

# Function For Fetching OHLCV with support for up to 3000 candles for the 1-minute timeframe
def fetch_OHLCV(symbol, timeframe, limit=3000):
    max_limit = 1500  # Binance's maximum limit per fetch
    all_data = []

    if timeframe == '1m' and limit > max_limit:
        remaining = limit
        since = None  # Fetch from the latest data point first
        while remaining > 0:
            batch_limit = min(max_limit, remaining)
            batch_data = binance_futures.fetch_ohlcv(symbol, timeframe, limit=batch_limit, since=since)
            if not batch_data:
                break  # No more data available
            all_data = batch_data + all_data  # Add new batch to the start (reverse order)
            since = batch_data[0][0] - (60 * 1000)  # Move since backward by 1 minute
            remaining -= len(batch_data)
    else:
        all_data = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Function to calculate Aroon Indicator
def calculate_aroon(df, period=14):
    # Ensure high and low columns are present
    if not all(col in df.columns for col in ['high', 'low']):
        raise ValueError("Missing required columns in DataFrame")
    
    # Calculate the Aroon Up and Aroon Down using TA-Lib
    aroon_up, aroon_down = ta.AROON(df['high'], df['low'], timeperiod=period)
    
    # Combine with timestamp and close price in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'aroon_up': up, 'aroon_down': down}]
        for idx, (row, up, down) in enumerate(zip(df.to_dict('records'), aroon_up, aroon_down))
    ]
    
    return result


symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2
limit = 500  # Number of candles to fetch

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe, limit)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2, limit)

# Calculate Aroon Indicator
aroon_result = calculate_aroon(ohlcv_data)
aroon_result2 = calculate_aroon(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - Aroon Indicator")
for entry in aroon_result:
    print(entry)
print("")
print("5 MINUTES CHART - Aroon Indicator")
for entry in aroon_result2:
    print(entry)