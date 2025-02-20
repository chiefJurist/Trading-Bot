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
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)  # Ensure UTC
    df['timestamp'] = df['timestamp'].dt.tz_convert('Etc/GMT-1')  # Convert to UTC+1
    df['timestamp'] = df['timestamp'].dt.tz_localize(None)  # Remove timezone info

    return df

# Function to calculate Bollinger Bands
def calculate_bollinger_bands(close_prices, timeperiod=20, nbdevup=1, nbdevdn=1):
    upperband, middleband, lowerband = ta.BBANDS(
        close_prices, timeperiod=timeperiod, nbdevup=nbdevup, nbdevdn=nbdevdn, matype=0
    )
    return upperband, middleband, lowerband

# Function to calculate EMA 50 and EMA 200
def calculate_ema(close_prices, ema_periods=(50, 200)):
    ema_50 = ta.EMA(close_prices, timeperiod=ema_periods[0])
    ema_200 = ta.EMA(close_prices, timeperiod=ema_periods[1])
    return ema_50, ema_200

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '5m'  # Example timeframe

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe)

# Calculate Bollinger Bands and EMA
ohlcv_data['upperband'], ohlcv_data['middleband'], ohlcv_data['lowerband'] = calculate_bollinger_bands(ohlcv_data['close'])
ohlcv_data['ema_50'], ohlcv_data['ema_200'] = calculate_ema(ohlcv_data['close'])

# Initialize results dictionary
pattern_matches = []

# Loop through all 1 day candles
for i in range(len(ohlcv_data)):
    # Get the needed data from the candle
    current_open = ohlcv_data['open'].iloc[i]
    current_close = ohlcv_data['close'].iloc[i]
    current_timestamp = ohlcv_data['timestamp'].iloc[i]
    current_ema50 = ohlcv_data['ema_50'].iloc[i]
    current_ema200 = ohlcv_data['ema_200'].iloc[i]

    if (current_close > current_open):
        color = 'green'
    else:
        color = 'red'

    # Check for bullish pattern
    if (current_close > current_ema50 and current_ema50 > current_ema200):
        pattern_matches.append({
            'timestamp': current_timestamp,
            'type': 'bullish',
            'open' : float(current_open),
            'close': float(current_close),
            'EMA-50': float(current_ema50),
            'EMA-200': float(current_ema200),
            'color' : color
        })

    # Check for bearish pattern
    if (current_close < current_ema50 and current_ema50 < current_ema200):
        pattern_matches.append({
            'timestamp': current_timestamp,
            'type': 'bearish',
            'open' : float(current_open),
            'close': float(current_close),
            'EMA-50': float(current_ema50),
            'EMA-200': float(current_ema200),
            'color' : color
        })

# Print all detected patterns in the desired format
formatted_pattern_matches = [
    [idx, match['timestamp'], {'type': match['type'], 'open': match['open'], 'close': match['close'], 'EMA-50': match['EMA-50'], 'EMA-200': match['EMA-200']}]
    for idx, match in enumerate(pattern_matches)
]

# Print the results
print("PATTERN MATCHES (1 MINUTE CHART)")
for entry in formatted_pattern_matches:
    print(entry)
    print('')