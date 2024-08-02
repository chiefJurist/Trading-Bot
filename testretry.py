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

# Function for Transfer of Capital to the Futures Account
def initial_transfer(delay=2):
    try:
        balance = binance_spot.fetch_balance()['total']['USDT']
        if balance > 0:
            binance_spot.sapi_post_futures_transfer({
                'asset': 'USDT',
                'amount': balance,
                'type': 1  # Type 1 means transfer from spot to futures
            })
    except Exception as e:
        print(f"Error in initial_transfer: {e}")
        time.sleep(delay)  # Wait before retrying
        initial_transfer(delay)  # Recursive call for retry

# Function for Withdrawal of Profit Transferred to Spot Account
def check_and_withdraw_spot_balance(delay=2):
    try:
        usdt_profit_balance = binance_spot.fetch_balance()['total']['USDT']
        if usdt_profit_balance > 500:
            binance_spot.withdraw('USDT', usdt_profit_balance, ADDRESS_ONE, tag=None, params={'network': 'BEP20'})
            time.sleep(10)  # Sleep to ensure the withdrawals are processed
    except Exception as e:
        print(f"Error in check_and_withdraw_spot_balance: {e}")
        time.sleep(delay)  # Wait before retrying
        check_and_withdraw_spot_balance(delay)  # Recursive call for retry

# Function for Fetching OHLCV
def fetch_OHLCV(symbol, timeframe, limit=500, delay=2):
    try:
        bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"Error in fetch_OHLCV: {e}")
        time.sleep(delay)  # Wait before retrying
        return fetch_OHLCV(symbol, timeframe, limit, delay)  # Recursive call for retry

# Function for Calculating Indicators
def calculate_indicators(df, window=20, num_std_dev=2, delay=2):
    try:
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
    except Exception as e:
        print(f"Error in calculate_indicators: {e}")
        time.sleep(delay)  # Wait before retrying
        return calculate_indicators(df, window, num_std_dev, delay)  # Recursive call for retry

# Manage Futures Position And Balance
def manage_futures_positions_and_balance(delay=2):
    # Setting leverage
    try:
        binance_futures.set_leverage(10, '1000PEPE/USDT:USDT')
    except Exception as e:
        print(f"Error setting leverage: {e}")
        time.sleep(delay)  # Wait before retrying
        manage_futures_positions_and_balance(delay)  # Recursive call for retry

    # Fetching USDT Balance
    try:
        usdt_balance = binance_futures.fetch_balance()['total']['USDT']
    except Exception as e:
        print(f"Error fetching USDT balance: {e}")
        time.sleep(delay)  # Wait before retrying
        manage_futures_positions_and_balance(delay)  # Recursive call for retry

    # Fetching OHLCV
    try:
        df = fetch_OHLCV('1000PEPE/USDT', '5m')
    except Exception as e:
        print(f"Error fetching OHLCV data: {e}")
        time.sleep(delay)  # Wait before retrying
        df = fetch_OHLCV('1000PEPE/USDT', '5m', delay=delay)  # Recursive call for retry

    # Calculating indicators
    try:
        k, d, upperband, middleband, lowerband = calculate_indicators(df)
    except Exception as e:
        print(f"Error calculating indicators: {e}")
        time.sleep(delay)  # Wait before retrying
        k, d, upperband, middleband, lowerband = calculate_indicators(df, delay=delay)  # Recursive call for retry

    # Checking positions and orders
    try:
        positions = binance_futures.fetch_positions_risk()
        orders = binance_futures.fetch_open_orders('1000PEPE/USDT:USDT')
    except Exception as e:
        print(f"Error fetching positions, orders: {e}")
        time.sleep(delay)  # Wait before retrying
        manage_futures_positions_and_balance(delay)  # Recursive call for retry

    # MAIN TRADING LOGIC
    # (Insert trading logic here, ensure you handle retries for each specific case)

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
