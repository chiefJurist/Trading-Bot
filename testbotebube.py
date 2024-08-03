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

# Function For Transfer Of The Capital To The Futures Account
def initial_transfer():
    balance = binance_spot.fetch_balance()['total']['USDT']
    if balance > 0:
        binance_spot.sapi_post_futures_transfer({
            'asset': 'USDT',
            'amount': 20,
            'type': 1  # Type 1 means transfer from spot to futures
        })

# Function For Withdrawal of The Profit Transferred to Spot Account
def check_and_withdraw_spot_balance():
    usdt_profit_balance = binance_spot.fetch_balance()['total']['USDT']
    if usdt_profit_balance > 500:
        binance_spot.withdraw('USDT', usdt_profit_balance, ADDRESS_ONE, tag=None, params={'network': 'BEP20'})
        time.sleep(10)  # Sleep to ensure the withdrawals are processed

# Function For Fetching OHLCV
def fetch_OHLCV(symbol, timeframe, limit=500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Function For Calculating Indicators
def calculate_indicators(df, window=20, num_std_dev=2):
    # Stochastic Oscillator
    rsi = ta.RSI(df['close'].values, timeperiod=14)
    k, d = ta.STOCH(rsi, rsi, rsi, 
                    fastk_period=14, 
                    slowk_period=3, 
                    slowk_matype=0, 
                    slowd_period=3, 
                    slowd_matype=0)
    
    # Bollinger Bands
    rolling_mean = df['close'].rolling(window=window).mean()
    rolling_std = df['close'].rolling(window=window).std()
    upperband = rolling_mean + (rolling_std * num_std_dev)
    middleband = rolling_mean
    lowerband = rolling_mean - (rolling_std * num_std_dev)

    return k, d, upperband, middleband, lowerband

# Manage Futures Position And Balance
def manage_futures_positions_and_balance():
    # Setting leverage
    binance_futures.set_leverage(10, '1000PEPE/USDT:USDT')

    # Fetching USDT Balance
    usdt_balance = binance_futures.fetch_balance()['total']['USDT']

    # Fetching OHLCV
    df = fetch_OHLCV('1000PEPE/USDT', '5m')

    # Calculating indicators
    k, d, upperband, middleband, lowerband = calculate_indicators(df)

    # Checking positions and orders
    positions = binance_futures.fetch_positions_risk()
    orders = binance_futures.fetch_open_orders('1000PEPE/USDT:USDT')
    current_price = binance_futures.fetch_ticker('1000PEPE/USDT:USDT')['last']

    # MAIN TRADING LOGIC
    if len(positions) == 0:
        # Creating order for a golden cross at a good BB
        if k[499] > (d[499] + 15) and current_price < middleband[499]:
            try:
                def retryFunc1():
                    current_price = binance_futures.fetch_ticker('1000PEPE/USDT:USDT')['last']
                    amount = usdt_balance * 10 / current_price
                    binance_futures.create_market_buy_order("1000PEPE/USDT:USDT", amount)
                    time.sleep(20)  # add a break for safety

                    # Taking profit order
                    recent_order = binance_futures.fetch_closed_orders('1000PEPE/USDT:USDT')[-1]
                    open_price = float(recent_order['info']['avgPrice'])
                    target_price = open_price + (open_price * 0.0055)
                    close_amount = float(amount)
                    binance_futures.create_limit_sell_order('1000PEPE/USDT:USDT', close_amount, target_price)
                    time.sleep(10)  # add a break for safety
                retryFunc1()
            except Exception as e:
                print(f"Error creating market buy or limit sell order: {e}")
                time.sleep(10)
                retryFunc1()

        # Creating order for a death cross at a good EMA
        elif (k[499] + 15) < d[499] and current_price > middleband[499]:
            try:
                def retryFunc2():
                    current_price = binance_futures.fetch_ticker('1000PEPE/USDT:USDT')['last']
                    amount = usdt_balance * 10 / current_price
                    binance_futures.create_market_sell_order("1000PEPE/USDT:USDT", amount)
                    time.sleep(10)  # add a break for safety

                    # Taking profit order
                    recent_order = binance_futures.fetch_closed_orders('1000PEPE/USDT:USDT')[-1]
                    open_price = float(recent_order['info']['avgPrice'])
                    target_price = open_price - (open_price * 0.0055)
                    close_amount = float(amount)
                    binance_futures.create_limit_buy_order('1000PEPE/USDT:USDT', close_amount, target_price)
                    time.sleep(10)  # add a break for safety
                retryFunc2()
            except Exception as e:
                print(f"Error creating market sell or limit buy order: {e}")
                time.sleep(10)
                retryFunc2()

    elif len(positions) > 0 and len(orders) == 0:
        # Taking Profit By Creating Order For Closing Positions
        for position in positions:
            if position['side'] == 'short':
                try:
                    def retryFunc3():
                        open_price = float(position['entryPrice'])
                        target_price = open_price - (open_price * 0.0055)
                        close_amount = abs(float(position['info']['positionAmt']))
                        binance_futures.create_limit_buy_order('1000PEPE/USDT:USDT', close_amount, target_price)
                        time.sleep(10)  # add a break for safety
                    retryFunc3()
                except Exception as e:
                    print(f"Error creating limit buy order for short position: {e}")
                    time.sleep(10)
                    retryFunc3()
            elif position['side'] == 'long':
                try:
                    def retryFunc4():
                        open_price = float(position['entryPrice'])
                        target_price = open_price + (open_price * 0.0055)
                        close_amount = abs(float(position['info']['positionAmt']))
                        binance_futures.create_limit_sell_order('1000PEPE/USDT:USDT', close_amount, target_price)
                        time.sleep(10)  # add a break for safety
                    retryFunc4()
                except Exception as e:
                    print(f"Error creating limit sell order for long position: {e}")
                    time.sleep(10)
                    retryFunc4()

    elif len(positions) > 0 and len(orders) > 0:
        for position in positions:
            # Exiting Before A Major Loss
            if position['side'] == 'short':
                if k[499] > (d[499] + 15):
                    try:
                        def retryFunc5():
                            close_amount = abs(float(position['info']['positionAmt']))

                            # Cancel all open orders before creating the new market order
                            for order in orders:
                                binance_futures.cancel_order(order['id'], '1000PEPE/USDT:USDT')
                                time.sleep(2)  # add a break for safety

                            binance_futures.create_market_buy_order('1000PEPE/USDT:USDT', close_amount)
                        retryFunc5()
                    except Exception as e:
                        print(f"Error closing short position: {e}")
                        time.sleep(10)
                        retryFunc5()

            elif position['side'] == 'long':
                if (k[499] + 15) < d[499]:
                    try:
                        def retryFunc6():
                            close_amount = abs(float(position['info']['positionAmt']))

                            # Cancel all open orders before creating the new market order
                            for order in orders:
                                binance_futures.cancel_order(order['id'], '1000PEPE/USDT:USDT')
                                time.sleep(2)  # add a break for safety

                            binance_futures.create_market_sell_order('1000PEPE/USDT:USDT', close_amount)
                        retryFunc6()
                    except Exception as e:
                        print(f"Error closing long position: {e}")
                        time.sleep(10)
                        retryFunc6()
    else:
        pass

# General Function
def main():
    initial_transfer()
    
    while True:
        try:
            # check_and_withdraw_spot_balance()
            manage_futures_positions_and_balance()
            time.sleep(5)  # Main loop delay
        except Exception as e:
            print(f"An error occurred in the main loop: {e}")
            time.sleep(20)  # Wait for 20 seconds before retrying

# CALLING THE GENERAL FUNCTION
main()