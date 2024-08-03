import ccxt
import pandas as pd
import talib as ta
import time

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

binance_futures.set_leverage(3, 'SOL/USDT:USDT')
current_price = binance_futures.fetch_ticker('SOL/USDT:USDT')['last']
usdt_balance = binance_futures.fetch_balance()['total']['USDT']
amount = usdt_balance * 3 / current_price
binance_futures.create_market_buy_order("SOL/USDT:USDT", amount)
