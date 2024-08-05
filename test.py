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

# binance_futures.set_leverage(10, 'SOL/USDT:USDT')
# current_price = binance_futures.fetch_ticker('SOL/USDT:USDT')['last']
# usdt_balance = binance_futures.fetch_balance()['total']['USDT']
# amount = usdt_balance * 10 / current_price
# binance_futures.create_market_buy_order("SOL/USDT:USDT", amount)

# time.sleep(5)

# recent_order = binance_futures.fetch_closed_orders('SOL/USDT:USDT')[-1]
# open_price = float(recent_order['info']['avgPrice'])
# target_price = open_price + (open_price * 0.0055)
# close_amount = float(amount)
# binance_futures.create_limit_sell_order('SOL/USDT:USDT', close_amount, target_price)
# time.sleep(5)  # add a break for safety


# positions = binance_futures.fetch_positions_risk()
# orders = binance_futures.fetch_open_orders('SOL/USDT:USDT')

# for position in positions:
#     close_amount = abs(float(position['info']['positionAmt']))

#     # Cancel all open orders before creating the new market order
#     for order in orders:
#         binance_futures.cancel_order(order['id'], 'SOL/USDT:USDT')
#         time.sleep(5)  # add a break for safety

#     binance_futures.create_market_sell_order('SOL/USDT:USDT', close_amount)


# Define the parameters
symbol = 'BTC/USDT'  # The trading pair
timeframe = '1m'  # The desired timeframe
specific_time = '2024-08-05 17:51:00'  # The specific start time
end_time = '2024-08-05 17:51:59'  # The specific end time

# Convert the specific time to timestamps in milliseconds
since_timestamp = int(datetime.datetime.strptime(specific_time, '%Y-%m-%d %H:%M:%S').timestamp() * 1000)
end_timestamp = int(datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S').timestamp() * 1000)

# Fetch OHLCV data for a period before and including the specific minute
ohlcv = binance_futures.fetch_ohlcv(symbol, timeframe, since=since_timestamp - 15 * 60 * 1000, limit=1000)

# Convert the data to a pandas DataFrame
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

# Convert timestamp to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

# Calculate the Stochastic Oscillator
def calculate_stoch(df, k_period=14, d_period=3):
    df['low_min'] = df['low'].rolling(window=k_period).min()
    df['high_max'] = df['high'].rolling(window=k_period).max()
    df['%K'] = 100 * ((df['close'] - df['low_min']) / (df['high_max'] - df['low_min']))
    df['%D'] = df['%K'].rolling(window=d_period).mean()
    return df

# Apply the calculation to the dataframe
stoch_df = calculate_stoch(df)

# Filter the DataFrame for the desired range
stoch_df = stoch_df[(stoch_df['timestamp'] >= specific_time) & (stoch_df['timestamp'] <= end_time)]

# Set pandas to display all rows
pd.set_option('display.max_rows', None)

# Display the Stochastic Oscillator values
print(stoch_df[['%K', '%D']])