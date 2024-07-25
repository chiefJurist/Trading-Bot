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

#Function For Transfer of the capital to the futures account
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
def calculate_stoch(df):
    rsi = ta.RSI(df['close'].values, timeperiod=14)
    k, d = ta.STOCH(rsi, rsi, rsi, fastk_period=14, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)

#Function for Calculating EMA
def calculate_ema(df2):
    ema1 = ta.EMA(df2['close'], timeperiod=7)
    ema2 = ta.EMA(df2['close'], timeperiod=25)
    ema3 = ta.EMA(df2['close'], timeperiod=99)

#Manage Futures Position And Balance
def manage_futures_positions_and_balance():
    #setting leverage
    binance_futures.set_leverage(10, '1000BONK/USDT:USDT')

    #fetching USDT Balance
    usdt_balance = binance_futures.fetch_balance()['total']['USDT']

    #fetching OHLCV and plotting Stochastic Oscillator
    df = fetch_OHLCV('1000BONK/USDT', '5m')
    df2 = fetch_OHLCV('1000BONK/USDT', '3m')

    #calculating indicators
    k, d = calculate_stoch(df)
    ema1, ema2, ema3 = calculate_ema(df2)

    #GOLDEN CROSS AT A GOOD EMA
    if k[499] > d[499] and ema1[499] > ema2[499] and ema2[499] > ema3[499]:
        #Close Shorts If Any And Open A Long Position Regardless
        positions = binance_futures.fetch_positions_risk()
        if positions:
            for position in positions:
                #close short positions
                if position['side'] == 'short':
                    binance_futures.create_market_buy_order('1000BONK/USDT:USDT', abs(float(position['info']['positionAmt'])))
                    time.sleep(10)  # Sleep to ensure safety

                    #check total balance to inititate withdrawal if neccessary
                    # if usdt_balance >= 600:
                    #     transfer_amount = usdt_balance - 100
                    #     binance_futures.sapi_post_futures_transfer({
                    #         'asset': 'USDT',
                    #         'amount': transfer_amount,
                    #         'type': 2  # Type 2 means transfer from futures to spot
                    #     })
                    #     usdt_balance = 100
                    #     time.sleep(30)  # Sleep to ensure safety
                elif position['side'] == 'long':
                    pass
        else:
            #create a long position regardless
            current_price = binance_futures.fetch_ticker('1000BONK/USDT:USDT')['last']
            amount = usdt_balance * 10 / current_price

            binance_futures.create_market_buy_order("1000BONK/USDT:USDT", amount)   
            #Add a break
            time.sleep(10)


    #DEATH CROSS
    if d[499] > k[499]:
        #Close Longs If Any And Open A Short Position Regardless
        positions = binance_futures.fetch_positions_risk()
        if positions:
            for position in positions:
                if position['side'] == 'long':
                    #close long positions
                    binance_futures.create_market_sell_order('1000BONK/USDT:USDT', abs(float(position['info']['positionAmt'])))
                    time.sleep(10)  # Sleep to ensure safety

                    #check total balance to inititate withdrawal if neccessary
                    # if usdt_balance >= 600:
                    #     transfer_amount = usdt_balance - 100
                    #     binance_futures.sapi_post_futures_transfer({
                    #         'asset': 'USDT',
                    #         'amount': transfer_amount,
                    #         'type': 2  # Type 2 means transfer from futures to spot
                    #     })
                    #     usdt_balance = 100
                    #     time.sleep(30)  # Sleep to ensure safety  
                elif position['side'] == 'short':
                    pass        
        else:
            #create a short position regardless
            current_price = binance_futures.fetch_ticker('1000BONK/USDT:USDT')['last']
            amount = usdt_balance * 10 / current_price

            binance_futures.create_market_sell_order("1000BONK/USDT:USDT", amount)
            time.sleep(10)  # Sleep to ensure safety


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