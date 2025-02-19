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

# #Setting leverage
# binance_futures.set_leverage(20, 'ETH/USDT:USDT')

# #Fetching USDT Balance
# free_usdt_balance = binance_futures.fetch_balance()['free']['USDT']

# #Getting the current price of the asset
# current_price = binance_futures.fetch_ticker('ETH/USDT:USDT')['last']

# #Opening long position
# try:
#     amount = free_usdt_balance * 19.6 / current_price #using the half capital
#     long_position = binance_futures.create_order(
#         symbol="ETH/USDT:USDT",  # Symbol for the asset
#         side="BUY",                     # Buy to open a long position
#         type="MARKET",                  # Market order
#         amount=amount,                  # Amount of asset to buy
#         params={"positionSide": "LONG"} # Specify "LONG" since you're in Hedge Mode
#     )
#     print("Successfully opened long position")
# except Exception as e:
#     print(f"Error in opening long positions : {e}")
# # Closing the position
# try:
#     open_price = binance_futures.fetch_closed_orders('ETH/USDT:USDT')[-1]['average']
#     target_price = open_price + (open_price * 0.015)
#     stop_loss_price = open_price - (open_price * 0.0025)  # Stop-Loss price
#     close_amount = float(amount)
#     # A take-profit order
#     long_take_profit = binance_futures.create_order(
#         symbol='ETH/USDT:USDT',  # Symbol for the asset
#         side='SELL',                  # Sell to close the long position
#         type='LIMIT',                 # Limit order
#         amount=close_amount,          # Amount to sell
#         price=target_price,           # Target price for the limit order
#         params = {
#             "positionSide": "LONG",  # Specify "LONG" to close the long position
#             "timeInForce": "GTC"     # Good 'til canceled; adjust as necessary
#         }
#     )
#     print("successfully created close order for long position")
#     # A stop-loss order
#     long_stoploss = binance_futures.create_order(
#         symbol='ETH/USDT:USDT',  # Symbol for the asset
#         side='SELL',            # Sell to close the long position
#         type='STOP_MARKET',     # Stop market order
#         amount=close_amount,    # Amount to sell
#         params={
#             "positionSide": "LONG",  # Specify "LONG" to close the long position
#             "stopPrice": stop_loss_price,  # Stop price for the order
#         }
#     )
#     print("successfully created stoploss order for long position")
# except Exception as e:
#     print(f"Error in creating close order or stoploss order for long positions when no position is opened : {e}")

# #Opening short position
# try:
#     amount = free_usdt_balance * 10 / current_price #using the entire capital
#     short_position = binance_futures.create_order(
#         symbol='ETH/USDT:USDT',  # Symbol for the asset
#         side='SELL',                        # Sell to open a short position
#         type='MARKET',                      # Market order
#         amount=amount,                      # Amount to sell
#         params={"positionSide": "SHORT"}    # Specify "SHORT" to open the short position
#     )
#     print("Successfully opened short position")
# except Exception as e:
#     print(f"Error in opening short positions when no position is opened : {e}")
# # Closing the position
# try:
#     open_price = binance_futures.fetch_closed_orders('ETH/USDT:USDT')[-1]['average']
#     target_price = open_price - (open_price * 0.015)
#     stop_loss_price = open_price + (open_price * 0.0025)  # Stop-Loss price
#     close_amount = float(amount)
#     # A take-profit order
#     short_take_profit = binance_futures.create_order(
#         symbol='ETH/USDT:USDT',      # Symbol for the asset
#         side='BUY',                   # Buy to close the short position
#         type='LIMIT',                 # Limit order
#         amount=close_amount,          # Amount to buy
#         price=target_price,           # Target price for the limit order
#         params = {
#             "positionSide": "SHORT",  # Specify "SHORT" to close the short position
#             "timeInForce": "GTC"      # Good 'til canceled; adjust as necessary
#         }
#     )
#     print("successfully created close order for short position")
#     # A stoploss order
#     short_stoploss = binance_futures.create_order(
#         symbol='ETH/USDT:USDT',  # Symbol for the asset
#         side='BUY',             # Buy to close the short position
#         type='STOP_MARKET',     # Stop market order
#         amount=close_amount,    # Amount to buy
#         params={
#             "positionSide": "SHORT",  # Specify "SHORT" to close the short position
#             "stopPrice": stop_loss_price,  # Stop price for the order
#         }
#     )
#     print("successfully created stoploss order for short position")
# except Exception as e:
#     print(f"Error in creating close order for short positions when no position is opened : {e}")

# print("Long Position: ")
# print(long_position)
# print("")
# print("Long Position Take Profit Order: ")
# print(long_take_profit)
# print("")
# print("Long Position Stoploss Order: ")
# print(long_stoploss)
# print("")
# print("Short Position: ")
# print(short_position)
# print("")
# print("Short Position Take Profit Order: ")
# print(short_take_profit)
# print("")
# print("Short Position Stoploss Order: ")
# print(short_stoploss)
# print("")


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

# Calculate Bollinger Bands for 1m chart
df['upperband'], df['middleband'], df['lowerband'] = calculate_bollinger_bands(df['close'])

#Points in The Chart
print("last open : ", last_open = df['open'].iloc[-2])                     #last candle open price
print("last close : ", last_close = df['close'].iloc[-2])                   #last candle close price
print("last upperband : ", last_upperband = df['upperband'].iloc[-2])           #last candle upperband
print("last lowerband : ", last_lowerband = df['lowerband'].iloc[-2])           #last candle lowerband
print("second to the last open : ", second_last_open = df['open'].iloc[-3])              #second to the last candle open price
print("second to the last close : ", second_last_close = df['close'].iloc[-3])            #second to the last candle close price
print("second to the last upperband : ", second_last_upperband = df['upperband'].iloc[-3])    #second to the last candle upperband
print("second to the last lowerband : ", second_last_lowerband = df['lowerband'].iloc[-3])    #second to the last candle lowerband
print("third to the last open : ", third_last_open = df['open'].iloc[-4])               #third to the last candle open price
print("third to the last close : ", third_last_close = df['close'].iloc[-4])             #third to the last candle close price
print("third to the last upperband : ", third_last_upperband = df['upperband'].iloc[-4])     #third to the last candle upperband
print("third to the last lowerband : ", third_last_lowerband = df['lowerband'].iloc[-4])     #third to the last candle lowerband
print("fourth to the last open : ", fourth_last_open = df['open'].iloc[-5])              #fourth to the last candle open price
print("fourth to the last close : ", fourth_last_close = df['close'].iloc[-5])            #fourth to the last candle close price
print("fourth to the last upperband : ", fourth_last_upperband = df['upperband'].iloc[-5])    #fourth to the last candle upperband
print("fourth to the last lowerband : ", fourth_last_lowerband = df['lowerband'].iloc[-5])    #fourth to the last candle lowerband
print("last big open : ", last_big_open = df2['open'].iloc[-2])                #last candle open price on the 1 day chart
print("last big close : ", last_big_close = df2['close'].iloc[-2])              #last candle close price on the 1 day chart
print("last big high : ", last_big_high = df2['high'].iloc[-2])                #last candle high price on the 1 day chart
print("last big low : ", last_big_low = df2['low'].iloc[-2])                  #last candle low price on the 1 day chart