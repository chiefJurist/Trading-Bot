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

# Functions to approximate  significant figures and handle NaN values
def significant_figures_six(x):
    if pd.isna(x) or x == 0:  # Check for NaN or zero
        return np.nan if pd.isna(x) else 0
    else:
        return round(x, 6 - int(math.floor(math.log10(abs(x)))) - 1)
    
def significant_figures_four(x):
    if pd.isna(x) or x == 0:  # Check for NaN or zero
        return np.nan if pd.isna(x) else 0
    else:
        return round(x, 4 - int(math.floor(math.log10(abs(x)))) - 1)

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
    k = pd.Series(k).apply(significant_figures_four)
    d = pd.Series(d).apply(significant_figures_four)
    return k, d

#Function For Calculating Bollinger Bands
def calculate_bollinger(df, window, num_std_dev):
    # Calculate the moving average (middle band) and round it to 7 significant figures
    middle_band_calc = df['close'].rolling(window=window, min_periods=1).mean()
    middleband = middle_band_calc.apply(significant_figures_six)
    # Calculate the standard deviation and use it to derive the upper and lower bands
    std_dev = df['close'].rolling(window=window, min_periods=1).std()
    # Calculate the upper and lower bands and round them to 6 significant figures
    upperband = (middle_band_calc + (std_dev * num_std_dev)).apply(significant_figures_six)
    lowerband = (middle_band_calc - (std_dev * num_std_dev)).apply(significant_figures_six)
    
    return upperband, middleband, lowerband

#Fetching OHLCV
df = fetch_OHLCV('ETH/USDT:USDT', '1m')
big_df = fetch_OHLCV('ETH/USDT:USDT', '5m')

# #Calculating indicators
# k, d = calculate_stoch(df)
# big_k, big_d = calculate_stoch(big_df)
# upperband, middleband, lowerband = calculate_bollinger(df, 20, 0.975)
# big_upperband, big_middleband, big_lowerband = calculate_bollinger(big_df, 20, 1.95)


# #Prices at points of candles in 1m chart
# last_open = df['open'].iloc[-2]             # Last candle open for 1m
# last_high = df['high'].iloc[-2]             # Last candle high for 1m
# last_low = df['low'].iloc[-2]               # Last candle low for 1m
# last_close = df['close'].iloc[-2]           # Last candle close for 1m
# second_last_open = df['open'].iloc[-3]      # Second to the last candle open for 1m
# second_last_high = df['high'].iloc[-3]      # Second to the last candle high for 1m
# second_last_low = df['low'].iloc[-3]        # Second to the last candle low for 1m
# second_last_close = df['close'].iloc[-3]    # Second to the last candle close for 1m

# #Prices at points of candles in 5m chart
# big_last_open = big_df['open'].iloc[-2]             # Last candle open for 5m
# big_last_high = big_df['high'].iloc[-2]             # Last candle high for 5m
# big_last_low = big_df['low'].iloc[-2]               # Last candle low for 5m
# big_last_close = big_df['close'].iloc[-2]           # Last candle close for 5m
# second_big_last_open = big_df['open'].iloc[-3]      # Second to the last candle open for 5m
# second_big_last_high = big_df['high'].iloc[-3]      # Second to the last candle high for 5m
# second_big_last_low = big_df['low'].iloc[-3]        # Second to the last candle low for 5m
# second_big_last_close = big_df['close'].iloc[-3]    # Second to the last candle close for 5m
# third_big_last_open = big_df['open'].iloc[-4]       # Third to the last candle open for 5m
# third_big_last_high = big_df['high'].iloc[-4]       # Third to the last candle high for 5m
# third_big_last_low = big_df['low'].iloc[-4]         # Third to the last candle low for 5m
# third_big_last_close = big_df['close'].iloc[-4]     # Third to the last candle close for 5m
# fourth_big_last_open = big_df['open'].iloc[-5]      # Fourth to the last candle open for 5m
# fourth_big_last_high = big_df['high'].iloc[-5]      # Fourth to the last candle high for 5m
# fourth_big_last_low = big_df['low'].iloc[-5]        # Fourth to the last candle low for 5m
# fourth_big_last_close = big_df['close'].iloc[-5]    # Fourth to the last candle close for 5m
# fifth_big_last_open = big_df['open'].iloc[-6]       # Fifth to the last candle open for 5m
# fifth_big_last_high = big_df['high'].iloc[-6]       # Fifth to the last candle high for 5m
# fifth_big_last_low = big_df['low'].iloc[-6]         # Fifth to the last candle low for 5m
# fifth_big_last_close = big_df['close'].iloc[-6]     # Fifth to the last candle close for 5m


