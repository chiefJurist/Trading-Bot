import ccxt
import talib
import numpy as np
import pandas as pd
import time

# Replace with your own Binance API key and secret
api_key = 'your_api_key'
api_secret = 'your_api_secret'

# Initialize Binance futures client
binance = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
    },
})

# Constants
symbol = '1000PEPE/USDT'
timeframe = '1h'  # You can change the timeframe as needed
bollinger_window = 20
bollinger_nbdevup = 2
bollinger_nbdevdn = 2
stochastic_k = 14
stochastic_d = 3

# Fetch OHLCV data
def fetch_ohlcv(symbol, timeframe):
    ohlcv = binance.fetch_ohlcv(symbol, timeframe)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Calculate Bollinger Bands and Stochastic Oscillator
def calculate_indicators(df):
    df['upper_band'], df['middle_band'], df['lower_band'] = talib.BBANDS(
        df['close'], timeperiod=bollinger_window, nbdevup=bollinger_nbdevup, nbdevdn=bollinger_nbdevdn
    )
    df['slowk'], df['slowd'] = talib.STOCH(
        df['high'], df['low'], df['close'],
        fastk_period=stochastic_k, slowk_period=stochastic_d, slowk_matype=0,
        slowd_period=stochastic_d, slowd_matype=0
    )
    return df

# Place a market order
def create_market_order(symbol, side, amount):
    order = binance.create_order(symbol, 'market', side, amount)
    return order

# Place a limit order
def create_limit_order(symbol, side, amount, price):
    order = binance.create_order(symbol, 'limit', side, amount, price)
    return order

# Main function to run the strategy
def run_strategy():
    df = fetch_ohlcv(symbol, timeframe)
    df = calculate_indicators(df)

    # Check for trading signals
    last_row = df.iloc[-1]
    previous_row = df.iloc[-2]

    leverage = 10
    profit_target = 0.0055

    if (
        previous_row['slowk'] < previous_row['slowd'] and
        last_row['slowk'] > last_row['slowd'] and
        last_row['slowk'] < last_row['middle_band'] and
        last_row['slowk'] > last_row['lower_band']
    ):
        # Golden cross below the middle band and near the lower band
        print("Golden cross detected: Placing long order")
        amount = 10  # Define the amount you want to trade
        order = create_market_order(symbol, 'buy', amount)
        open_price = float(order['price'])
        close_price = open_price * (1 + profit_target)
        create_limit_order(symbol, 'sell', amount, close_price)
        print(f"Long position opened at {open_price}, limit sell order placed at {close_price}")

    elif (
        previous_row['slowk'] > previous_row['slowd'] and
        last_row['slowk'] < last_row['slowd'] and
        last_row['slowk'] > last_row['middle_band'] and
        last_row['slowk'] < last_row['upper_band']
    ):
        # Death cross above the middle band and near the upper band
        print("Death cross detected: Placing short order")
        amount = 10  # Define the amount you want to trade
        order = create_market_order(symbol, 'sell', amount)
        open_price = float(order['price'])
        close_price = open_price * (1 - profit_target)
        create_limit_order(symbol, 'buy', amount, close_price)
        print(f"Short position opened at {open_price}, limit buy order placed at {close_price}")

# Run the strategy in a loop
while True:
    try:
        run_strategy()
        time.sleep(60 * 60)  # Run the strategy every hour
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(60)
