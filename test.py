import ccxt
import pandas as pd
import talib as ta
import time
import math

# The User's API keys and addresses
SPOT_API_KEY = 'Io1hIHpNwK2PldQaV45ow3LlUbDW7CqzTnpiyWo3JSOQlm38RLKA0CfDQT0BuOhC'
SPOT_SECRET_KEY = '6bKn0jotdod18Y7fto7gDBVmO0zMMdR5OrhUpIy2f57qm7o4YE0AWAiQFLSa3GbW'
FUTURES_API_KEY = 'fvcNgcglEHAoouBoMn1s4NhlyK90CXs5wcjyi2HJm2fSIQpgCnpZHII6c295iUQM'
FUTURES_SECRET_KEY = 'nsjeRYY6nPxy1cfF07JNU8mhHnxwRB5FO8DHGtfZy9927u26ajnodnaSOLPvK5nV'

ADDRESS_ONE = '0x9D95d4751fCc02157d55527Ca4D50588bCC80590'
ADDRESS_TWO = '0x01460c011ca42552705a7c29a95bed64ffe45ea0'


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

# balance = binance_spot.fetch_balance()['total']['USDT']
# binance_spot.withdraw('USDT', balance, ADDRESS_TWO, tag=None, params={'network': 'BEP20'})


# # Close all positions
# positions = binance_futures.fetch_positions_risk()
# for position in positions:
#             if float(position['positionAmt']) != 0:
#                 side = 'sell' if float(position['positionAmt']) > 0 else 'buy'
#                 binance_futures.create_order(
#                     symbol=position['symbol'],
#                     type='market',
#                     side=side,
#                     amount=abs(float(position['positionAmt']))
#                 )


# #Checking sotchrsi
# symbol = 'ETH/USDT'
# timeframe = '5m'

# def fetch_OHLCV(symbol, timeframe, limit=500):
#     bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
#     df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
#     df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
#     return df

# def calculate_stoch_rsi(df):
#     stoch_rsi_k, stoch_rsi_d = ta.STOCHRSI(df['close'], timeperiod=14)
#     return stoch_rsi_k, stoch_rsi_d

# df = fetch_OHLCV(symbol, timeframe)
# stoch_rsi_k, stoch_rsi_d = calculate_stoch_rsi(df)

# print(stoch_rsi_d[499], 'Break', stoch_rsi_k[499])




#Setting Leverage and entering trade
balance = binance_spot.fetch_balance()['total']['USDT']
print(balance)

leverage = binance_futures.set_leverage(2, 'ETH/USDT:USDT')
print(leverage)
# current_price = binance_futures.fetch_ticker('ETH/USDT:USDT')['last']

# createOrder = binance_futures.create_market_buy_order("ETH/USDT:USDT", balance)

# print("leverage:", leverage, "current_price:", current_price,  "Order:", createOrder)