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

# Function for fetching OHLCV
def fetch_OHLCV(symbol, timeframe, limit=41):
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

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1d'  # Example timeframe

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe)

# Calculate Bollinger Bands for both timeframes
ohlcv_data['upperband'], ohlcv_data['middleband'], ohlcv_data['lowerband'] = calculate_bollinger_bands(ohlcv_data['close'])

# Initialize results dictionary
pattern_matches = []

# Loop through all 1 day candles
for i in range(len(ohlcv_data)):
    # Get the needed data from the candle
    current_open = ohlcv_data['open'].iloc[i]
    current_close = ohlcv_data['close'].iloc[i]
    current_high = ohlcv_data['high'].iloc[i]
    current_low = ohlcv_data['low'].iloc[i]
    current_timestamp = ohlcv_data['timestamp'].iloc[i]


    # Check for bullish pattern
    if (current_close > current_open):
        pattern_matches.append({
            'timestamp': current_timestamp,
            'color': 'green',
            'open' : float(current_open),
            'close': float(current_close),
            'high': float(current_high),
            'low': float(current_low),
            'candle-size': float(current_close - current_open),
            'upper-wick': float(current_high - current_close),
            'lower-wick': float(current_open - current_low),

        })

    # Check for bearish pattern
    if (current_close < current_open):
        pattern_matches.append({
            'timestamp': current_timestamp,
            'color': 'red',
            'open' : float(current_open),
            'close': float(current_close),
            'high': float(current_high),
            'low': float(current_low),
            'candle-size': float(current_open - current_close),
            'upper-wick': float(current_high - current_open),
            'lower-wick': float(current_close - current_low),

        })

# Print all detected patterns in the desired format
formatted_pattern_matches = [
    [idx, match['timestamp'], {'color': match['color'], 'open': match['open'], 'candle-size': match['candle-size'], 'upper-wick': match['upper-wick'], 'lower-wick': match['lower-wick']}]
    for idx, match in enumerate(pattern_matches)
]

# Print the results
print("PATTERN MATCHES (1 MINUTE CHART)")
for entry in formatted_pattern_matches:
    print(entry)
    print('')