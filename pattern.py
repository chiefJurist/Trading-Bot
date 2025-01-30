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

# Function for fetching OHLCV
def fetch_OHLCV(symbol, timeframe, limit=1500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Function to calculate Bollinger Bands
def calculate_bollinger_bands(close_prices, timeperiod=20, nbdevup=1, nbdevdn=1):
    upperband, middleband, lowerband = ta.BBANDS(
        close_prices, timeperiod=timeperiod, nbdevup=nbdevup, nbdevdn=nbdevdn, matype=0
    )
    return upperband, middleband, lowerband

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe)

# Calculate Bollinger Bands for both timeframes
ohlcv_data['upperband'], ohlcv_data['middleband'], ohlcv_data['lowerband'] = calculate_bollinger_bands(ohlcv_data['close'])

# Initialize results dictionary
pattern_matches = []

# Loop through all 1-minute candles (starting from the 3rd candle to avoid out-of-bound errors)
for i in range(2, len(ohlcv_data)):
    # Get the current and previous candles for the 1-minute chart
    current_close = ohlcv_data['close'].iloc[i]
    last_close = ohlcv_data['close'].iloc[i - 1]
    second_last_close = ohlcv_data['close'].iloc[i - 2]
    third_last_close = ohlcv_data['close'].iloc[i - 3]
    current_open = ohlcv_data['open'].iloc[i]
    last_open = ohlcv_data['open'].iloc[i - 1]
    second_last_open = ohlcv_data['open'].iloc[i - 2]
    third_last_open = ohlcv_data['open'].iloc[i - 3]
    current_upperband = ohlcv_data['upperband'].iloc[i]
    last_upperband = ohlcv_data['upperband'].iloc[i - 1]
    second_last_upperband = ohlcv_data['upperband'].iloc[i - 2]
    third_last_upperband = ohlcv_data['upperband'].iloc[i - 3]
    current_lowerband = ohlcv_data['lowerband'].iloc[i]
    last_lowerband = ohlcv_data['lowerband'].iloc[i - 1]
    second_last_lowerband = ohlcv_data['lowerband'].iloc[i - 2]
    third_last_lowerband = ohlcv_data['lowerband'].iloc[i - 3]

    # Find the corresponding 5-minute candles
    current_timestamp = ohlcv_data['timestamp'].iloc[i]


    # Check for bullish pattern
    if (
        last_close > last_lowerband and second_last_close > second_last_lowerband and third_last_close < third_last_lowerband and second_last_close > second_last_open and last_close > last_open
    ):
        pattern_matches.append({
            'timestamp': current_timestamp,
            'type': 'Bullish',
            'close': current_close,
            'lowerband': current_lowerband,
            'upperband': current_upperband,
        })

    # Check for bearish pattern
    if (
        last_close < last_upperband and second_last_close < second_last_upperband and third_last_close > third_last_upperband and second_last_close < second_last_open and last_close < last_open
    ):
        pattern_matches.append({
            'timestamp': current_timestamp,
            'type': 'Bearish',
            'close': current_close,
            'lowerband': current_lowerband,
            'upperband': current_upperband,
        })

# Print all detected patterns in the desired format
formatted_pattern_matches = [
    [idx, match['timestamp'], {'type': match['type'], 'close': match['close'], 'lowerband': match['lowerband'], 'upperband': match['upperband']}]
    for idx, match in enumerate(pattern_matches)
]

# Print the results
print("PATTERN MATCHES (1 MINUTE CHART)")
for entry in formatted_pattern_matches:
    print(entry)