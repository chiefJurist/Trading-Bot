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

#Setting leverage
binance_futures.set_leverage(10, 'ETH/USDT:USDT')

#Fetching USDT Balance
free_usdt_balance = binance_futures.fetch_balance()['free']['USDT']

#Getting the current price of the asset
current_price = binance_futures.fetch_ticker('ETH/USDT:USDT')['last']

#Opening long position
try:
    amount = free_usdt_balance * 5 / current_price #using the half capital
    long_position = binance_futures.create_order(
        symbol="ETH/USDT:USDT",  # Symbol for the asset
        side="BUY",                     # Buy to open a long position
        type="MARKET",                  # Market order
        amount=amount,                  # Amount of asset to buy
        params={"positionSide": "LONG"} # Specify "LONG" since you're in Hedge Mode
    )
    print("Successfully opened long position")
except Exception as e:
    print(f"Error in opening long positions : {e}")
# Closing the position
try:
    open_price = binance_futures.fetch_closed_orders('ETH/USDT:USDT')[-1]['average']
    target_price = open_price + (open_price * 0.015)
    stop_loss_price = open_price - (open_price * 0.0025)  # Stop-Loss price
    close_amount = float(amount)
    # A take-profit order
    long_take_profit = binance_futures.create_order(
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
    print("successfully created close order for long position")
    # A stop-loss order
    long_stoploss = binance_futures.create_order(
        symbol='ETH/USDT:USDT',  # Symbol for the asset
        side='SELL',            # Sell to close the long position
        type='STOP_MARKET',     # Stop market order
        amount=close_amount,    # Amount to sell
        params={
            "positionSide": "LONG",  # Specify "LONG" to close the long position
            "stopPrice": stop_loss_price,  # Stop price for the order
        }
    )
    print("successfully created stoploss order for long position")
except Exception as e:
    print(f"Error in creating close order or stoploss order for long positions when no position is opened : {e}")

#Opening short position
try:
    amount = free_usdt_balance * 10 / current_price #using the entire capital
    short_position = binance_futures.create_order(
        symbol='ETH/USDT:USDT',  # Symbol for the asset
        side='SELL',                        # Sell to open a short position
        type='MARKET',                      # Market order
        amount=amount,                      # Amount to sell
        params={"positionSide": "SHORT"}    # Specify "SHORT" to open the short position
    )
    print("Successfully opened short position")
except Exception as e:
    print(f"Error in opening short positions when no position is opened : {e}")
# Closing the position
try:
    open_price = binance_futures.fetch_closed_orders('ETH/USDT:USDT')[-1]['average']
    target_price = open_price - (open_price * 0.015)
    stop_loss_price = open_price + (open_price * 0.0025)  # Stop-Loss price
    close_amount = float(amount)
    # A take-profit order
    short_take_profit = binance_futures.create_order(
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
    print("successfully created close order for short position")
    # A stoploss order
    short_stoploss = binance_futures.create_order(
        symbol='ETH/USDT:USDT',  # Symbol for the asset
        side='BUY',             # Buy to close the short position
        type='STOP_MARKET',     # Stop market order
        amount=close_amount,    # Amount to buy
        params={
            "positionSide": "SHORT",  # Specify "SHORT" to close the short position
            "stopPrice": stop_loss_price,  # Stop price for the order
        }
    )
    print("successfully created stoploss order for short position")
except Exception as e:
    print(f"Error in creating close order for short positions when no position is opened : {e}")

print("Long Position: ")
print(long_position)
print("")
print("Long Position Take Profit Order: ")
print(long_take_profit)
print("")
print("Long Position Stoploss Order: ")
print(long_stoploss)
print("")
print("Short Position: ")
print(short_position)
print("")
print("Short Position Take Profit Order: ")
print(short_take_profit)
print("")
print("Short Position Stoploss Order: ")
print(short_stoploss)
print("")