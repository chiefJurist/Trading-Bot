import ccxt
import pandas as pd
import talib as ta
import numpy as np
import math
import time
import datetime

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

# # Function to approximate to 6 significant figures and handle NaN values
# def significant_figures(x):
#     if pd.isna(x) or x == 0:  # Check for NaN or zero
#         return np.nan if pd.isna(x) else 0
#     else:
#         return round(x, 6 - int(math.floor(math.log10(abs(x)))) - 1)

# # Function For Calculating Bollinger Bands with rounding to 6 significant figures
# def calculate_bollinger_bands(df, window=20, num_std_dev=0.975):
#     # Calculate the moving average (middle band) and round it to 6 significant figures
#     middle_band_calc = df['close'].rolling(window=window, min_periods=1).mean()
#     middleband = middle_band_calc.apply(significant_figures)

#     # Calculate the standard deviation and use it to derive the upper and lower bands
#     std_dev = df['close'].rolling(window=window, min_periods=1).std()

#     # Calculate the upper and lower bands and round them to 6 significant figures
#     upperband = (middleband + (std_dev * num_std_dev)).apply(significant_figures)
#     lowerband = (middleband - (std_dev * num_std_dev)) .apply(significant_figures)

#     return upperband, middleband, lowerband

# # Fetching OHLCV data
# df = fetch_OHLCV('1000PEPE/USDT:USDT', '5m')

# # Calculating Bollinger Bands with rounding
# upperband, middleband, lowerband = calculate_bollinger_bands(df)

# # Closing Prices of candles
# last_close = df['close'].iloc[-2]       # Last candle close
# second_last_close = df['close'].iloc[-3] # Second to last candle close
# third_last_close = df['close'].iloc[-4] # third to last candle close

# # Print Bollinger Band results for the last few candles
# print('upperband[498] =', upperband.iloc[-2])
# print('upperband[497] =', upperband.iloc[-3])
# print('upperband[496] =', upperband.iloc[-4])
# print('middleband[498] =', middleband.iloc[-2])
# print('middleband[497] =', middleband.iloc[-3])
# print('middleband[496] =', middleband.iloc[-4])
# print('lowerband[498] =', lowerband.iloc[-2])
# print('lowerband[497] =', lowerband.iloc[-3])
# print('lowerband[496] =', lowerband.iloc[-4])
# print('last_close, second_last_close, third_last_close =', last_close, second_last_close, third_last_close)

#Fetching USDT Balance
usdt_balance = binance_futures.fetch_balance()['total']['USDT']
print(usdt_balance)

#Checking positions and orders
positions = binance_futures.fetch_positions_risk()
orders = binance_futures.fetch_closed_orders('1000PEPE/USDT:USDT')
current_price = binance_futures.fetch_ticker('1000PEPE/USDT:USDT')['last']
print(orders)

for position in positions:
    print(position['side'])