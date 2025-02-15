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
def fetch_OHLCV(symbol, timeframe, limit=500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

#Function For Calculating Bollinger Bands
def calculate_bollinger_bands(close_prices, timeperiod=20, nbdevup=1, nbdevdn=1):
    upperband, middleband, lowerband = ta.BBANDS(
        close_prices, timeperiod=timeperiod, nbdevup=nbdevup, nbdevdn=nbdevdn, matype=0
    )
    return upperband, middleband, lowerband


#Fetching OHLCV
df = fetch_OHLCV('ETH/USDT:USDT', '1m')
df2 = fetch_OHLCV('ETH/USDT:USDT', '1d')

# Calculate Bollinger Bands for both timeframes
df['upperband'], df['middleband'], df['lowerband'] = calculate_bollinger_bands(df['close'])
df2['upperband'], df2['middleband'], df2['lowerband'] = calculate_bollinger_bands(df2['close'])

print("last_open: ", df['open'].iloc[-2])
print("")
print("last_close: ", df['close'].iloc[-2])
print("")
print("last_upperband: ", df['upperband'].iloc[-2])
print("")
print("last_lowerband: ", df['lowerband'].iloc[-2])
print("")
print("second_last_open: ", df['open'].iloc[-3])
print("")
print("second_last_close: ", df['close'].iloc[-3])
print("")
print("second_last_upperband: ", df['upperband'].iloc[-3])
print("")
print("second_last_lowerband: ", df['lowerband'].iloc[-3])
print("")
print("third_last_open: ", df['open'].iloc[-4])
print("")
print("third_last_close: ", df['close'].iloc[-4])
print("")
print("third_last_upperband: ", df['upperband'].iloc[-4])
print("")
print("third_last_lowerband: ", df['lowerband'].iloc[-4])
print("")
print("fourth_last_open: ", df['open'].iloc[-5])
print("")
print("fourth_last_close: ", df['close'].iloc[-5])
print("")
print("fourth_last_upperband: ", df['upperband'].iloc[-5])
print("")
print("fourth_last_lowerband: ", df['lowerband'].iloc[-5])
print("")
print("last_big_open: ", df2['open'].iloc[-2])
print("")
print("last_big_close: ", df2['close'].iloc[-2])
print("")
print("last_big_high: ", df2['high'].iloc[-2])
print("")
print("last_big_low: ", df2['low'].iloc[-2])
print("")
print("last_big_upperband: ", df2['upperband'].iloc[-2])
print("")
print("last_big_lowerband: ", df2['lowerband'].iloc[-2])
print("")