# # Print Candle points for 1m chart
# print("1m CHART")
# print('bollinger[498] for 1m chart = ', upperband[498], ",", middleband[498], ",", lowerband[498])
# print('bollinger[497] for 1m chart = ', upperband[497], ",", middleband[497], ",", lowerband[497])
# print('stochastic[498] for 1m chart = ', k[498], ",", d[498])
# print('stochastic[497] for 1m chart = ', k[497], ",", d[497])
# print('ohlcv[498] for 1m chart = ', last_open, ",", last_high, ",", last_low, ",", last_close)
# print('ohlcv[497] for 1m chart = ', second_last_open, ",", second_last_high, ",", second_last_low, ",", second_last_close)
# print('')
# print("5m CHART")
# print('bollinger[498] for 5m chart = ', big_upperband[498], ",", big_middleband[498], ",", big_lowerband[498])
# print('bollinger[497] for 5m chart = ', big_upperband[497], ",", big_middleband[497], ",", big_lowerband[497])
# print('bollinger[496] for 5m chart = ', big_upperband[496], ",", big_middleband[496], ",", big_lowerband[496])
# print('bollinger[495] for 5m chart = ', big_upperband[495], ",", big_middleband[495], ",", big_lowerband[495])
# print('bollinger[494] for 5m chart = ', big_upperband[494], ",", big_middleband[494], ",", big_lowerband[494])
# print('stochastic[498] for 5m chart = ', big_k[498], ",", big_d[498])
# print('stochastic[497] for 5m chart = ', big_k[497], ",", big_d[497])
# print('stochastic[496] for 5m chart = ', big_k[496], ",", big_d[496])
# print('stochastic[495] for 5m chart = ', big_k[495], ",", big_d[495])
# print('stochastic[494] for 5m chart = ', big_k[494], ",", big_d[494])
# print('ohlcv[498] for 5m chart = ', big_last_open, ",", big_last_high, ",", big_last_low, ",", big_last_close)
# print('ohlcv[497] for 5m chart = ', second_big_last_open, ",", second_big_last_high, ",", second_big_last_low, ",", second_big_last_close)
# print('ohlcv[496] for 5m chart = ', third_big_last_open, ",", third_big_last_high, ",", third_big_last_low, ",", third_big_last_close)
# print('ohlcv[495] for 5m chart = ', fourth_big_last_open, ",", fourth_big_last_high, ",", fourth_big_last_low, ",", fourth_big_last_close)
# print('ohlcv[494] for 5m chart = ', fifth_big_last_open, ",", fifth_big_last_high, ",", fifth_big_last_low, ",", fifth_big_last_close)
# print("Bollinger[498] diff for 5m =", big_upperband[498] - big_lowerband[498])
# print("Candle diff and bollinger[498] lowerband for 5m =", big_last_low - big_lowerband[498])
# print("Bollinger[498] upperband and candle diff for 5m =", big_upperband[498] - big_last_high)


#Setting leverage
binance_futures.set_leverage(5, 'ETH/USDT:USDT')

#Fetching USDT Balance
usdt_balance = binance_futures.fetch_balance()['total']['USDT']

current_price = binance_futures.fetch_ticker('ETH/USDT:USDT')['last'] #fetching the current price

