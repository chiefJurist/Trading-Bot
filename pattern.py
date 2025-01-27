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
timeframe2 = '5m'  # Example timeframe 2

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2)

# Calculate Bollinger Bands for both timeframes
ohlcv_data['upperband'], ohlcv_data['middleband'], ohlcv_data['lowerband'] = calculate_bollinger_bands(ohlcv_data['close'])
ohlcv_data2['upperband'], ohlcv_data2['middleband'], ohlcv_data2['lowerband'] = calculate_bollinger_bands(ohlcv_data2['close'])

# Initialize results dictionary
pattern_matches = []

# Loop through all 1-minute candles (starting from the 3rd candle to avoid out-of-bound errors)
for i in range(2, len(ohlcv_data)):
    # Get the current and previous candles for the 1-minute chart
    last_close = ohlcv_data['close'].iloc[i - 1]
    second_last_close = ohlcv_data['close'].iloc[i - 2]
    last_upperband = ohlcv_data['upperband'].iloc[i - 1]
    last_lowerband = ohlcv_data['lowerband'].iloc[i - 1]
    second_last_upperband = ohlcv_data['upperband'].iloc[i - 2]
    second_last_lowerband = ohlcv_data['lowerband'].iloc[i - 2]

    # Find the corresponding 5-minute candles
    current_timestamp = ohlcv_data['timestamp'].iloc[i - 1]
    
    # Extract 5-minute candle details
    last_big_close = ohlcv_data2.loc[(ohlcv_data2['timestamp'] < current_timestamp) & ((current_timestamp - ohlcv_data2['timestamp']) < pd.Timedelta(minutes=10)), 'close'].iloc[-1]
    last_big_open = ohlcv_data2.loc[(ohlcv_data2['timestamp'] < current_timestamp) & ((current_timestamp - ohlcv_data2['timestamp']) < pd.Timedelta(minutes=10)), 'open'].iloc[-1]
    last_big_upperband = ohlcv_data2.loc[(ohlcv_data2['timestamp'] < current_timestamp) & ((current_timestamp - ohlcv_data2['timestamp']) < pd.Timedelta(minutes=10)), 'upperband'].iloc[-1]
    last_big_lowerband = ohlcv_data2.loc[(ohlcv_data2['timestamp'] < current_timestamp) & ((current_timestamp - ohlcv_data2['timestamp']) < pd.Timedelta(minutes=10)), 'lowerband'].iloc[-1]

    second_last_big_close = ohlcv_data2.loc[(ohlcv_data2['timestamp'] < current_timestamp) & ((current_timestamp - ohlcv_data2['timestamp']) < pd.Timedelta(minutes=10)), 'close'].iloc[-2]
    second_last_big_open = ohlcv_data2.loc[(ohlcv_data2['timestamp'] < current_timestamp) & ((current_timestamp - ohlcv_data2['timestamp']) < pd.Timedelta(minutes=10)), 'open'].iloc[-2]
    second_last_big_upperband = ohlcv_data2.loc[(ohlcv_data2['timestamp'] < current_timestamp) & ((current_timestamp - ohlcv_data2['timestamp']) < pd.Timedelta(minutes=10)), 'upperband'].iloc[-2]
    second_last_big_lowerband = ohlcv_data2.loc[(ohlcv_data2['timestamp'] < current_timestamp) & ((current_timestamp - ohlcv_data2['timestamp']) < pd.Timedelta(minutes=10)), 'lowerband'].iloc[-2]

    third_last_big_close = ohlcv_data2.loc[(ohlcv_data2['timestamp'] < current_timestamp) & ((current_timestamp - ohlcv_data2['timestamp']) < pd.Timedelta(minutes=10)), 'close'].iloc[-3]
    third_last_big_open = ohlcv_data2.loc[(ohlcv_data2['timestamp'] < current_timestamp) & ((current_timestamp - ohlcv_data2['timestamp']) < pd.Timedelta(minutes=10)), 'open'].iloc[-3]
    third_last_big_upperband = ohlcv_data2.loc[(ohlcv_data2['timestamp'] < current_timestamp) & ((current_timestamp - ohlcv_data2['timestamp']) < pd.Timedelta(minutes=10)), 'upperband'].iloc[-3]
    third_last_big_lowerband = ohlcv_data2.loc[(ohlcv_data2['timestamp'] < current_timestamp) & ((current_timestamp - ohlcv_data2['timestamp']) < pd.Timedelta(minutes=10)), 'lowerband'].iloc[-3]

    # Check for bullish pattern
    if (
        last_close > last_lowerband and second_last_close < second_last_lowerband and last_big_close > last_big_lowerband and second_last_big_close > second_last_big_lowerband  and last_big_close > last_big_open and second_last_big_close > second_last_big_open
    ):
        pattern_matches.append({
            'timestamp': current_timestamp,
            'type': 'Bullish',
            'close': last_close,
            'upperband': last_upperband,
            'lowerband': last_lowerband,
            '5m last upperband': last_big_upperband,
            '5m second to last ub': second_last_big_upperband,
            '5m third to last ub': third_last_big_upperband
        })

    # Check for bearish pattern
    if (
        last_close < last_upperband and second_last_close > second_last_upperband and last_big_close < last_big_upperband and second_last_big_close < second_last_big_upperband and third_last_big_close < third_last_big_upperband and last_big_close < last_big_open and second_last_big_close < second_last_big_open and third_last_big_close < third_last_big_open
    ):
        pattern_matches.append({
            'timestamp': current_timestamp,
            'type': 'Bearish',
            'close': last_close,
            'upperband': last_upperband,
            'lowerband': last_lowerband,
            '5m last upperband': last_big_upperband,
            '5m second to last ub': second_last_big_upperband,
            '5m third to last ub': third_last_big_upperband
        })

# Print all detected patterns
for match in pattern_matches:
    print(match)