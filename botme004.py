import ccxt
import pandas as pd
import talib as ta
import time

# The User's API keys and addresses
SPOT_API_KEY = 'qeSMvIcWC80rj3Ns0pJV2oJzMxt4lLy4C2eXCU05MenQ9ssQLKJcRrRJEzLjGD4k'
SPOT_SECRET_KEY = 'aMXwE79fkF6PnbMzdOemYEMNgbmu2ze9aHUGHmtWBT3VUGnXRCkutZ0T5sQmagXn'
FUTURES_API_KEY = 'ZkUZDQgbuJkk5a1RRODbMpMKcEpcr9Qc81zVD0xmblaPlGbPKwUAA7K9HhvW0aIs'
FUTURES_SECRET_KEY = 'ReliyQQXHqcOZ14d4thxUTtN3Ei6MVHezNMS9ONB8kqIenZdmeLW0s5hjp3JEE2T'
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

#Function For Transfer Of The Capital To The Futures Account
def initial_transfer():
    balance = binance_spot.fetch_balance()['total']['USDT']
    if balance > 0:
        binance_spot.sapi_post_futures_transfer({
            'asset': 'USDT',
            'amount': balance,
            'type': 1  # Type 1 means transfer from spot to futures
        })

#Function For Withdrawal of The Profit Transfered to Spot Account
def check_and_withdraw_spot_balance():
    usdt_profit_balance = binance_spot.fetch_balance()['total']['USDT']
    if usdt_profit_balance > 500:
        binance_spot.withdraw('USDT', usdt_profit_balance, ADDRESS_ONE, tag=None, params={'network': 'BEP20'})
        time.sleep(10)  # Sleep to ensure the withdrawals are processed

#Function For Fetching OHLCV
def fetch_OHLCV(symbol, timeframe, limit=500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

#Function For Calculating STOCHASTIC OSCILLATOR
def calculate_indicators(df, window=20, num_std_dev=2):
    #Stochastic Oscillator
    rsi = ta.RSI(df['close'].values, timeperiod=14)
    k, d = ta.STOCH(rsi, rsi, rsi, 
                    fastk_period=14, 
                    slowk_period=3, 
                    slowk_matype=0, 
                    slowd_period=3, 
                    slowd_matype=0)
    
    #Bollinger Bands
    rolling_mean = df['close'].rolling(window=window).mean()
    rolling_std = df['close'].rolling(window=window).std()
    upperband = rolling_mean + (rolling_std * num_std_dev)
    middleband = rolling_mean
    lowerband = rolling_mean - (rolling_std * num_std_dev)

    return k, d, upperband, middleband, lowerband

#Function for Calculating Bollinger

#Manage Futures Position And Balance
def manage_futures_positions_and_balance():
    #setting leverage
    binance_futures.set_leverage(10, '1000PEPE/USDT:USDT')

    #fetching USDT Balance
    usdt_balance = binance_futures.fetch_balance()['total']['USDT']

    #fetching OHLCV
    df = fetch_OHLCV('1000PEPE/USDT', '5m')

    #calculating indicators
    k, d, upperband, middleband, lowerband = calculate_indicators(df)

    #checking positions and orders
    positions = binance_futures.fetch_positions_risk()
    orders = binance_futures.fetch_open_orders('1000PEPE/USDT:USDT')
    current_price = binance_futures.fetch_ticker('1000PEPE/USDT:USDT')['last']

    #MAIN TRADING LOGIC
    if len(positions) == 0:
        #Creating order for a golden cross at a good BB
        if k.tail(1) > (d.tail(1) + 15) and current_price < middleband:      
            amount = usdt_balance * 10 / current_price
            binance_futures.create_market_buy_order("1000PEPE/USDT:USDT", amount)   
            time.sleep(20) #add a break for safety

            #taking profit order
            recent_order = binance_futures.fetch_closed_orders('1000PEPE/USDT:USDT')[-1]
            open_price = float(recent_order['info']['avgPrice'])
            target_price = open_price  + (open_price * 0.0055)
            close_amount = float(amount)
            binance_futures.create_limit_sell_order('1000PEPE/USDT:USDT', close_amount, target_price)
            time.sleep(10) #add a break for safety
        #Creating order for a death cross at a good ema
        elif (k.tail(1) + 10) < d.tail(1) and current_price > middleband:
            amount = usdt_balance * 10 / current_price
            binance_futures.create_market_sell_order("1000PEPE/USDT:USDT", amount)   
            time.sleep(10) #add a break for safety

            #taking profit order
            recent_order = binance_futures.fetch_closed_orders('1000PEPE/USDT:USDT')[-1]
            open_price = float(recent_order['info']['avgPrice'])
            target_price = open_price  - (open_price * 0.0055)
            close_amount = float(amount)
            binance_futures.create_limit_buy_order('1000PEPE/USDT:USDT', close_amount, target_price)
            time.sleep(10) #add a break for safety
    elif len(positions) > 0 and  len(orders) == 0:
        #Taking Profit By Creating Order For Closing Positions
        for position in positions:
            if position['side'] == 'short':
                open_price = float(position['entryPrice'])
                target_price = open_price  - (open_price * 0.0055)
                close_amount = abs(float(position['info']['positionAmt']))
                binance_futures.create_limit_buy_order('1000PEPE/USDT:USDT', close_amount, target_price)
                time.sleep(10) #add a break for safety
            elif position['side'] == 'long':
                open_price = float(position['entryPrice'])
                target_price = open_price  + (open_price * 0.0055)
                close_amount = abs(float(position['info']['positionAmt']))
                binance_futures.create_limit_sell_order('1000PEPE/USDT:USDT', close_amount, target_price)
                time.sleep(10) #add a break for safety
    elif len(positions) > 0 and  len(orders) > 0:
        for position in positions:
            #Exiting Before A Major Loss
            if position['side'] == 'short' and k.tail(1) > (d.tail(1) + 15):
                close_amount = abs(float(position['info']['positionAmt']))
                binance_futures.create_market_buy_order('1000PEPE/USDT:USDT', close_amount, target_price)
            elif position['side'] == 'long' and (k.tail(1) + 10) < d.tail(1):
                close_amount = abs(float(position['info']['positionAmt']))
                binance_futures.create_market_sell_order('1000PEPE/USDT:USDT', close_amount, target_price)
    else:
        pass


#General Function
def main():
    initial_transfer()
    while True:
        try: 
            #check_and_withdraw_spot_balance()
            manage_futures_positions_and_balance()
            time.sleep(5)  # Main loop delay
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(20)  # Wait for 20 seconds before retrying

#CALLING THE GENERAL FUNCTION
main()