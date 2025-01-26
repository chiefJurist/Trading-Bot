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

# Function for fetching OHLCV (Open, High, Low, Close, Volume) data
def fetch_OHLCV(symbol, timeframe, limit=1500):
    # Fetches OHLCV data for the given symbol and timeframe
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    # Converts the fetched data into a pandas DataFrame for easier processing
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    # Converts the 'timestamp' column from milliseconds to a readable datetime format
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df  # Returns the processed DataFrame

# Function to calculate Bollinger Bands
def calculate_bollinger_bands(close_prices, timeperiod=20, nbdevup=1, nbdevdn=1):
    # Uses TA-Lib's BBANDS function to calculate Bollinger Bands
    upperband, middleband, lowerband = ta.BBANDS(
        close_prices,  # Series of closing prices
        timeperiod=timeperiod,  # Period for Bollinger Bands calculation
        nbdevup=nbdevup,  # Number of standard deviations above the middle band
        nbdevdn=nbdevdn,  # Number of standard deviations below the middle band
        matype=0  # Type of moving average (0 = simple moving average)
    )
    return upperband, middleband, lowerband  # Returns the calculated bands as separate arrays

# Specify the trading pair and timeframes
symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # 1-minute timeframe
timeframe2 = '5m'  # 5-minute timeframe

# Fetch OHLCV data for the specified timeframes
ohlcv_data = fetch_OHLCV(symbol, timeframe)  # Fetches 1-minute data
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2)  # Fetches 5-minute data

# Calculate Bollinger Bands for the fetched OHLCV data
ohlcv_data['upperband'], ohlcv_data['middleband'], ohlcv_data['lowerband'] = calculate_bollinger_bands(ohlcv_data['close'])
ohlcv_data2['upperband'], ohlcv_data2['middleband'], ohlcv_data2['lowerband'] = calculate_bollinger_bands(ohlcv_data2['close'])

# Initialize an empty list to store detected pattern matches
pattern_matches = []

# Iterate through all 1-minute candles, starting from the 3rd candle
for i in range(2, len(ohlcv_data)):
    # Retrieve the current and previous candles' details for the 1-minute chart
    last_close = ohlcv_data['close'].iloc[i]
    second_last_close = ohlcv_data['close'].iloc[i - 1]
    last_upperband = ohlcv_data['upperband'].iloc[i]
    last_lowerband = ohlcv_data['lowerband'].iloc[i]
    second_last_upperband = ohlcv_data['upperband'].iloc[i - 1]
    second_last_lowerband = ohlcv_data['lowerband'].iloc[i - 1]

    # Find the corresponding 5-minute candles based on the current 1-minute candle's timestamp
    current_timestamp = ohlcv_data['timestamp'].iloc[i]
    five_minute_candles = ohlcv_data2[ohlcv_data2['timestamp'] <= current_timestamp].iloc[-3:]

    # Skip if there are fewer than 3 5-minute candles
    if len(five_minute_candles) < 3:
        continue

    # Extract details for the last three 5-minute candles
    last_big_close = five_minute_candles['close'].iloc[-1]
    last_big_open = five_minute_candles['open'].iloc[-1]
    last_big_upperband = five_minute_candles['upperband'].iloc[-1]
    last_big_lowerband = five_minute_candles['lowerband'].iloc[-1]

    second_last_big_close = five_minute_candles['close'].iloc[-2]
    second_last_big_open = five_minute_candles['open'].iloc[-2]
    second_last_big_upperband = five_minute_candles['upperband'].iloc[-2]
    second_last_big_lowerband = five_minute_candles['lowerband'].iloc[-2]

    third_last_big_close = five_minute_candles['close'].iloc[-3]
    third_last_big_open = five_minute_candles['open'].iloc[-3]
    third_last_big_upperband = five_minute_candles['upperband'].iloc[-3]
    third_last_big_lowerband = five_minute_candles['lowerband'].iloc[-3]

    # Check for a bullish pattern
    if (
        last_close > last_lowerband and second_last_close < second_last_lowerband and
        last_big_close > last_big_lowerband and second_last_big_close > second_last_big_lowerband and third_last_big_close > third_last_big_lowerband and
        last_big_close > last_big_open and second_last_big_close > second_last_big_open and third_last_big_close > third_last_big_open
    ):
        # Append bullish pattern details to the results list
        pattern_matches.append({
            'timestamp': current_timestamp,
            'type': 'Bullish',
            'close': last_close,
            'upperband': last_upperband,
            'middleband': ohlcv_data['middleband'].iloc[i],
            'lowerband': last_lowerband
        })

    # Check for a bearish pattern
    if (
        last_close < last_upperband and second_last_close > second_last_upperband and
        last_big_close < last_big_upperband and second_last_big_close < second_last_big_upperband and third_last_big_close < third_last_big_upperband and
        last_big_close < last_big_open and second_last_big_close < second_last_big_open and third_last_big_close < third_last_big_open
    ):
        # Append bearish pattern details to the results list
        pattern_matches.append({
            'timestamp': current_timestamp,
            'type': 'Bearish',
            'close': last_close,
            'upperband': last_upperband,
            'middleband': ohlcv_data['middleband'].iloc[i],
            'lowerband': last_lowerband
        })

# Print all detected patterns
for match in pattern_matches:
    print(match)  # Prints each detected pattern with its details