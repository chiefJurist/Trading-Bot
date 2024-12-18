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

# Function For Fetching OHLCV
def fetch_OHLCV(symbol, timeframe, limit=500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Function to calculate Beta (BETA)
def calculate_beta(df1, df2, period=14):
    """
    Calculates the Beta indicator for two datasets.
    
    Args:
        df1: DataFrame for the primary asset (e.g., ETH/USDT)
        df2: DataFrame for the benchmark asset (e.g., BTC/USDT)
        period: The time period for the Beta calculation (default is 14)
    
    Returns:
        A list of Beta values.
    """
    # Ensure the close column is present in both DataFrames
    if 'close' not in df1.columns or 'close' not in df2.columns:
        raise ValueError("Missing 'close' column in one or both DataFrames")
    
    # Calculate the Beta using TA-Lib
    beta = ta.BETA(df1['close'], df2['close'], timeperiod=period)
    
    # Combine with the timestamp and close price of the primary asset
    result = [
        [idx, row['timestamp'], {'close': row['close'], 'beta': beta_value}]
        for idx, (row, beta_value) in enumerate(zip(df1.to_dict('records'), beta))
    ]
    
    return result


# Symbols and Timeframes
symbol1 = 'ETH/USDT'  # Primary trading pair
symbol2 = 'BTC/USDT'  # Benchmark trading pair
timeframe = '1m'  # Example timeframe
timeframe2 = '5m'  # Example timeframe
limit = 500  # Number of candles to fetch

# Fetch OHLCV data for both assets
ohlcv_data1 = fetch_OHLCV(symbol1, timeframe, limit)
ohlcv_data2 = fetch_OHLCV(symbol2, timeframe, limit)

ohlcv_data1_5m = fetch_OHLCV(symbol1, timeframe2, limit)
ohlcv_data2_5m = fetch_OHLCV(symbol2, timeframe2, limit)

# Calculate Beta for both timeframes
beta_result = calculate_beta(ohlcv_data1, ohlcv_data2)
beta_result_5m = calculate_beta(ohlcv_data1_5m, ohlcv_data2_5m)

# Print the result
print("1 MINUTE CHART - Beta (BETA)")
for entry in beta_result:
    print(entry)
print("")
print("5 MINUTES CHART - Beta (BETA)")
for entry in beta_result_5m:
    print(entry)