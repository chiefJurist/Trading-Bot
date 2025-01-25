import ccxt
import pandas as pd
import talib as ta
import time
import math
from datetime import timezone, timedelta
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

# Function For Fetching OHLCV
def fetch_OHLCV(symbol, timeframe, limit=1500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    # Convert to UTC+1 for Nigeria
    df['timestamp'] = df['timestamp'].dt.tz_convert(timezone(timedelta(hours=1)))
    return df

# Function to calculate Bollinger Bands
def calculate_bollinger_bands(df, timeperiod=20, nbdevup=1, nbdevdn=1):
    upperband, middleband, lowerband = ta.BBANDS(
        df['close'], timeperiod=timeperiod, nbdevup=nbdevup, nbdevdn=nbdevdn, matype=0
    )
    df['upperband'] = upperband
    df['middleband'] = middleband
    df['lowerband'] = lowerband
    return df

# Function to detect bullish and bearish patterns
def detect_patterns(df_1m, df_5m):
    bullish_signals = []
    bearish_signals = []

    # Check 1m chart for initial criteria
    for i in range(1, len(df_1m)):
        # Bullish condition on 1m chart
        if (df_1m['close'].iloc[i] > df_1m['lowerband'].iloc[i]) and \
           (df_1m['close'].iloc[i - 1] < df_1m['lowerband'].iloc[i - 1]):
            
            # Check 5m chart for confirmation
            last_5m = df_5m.iloc[-3:]  # Get the last 3 candles
            if all(last_5m['close'] > last_5m['open']):  # All 3 candles bullish
                if (last_5m['close'].iloc[-1] > last_5m['lowerband'].iloc[-1]) and \
                   (last_5m['close'].iloc[-1] > last_5m['close'].iloc[-2] > last_5m['close'].iloc[-3]):
                    bullish_signals.append(df_1m['timestamp'].iloc[i])

        # Bearish condition on 1m chart
        if (df_1m['close'].iloc[i] < df_1m['upperband'].iloc[i]) and \
           (df_1m['close'].iloc[i - 1] > df_1m['upperband'].iloc[i - 1]):
            
            # Check 5m chart for confirmation
            last_5m = df_5m.iloc[-3:]  # Get the last 3 candles
            if all(last_5m['close'] < last_5m['open']):  # All 3 candles bearish
                if (last_5m['close'].iloc[-1] < last_5m['upperband'].iloc[-1]) and \
                   (last_5m['close'].iloc[-1] < last_5m['close'].iloc[-2] < last_5m['close'].iloc[-3]):
                    bearish_signals.append(df_1m['timestamp'].iloc[i])

    return bullish_signals, bearish_signals

# Main Execution
symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2

# Fetch OHLCV data
ohlcv_data_1m = fetch_OHLCV(symbol, timeframe)
ohlcv_data_5m = fetch_OHLCV(symbol, timeframe2)

# Calculate Bollinger Bands
df_1m = calculate_bollinger_bands(ohlcv_data_1m)
df_5m = calculate_bollinger_bands(ohlcv_data_5m)

# Detect patterns
bullish_signals, bearish_signals = detect_patterns(df_1m, df_5m)

# Print Results
print("Bullish Signals (1m chart):")
for ts in bullish_signals:
    print(f"Timestamp: {ts}")

print("\nBearish Signals (1m chart):")
for ts in bearish_signals:
    print(f"Timestamp: {ts}")