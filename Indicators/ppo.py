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

# Function to calculate PPO (Percentage Price Oscillator)
def calculate_ppo(df, fastperiod=12, slowperiod=26, matype=0):
    # Ensure close column is present
    if 'close' not in df.columns:
        raise ValueError("Missing required columns in DataFrame")

    # Calculate PPO using TA-Lib
    ppo_values, signal_values, hist_values = ta.PPO(df['close'], fastperiod=fastperiod, slowperiod=slowperiod, matype=matype)

    # Combine with timestamp, close price, PPO value, signal value, and histogram in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'ppo': ppo, 'signal': signal, 'histogram': hist}]
        for idx, (row, ppo, signal, hist) in enumerate(zip(df.to_dict('records'), ppo_values, signal_values, hist_values))
    ]
    
    return result

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2
limit = 500  # Number of candles to fetch

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe, limit)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2, limit)

# Calculate PPO (Percentage Price Oscillator)
ppo_result = calculate_ppo(ohlcv_data)
ppo_result2 = calculate_ppo(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - PPO")
for entry in ppo_result:
    print(entry)
print("")
print("5 MINUTES CHART - PPO")
for entry in ppo_result2:
    print(entry)