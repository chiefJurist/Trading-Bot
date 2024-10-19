import ccxt
import pandas as pd
import talib as ta
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
    bars = binance_spot.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

#Function For Calculating Indicators
def calculate_indicators(df, window=20, num_std_dev=1.0):
    #Stochastic Oscillator
    rsi = ta.RSI(df['close'].values, timeperiod=14)
    k, d = ta.STOCH(rsi, rsi, rsi, 
                    fastk_period=14, 
                    slowk_period=3, 
                    slowk_matype=0, 
                    slowd_period=3, 
                    slowd_matype=0)
    return k, d
    
    #Bollinger Bands
    
def calculate_bollinger_bands(df, window=20, num_std_dev=1.0):
        # Calculating the moving average (middle band)
        middle_band = df['close'].rolling(window=window).mean()

        # Calculating the standard deviation
        std_dev = df['close'].rolling(window=window).std()

        # Calculating the upper and lower bands
        upper_band = middle_band + (std_dev * num_std_dev)
        lower_band = middle_band - (std_dev * num_std_dev)

        return upper_band, middle_band, lower_band

#Fetching OHLCV
df = fetch_OHLCV('PEPE/USDT', '5m')

#Calculating indicators
k, d = calculate_indicators(df)
upper_band, middle_band, lower_band =calculate_bollinger_bands(df) 

#Closing Prices of candles
last_close = df['close'].iloc[-2]       # Last candle close
second_last_close = df['close'].iloc[-3] # Second to last candle close
third_last_close = df['close'].iloc[-4] # third to last candle s

print('k[498 = ]' , k[498])
print('k[497 = ]' , k[497])
print('k[496 = ]' , k[496])
print('d[498 = ]' , d[498])
print('d[497 = ]' , d[497])
print('d[496 = ]' , d[496])
print('upperband[498 = ]' , upper_band[498])
print('upperband[497 = ]' , upper_band[497])
print('upperband[496 = ]' , upper_band[496])
print('middleband[498 = ]' ,middle_band[498])
print('middleband[497 = ]' ,middle_band[497])
print('middleband[496 = ]' ,middle_band[496])
print('lowerband[498 = ]' , lower_band[498])
print('lowerband[497 = ]' , lower_band[497])
print('lowerband[496 = ]' , lower_band[496])
print('last_close, second_last_close, third_last_close = ' , last_close, second_last_close, third_last_close)