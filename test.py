import ccxt
import pandas as pd
import talib as ta
import time
import datetime

# The User's API keys and addresses
SPOT_API_KEY = 'FoQ10hJJ697zQQqU2rlWyXnODUaBud8pbe5CzxujtuAY6GnbxciJQaqX4gzVZlum'
SPOT_SECRET_KEY = 'xROpNPjxwW5XQwDUktGY3S0J4UZapyAPs67Kx4CsuLdNNI4cIeRqyWnxPLXe2PAC'
FUTURES_API_KEY = 'rhC7lpPd41Ll4nQNEpRPDkn9RhAsw1tslLQscgqA3GFRVkoeOl2Bl9x1hU2CR81e'
FUTURES_SECRET_KEY = 'tAj97Rs2MUiGp0KEOdR8MMlC8FCVotAsjNekVUcnyC85DPweReMZyLAzZxJK3fdk'
ADDRESS_ONE = '0x3d41cf8e4d3c32718920f35ef913aea04414ec9e'

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

#For Date
dt = '2024-08-06 01:00:00'

# Convert the datetime object to a timestamp
timestamp = dt.timestamp()


#Fetch OHLCV
def fetch_OHLCV(symbol, timeframe, limit=500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

#Calculate Indicators
def calculate_indicators(df,window=20, num_std_dev=2):
    #Stochastic Oscillator
    rsi = ta.RSI(df['close'].values, timeperiod=14)
    k, d = ta.STOCH(rsi, rsi, rsi, 
                    fastk_period=14, 
                    slowk_period=3, 
                    slowk_matype=0, 
                    slowd_period=3, 
                    slowd_matype=0)
    
    #Bollinger Bands
    rolling_mean = df['close'].rolling(window=window).mean()
    rolling_std = df['close'].rolling(window=window).std()
    upperband = rolling_mean + (rolling_std * num_std_dev)
    middleband = rolling_mean
    lowerband = rolling_mean - (rolling_std * num_std_dev)

    return k, d, upperband, middleband, lowerband

df = fetch_OHLCV('BTC/USDT:USDT', '1m')

#Calculating indicators
k, d, upperband, middleband, lowerband = calculate_indicators(df)

#Convert to dataframe for easy display
k_d = pd.DataFrame({'k': k, 'd': d})

# Set display options
pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', lambda x: '%.6f' % x)

print(k_d, dt, timestamp)