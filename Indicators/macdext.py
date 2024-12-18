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

# Function to calculate MACDEXT (MACD with Extended Options)
def calculate_macdext(df, fastperiod=12, slowperiod=26, signalperiod=9, movavg='ema'):
    # Ensure close column is present
    if 'close' not in df.columns:
        raise ValueError("Missing required columns in DataFrame")
    
    # Calculate MACDEXT using TA-Lib with extended options
    macd, macdsignal, macdhist = ta.MACDEXT(df['close'], fastperiod=fastperiod, slowperiod=slowperiod, 
                                             signalperiod=signalperiod, 
                                             movav=ta.MA_Type.__dict__.get(movavg.lower(), ta.MA_Type.EMA))
    
    # Combine with timestamp, close price, MACD, MACD Signal, and MACD Histogram in the output
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'macd': m, 'macdsignal': ms, 'macdhist': mh}]
        for idx, (row, m, ms, mh) in enumerate(zip(df.to_dict('records'), macd, macdsignal, macdhist))
    ]
    
    return result

symbol = 'ETH/USDT'  # Example trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe 2
limit = 500  # Number of candles to fetch

# Fetch OHLCV data
ohlcv_data = fetch_OHLCV(symbol, timeframe, limit)
ohlcv_data2 = fetch_OHLCV(symbol, timeframe2, limit)

# Calculate MACDEXT (MACD with Extended Options)
macdext_result = calculate_macdext(ohlcv_data)
macdext_result2 = calculate_macdext(ohlcv_data2)

# Print the result
print("1 MINUTE CHART - MACDEXT (MACD with Extended Options)")
for entry in macdext_result:
    print(entry)
print("")
print("5 MINUTES CHART - MACDEXT (MACD with Extended Options)")
for entry in macdext_result2:
    print(entry)