try:
    amount = usdt_balance * 2.5 / current_price #using half the capital
    binance_futures.create_order(
        symbol="ETH/USDT:USDT",  # Symbol for the asset
        side="BUY",                     # Buy to open a long position
        type="MARKET",                  # Market order
        amount=amount,                  # Amount of asset to buy
        params={"positionSide": "LONG"} # Specify "LONG" since you're in Hedge Mode
    )
    print("long position created successfully")
except Exception as e:
    print(f"Error in opening long positions when no position is opened : {e}")
# Closing the position
try:
    open_price = binance_futures.fetch_closed_orders('ETH/USDT:USDT')[-1]['average']
    target_price = open_price + (open_price * 0.01)
    stop_loss_price = open_price - (open_price * 0.001)  # Stop-Loss price
    close_amount = float(amount)
    # A take-profit order
    binance_futures.create_order(
        symbol='ETH/USDT:USDT',  # Symbol for the asset
        side='SELL',                  # Sell to close the long position
        type='LIMIT',                 # Limit order
        amount=close_amount,          # Amount to sell
        price=target_price,           # Target price for the limit order
        params = {
            "positionSide": "LONG",  # Specify "LONG" to close the long position
            "timeInForce": "GTC"     # Good 'til canceled; adjust as necessary
        }
    )
    print("take-profit order for long position created successfully")
    # A stop-loss order
    binance_futures.create_order(
        symbol='ETH/USDT:USDT',  # Symbol for the asset
        side='SELL',            # Sell to close the long position
        type='STOP_MARKET',     # Stop market order
        amount=close_amount,    # Amount to sell
        params={
            "positionSide": "LONG",  # Specify "LONG" to close the long position
            "stopPrice": stop_loss_price,  # Stop price for the order
        }
    )
    print("stop-loss order for long position created successfully")
except Exception as e:
    print(f"Error in creating close order for long positions when no position is opened : {e}")


#Fetching USDT Balance
free_usdt = binance_futures.fetch_balance()['free']['USDT']

#Short position
try:
    amount = free_usdt * 5 / current_price #using half of the capital
    binance_futures.create_order(
        symbol='ETH/USDT:USDT',  # Symbol for the asset
        side='SELL',                        # Sell to open a short position
        type='MARKET',                      # Market order
        amount=amount,                      # Amount to sell
        params={"positionSide": "SHORT"}    # Specify "SHORT" to open the short position
    )
    print("short position created successfully")
except Exception as e:
    print(f"Error in opening short positions when no position is opened : {e}")
# Closing the position
try:
    open_price = binance_futures.fetch_closed_orders('ETH/USDT:USDT')[-1]['average']
    target_price = open_price - (open_price * 0.01)
    stop_loss_price = open_price + (open_price * 0.001)  # Stop-Loss price
    close_amount = float(amount)
    # A take-profit order
    binance_futures.create_order(
        symbol='ETH/USDT:USDT',      # Symbol for the asset
        side='BUY',                   # Buy to close the short position
        type='LIMIT',                 # Limit order
        amount=close_amount,          # Amount to buy
        price=target_price,           # Target price for the limit order
        params = {
            "positionSide": "SHORT",  # Specify "SHORT" to close the short position
            "timeInForce": "GTC"      # Good 'til canceled; adjust as necessary
        }
    )
    print("take-profit order for short position created successfully")
    # A stoploss order
    binance_futures.create_order(
        symbol='ETH/USDT:USDT',  # Symbol for the asset
        side='BUY',             # Buy to close the short position
        type='STOP_MARKET',     # Stop market order
        amount=close_amount,    # Amount to buy
        params={
            "positionSide": "SHORT",  # Specify "SHORT" to close the short position
            "stopPrice": stop_loss_price,  # Stop price for the order
        }
    )
    print("stop-loss order for short position created successfully")
except Exception as e:
    print(f"Error in creating close order for short positions when no position is opened : {e}")