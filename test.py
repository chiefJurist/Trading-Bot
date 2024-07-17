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

balance = binance_spot.fetch_balance()['total']['USDT']
binance_spot.withdraw('USDT', balance, ADDRESS_TWO, tag=None, params={'network': 'BEP20'})