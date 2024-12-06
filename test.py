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

# Function to approximate to 6 significant figures and handle NaN values
def significant_figures(x):
    if pd.isna(x) or x == 0:  # Check for NaN or zero
        return np.nan if pd.isna(x) else 0
    else:
        return round(x, 6 - int(math.floor(math.log10(abs(x)))) - 1)

#Function For Calculating STOCHF
def calculate_stoch(df):
    #Stochastic Oscillator
    rsi = ta.RSI(df['close'].values, timeperiod=14)
    k, d = ta.STOCH(rsi, rsi, rsi, 
                    fastk_period=14, 
                    slowk_period=3, 
                    slowk_matype=0, 
                    slowd_period=3, 
                    slowd_matype=0)
    return k, d

#Function For Calculating Bollinger Bands
def calculate_bollinger(df, window, num_std_dev):
    # Calculate the moving average (middle band) and round it to 7 significant figures
    middle_band_calc = df['close'].rolling(window=window, min_periods=1).mean()
    middleband = middle_band_calc
    # Calculate the standard deviation and use it to derive the upper and lower bands
    std_dev = df['close'].rolling(window=window, min_periods=1).std()
    # Calculate the upper and lower bands and round them to 6 significant figures
    upperband = (middle_band_calc + (std_dev * num_std_dev))
    lowerband = (middle_band_calc - (std_dev * num_std_dev)) 
    
    return upperband, middleband, lowerband

#Fetching OHLCV
df = fetch_OHLCV('ETH/USDT:USDT', '1m')
big_df = fetch_OHLCV('ETH/USDT:USDT', '5m')

#Calculating indicators
k, d = calculate_stoch(df)
big_k, big_d = calculate_stoch(big_df)
upperband, middleband, lowerband = calculate_bollinger(df, 20, 0.975)
big_upperband, big_middleband, big_lowerband = calculate_bollinger(big_df, 20, 1.95)


#Prices at points of candles in 1m chart
last_open = df['open'].iloc[-2]             # Last candle open for 1m
last_high = df['high'].iloc[-2]             # Last candle high for 1m
last_low = df['low'].iloc[-2]               # Last candle low for 1m
last_close = df['close'].iloc[-2]           # Last candle close for 1m
second_last_open = df['open'].iloc[-3]      # Second to the last candle open for 1m
second_last_high = df['high'].iloc[-3]      # Second to the last candle high for 1m
second_last_low = df['low'].iloc[-3]        # Second to the last candle low for 1m
second_last_close = df['close'].iloc[-3]    # Second to the last candle close for 1m

#Prices at points of candles in 5m chart
big_last_open = big_df['open'].iloc[-2]             # Last candle open for 5m
big_last_high = big_df['high'].iloc[-2]             # Last candle high for 5m
big_last_low = big_df['low'].iloc[-2]               # Last candle low for 5m
big_last_close = big_df['close'].iloc[-2]           # Last candle close for 5m
second_big_last_open = big_df['open'].iloc[-3]      # Second to the last candle open for 5m
second_big_last_high = big_df['high'].iloc[-3]      # Second to the last candle high for 5m
second_big_last_low = big_df['low'].iloc[-3]        # Second to the last candle low for 5m
second_big_last_close = big_df['close'].iloc[-3]    # Second to the last candle close for 5m
third_big_last_open = big_df['open'].iloc[-4]       # Third to the last candle open for 5m
third_big_last_high = big_df['high'].iloc[-4]       # Third to the last candle high for 5m
third_big_last_low = big_df['low'].iloc[-4]         # Third to the last candle low for 5m
third_big_last_close = big_df['close'].iloc[-4]     # Third to the last candle close for 5m
fourth_big_last_open = big_df['open'].iloc[-5]      # Fourth to the last candle open for 5m
fourth_big_last_high = big_df['high'].iloc[-5]      # Fourth to the last candle high for 5m
fourth_big_last_low = big_df['low'].iloc[-5]        # Fourth to the last candle low for 5m
fourth_big_last_close = big_df['close'].iloc[-5]    # Fourth to the last candle close for 5m
fifth_big_last_open = big_df['open'].iloc[-6]       # Fifth to the last candle open for 5m
fifth_big_last_high = big_df['high'].iloc[-6]       # Fifth to the last candle high for 5m
fifth_big_last_low = big_df['low'].iloc[-6]         # Fifth to the last candle low for 5m
fifth_big_last_close = big_df['close'].iloc[-6]     # Fifth to the last candle close for 5m


# Print Candle points for 1m chart
print("1m CHART")
print('bollinger[498] for 1m chart = ', upperband[498], ",", middleband[498], ",", lowerband[498])
print('bollinger[497] for 1m chart = ', upperband[497], ",", middleband[497], ",", lowerband[497])
print('stochastic[498] for 1m chart = ', k[498], ",", d[498])
print('stochastic[497] for 1m chart = ', k[497], ",", d[497])
print('ohlcv[498] for 1m chart = ', last_open, ",", last_high, ",", last_low, ",", last_close)
print('ohlcv[497] for 1m chart = ', second_last_open, ",", second_last_high, ",", second_last_low, ",", second_last_close)
print('')
print("5m CHART")
print('bollinger[498] for 5m chart = ', big_upperband[498], ",", big_middleband[498], ",", big_lowerband[498])
print('bollinger[497] for 5m chart = ', big_upperband[497], ",", big_middleband[497], ",", big_lowerband[497])
print('bollinger[496] for 5m chart = ', big_upperband[496], ",", big_middleband[496], ",", big_lowerband[496])
print('bollinger[495] for 5m chart = ', big_upperband[495], ",", big_middleband[495], ",", big_lowerband[495])
print('bollinger[494] for 5m chart = ', big_upperband[494], ",", big_middleband[494], ",", big_lowerband[494])
print('stochastic[498] for 5m chart = ', big_k[498], ",", big_d[498])
print('stochastic[497] for 5m chart = ', big_k[497], ",", big_d[497])
print('stochastic[496] for 5m chart = ', big_k[496], ",", big_d[496])
print('stochastic[495] for 5m chart = ', big_k[495], ",", big_d[495])
print('stochastic[494] for 5m chart = ', big_k[494], ",", big_d[494])
print('ohlcv[498] for 5m chart = ', big_last_open, ",", big_last_high, ",", big_last_low, ",", big_last_close)
print('ohlcv[497] for 5m chart = ', second_big_last_open, ",", second_big_last_high, ",", second_big_last_low, ",", second_big_last_close)
print('ohlcv[496] for 5m chart = ', third_big_last_open, ",", third_big_last_high, ",", third_big_last_low, ",", third_big_last_close)
print('ohlcv[495] for 5m chart = ', fourth_big_last_open, ",", fourth_big_last_high, ",", fourth_big_last_low, ",", fourth_big_last_close)
print('ohlcv[494] for 5m chart = ', fifth_big_last_open, ",", fifth_big_last_high, ",", fifth_big_last_low, ",", fifth_big_last_close)