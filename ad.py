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


# Function to calculate Chaikin A/D Line
def calculate_chaikin_ad(df):
    # Ensure high, low, close, and volume columns are present
    if not all(col in df.columns for col in ['high', 'low', 'close', 'volume']):
        raise ValueError("Missing required columns in DataFrame")

    # Calculate the Chaikin A/D Line using TA-Lib
    ad_line = ta.AD(df['high'], df['low'], df['close'], df['volume'])

    # Combine with timestamp and close price in the output
    result = [
        {
            'index': idx,
            'timestamp': row['timestamp'],
            'close': row['close'],
            'ad_line': ad
        }
        for idx, (row, ad) in enumerate(zip(df.to_dict('records'), ad_line))
    ]

    return result


symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2
limit = 500  # Number of candles to fetch

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe, limit)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2, limit)

# Calculate Chaikin A/D Line
chaikin_ad_result = calculate_chaikin_ad(ohlcv_data)
chaikin_ad_result2 = calculate_chaikin_ad(ohlcv_data2)


# Print the result
print("1 MINUTE CHART")
for entry in chaikin_ad_result:
    print(entry)
print("")
print("5 MINUTES CHART")
for entry in chaikin_ad_result2:
    print(entry)