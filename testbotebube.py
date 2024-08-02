import ccxt
import pandas as pd
import talib as ta
import time

# The User's API keys and addresses
SPOT_API_KEY = 'ogP4gQPw6Ka4L5EW59vVAlalpbWuQSKxGVTfEbb9YrcMAg97j1kHaJOncciPMz38'
SPOT_SECRET_KEY = 'VmaNFuEh14rElVB2bPgIX3JMO1ZusOHLxmHoL0RDvRQrS5sXuK9Li9JV1gs0OL6s'
FUTURES_API_KEY = 'CkPX3ZqS27pqcE1g0PFAEJNoaAXfrde6F4dmw9xi4EXkfOGIKHbdmsifbLGsokqf'
FUTURES_SECRET_KEY = 'ij7UTix4aa3G6itq7ROW33fSdJMZSNofRog2yHqOTNoW13VN0yIn2O1gp53QFBwq'
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

# Function For Transfer Of The Capital To The Futures Account
def initial_transfer():
    balance = binance_spot.fetch_balance()['total']['USDT']
    if balance > 0:
        binance_spot.sapi_post_futures_transfer({
            'asset': 'USDT',
            'amount': balance,
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
    try:
        binance_futures.set_leverage(10, '1000PEPE/USDT:USDT')
    except Exception as e:
        print(f"Error setting leverage: {e}")
        return

    # Fetching USDT Balance
    try:
        usdt_balance = binance_futures.fetch_balance()['total']['USDT']
    except Exception as e:
        print(f"Error fetching USDT balance: {e}")
        return

    # Fetching OHLCV
    try:
        df = fetch_OHLCV('1000PEPE/USDT', '5m')
    except Exception as e:
        print(f"Error fetching OHLCV data: {e}")
        return

    # Calculating indicators
    try:
        k, d, upperband, middleband, lowerband = calculate_indicators(df)
    except Exception as e:
        print(f"Error calculating indicators: {e}")
        return

    # Checking positions and orders
    try:
        positions = binance_futures.fetch_positions_risk()
        orders = binance_futures.fetch_open_orders('1000PEPE/USDT:USDT')
    except Exception as e:
        print(f"Error fetching positions, orders, or current price: {e}")
        return

    # MAIN TRADING LOGIC
    if len(positions) == 0:
        # Creating order for a golden cross at a good BB
        if k[499] > (d[499] + 15) and k[498] > (d[498] + 15) and k[497] > (d[497] + 15) and k[496] > (d[496] + 15) and k[495] > (d[495] + 15) and k[494] > (d[494] + 15) and current_price < middleband[499]:
            try:
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
            except Exception as e:
                print(f"Error creating market buy or limit sell order: {e}")

        # Creating order for a death cross at a good EMA
        elif (k[499] + 15) < d[499] and (k[498] + 15) < d[498] and (k[497] + 15) < d[497] and (k[496] + 15) < d[496] and (k[495] + 15) < d[495] and (k[494] + 15) < d[494] and current_price > middleband[499]:
            try:
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
            except Exception as e:
                print(f"Error creating market sell or limit buy order: {e}")

    elif len(positions) > 0 and len(orders) == 0:
        # Taking Profit By Creating Order For Closing Positions
        for position in positions:
            if position['side'] == 'short':
                try:
                    open_price = float(position['entryPrice'])
                    target_price = open_price - (open_price * 0.0055)
                    close_amount = abs(float(position['info']['positionAmt']))
                    binance_futures.create_limit_buy_order('1000PEPE/USDT:USDT', close_amount, target_price)
                    time.sleep(10)  # add a break for safety
                except Exception as e:
                    print(f"Error creating limit buy order for short position: {e}")
            elif position['side'] == 'long':
                try:
                    open_price = float(position['entryPrice'])
                    target_price = open_price + (open_price * 0.0055)
                    close_amount = abs(float(position['info']['positionAmt']))
                    binance_futures.create_limit_sell_order('1000PEPE/USDT:USDT', close_amount, target_price)
                    time.sleep(10)  # add a break for safety
                except Exception as e:
                    print(f"Error creating limit sell order for long position: {e}")

    elif len(positions) > 0 and len(orders) > 0:
        for position in positions:
            # Exiting Before A Major Loss
            if position['side'] == 'short':
                if k[499] > (d[499] + 15) or k[498] > (d[498] + 15) or k[497] > (d[497] + 15) or k[496] > (d[496] + 15) or k[495] > (d[495] + 15):
                    try:
                            close_amount = abs(float(position['info']['positionAmt']))

                            # Cancel all open orders before creating the new market order
                            for order in orders:
                                binance_futures.cancel_order(order['id'], '1000PEPE/USDT:USDT')
                                time.sleep(2)  # add a break for safety

                            binance_futures.create_market_buy_order('1000PEPE/USDT:USDT', close_amount)
                    except Exception as e:
                        print(f"Error closing short position: {e}")

            elif position['side'] == 'long':
                if (k[499] + 15) < d[499] or (k[498] + 15) < d[498] or (k[497] + 15) < d[497] or (k[496] + 15) < d[496] or (k[495] + 15) < d[495]:
                    try:
                            close_amount = abs(float(position['info']['positionAmt']))

                            # Cancel all open orders before creating the new market order
                            for order in orders:
                                binance_futures.cancel_order(order['id'], '1000PEPE/USDT:USDT')
                                time.sleep(2)  # add a break for safety

                            binance_futures.create_market_sell_order('1000PEPE/USDT:USDT', close_amount)
                    except Exception as e:
                        print(f"Error closing long position: {e}")
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