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
    balance = binance_spot.fetch_balance()
    usdt_balance = balance['total']['USDT']
    
    if usdt_balance > 500:
        binance_spot.withdraw('USDT', usdt_balance, ADDRESS_ONE, tag=None, params={'network': 'BEP20'})
        time.sleep(10)  # Sleep to ensure the withdrawals are processed


#Function For Fetching OHLCV
def fetch_OHLCV(symbol, timeframe, limit=500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df


#Function For Calculating STOCHASTIC OSCILLATOR
def calculate_stochastic_oscillator(df):
    rsi = ta.RSI(df['close'].values, timeperiod=14)
    k, d = ta.STOCH(rsi, rsi, rsi, 
                    fastk_period=14, slowk_period=3, slowk_matype=0, 
                    slowd_period=3, slowd_matype=0)
    return k, d



#Manage Futures Position And Balance
#Setting Position Variable
long = False
short = False

def manage_futures_positions_and_balance():
    #setting leverage
    binance_futures.set_leverage(10, 'ETH/USDT:USDT')

    while True:
        #Fetching USDT Balance
        usdt_balance = binance_futures.fetch_balance()['total']['USDT']

        #fetching OHLCV and plotting Stochastic Oscillator
        df = fetch_OHLCV('ETH/USDT', '5m')
        k, d = calculate_stochastic_oscillator(df)


        #GOLDEN CROSS
        if k[499] > d[499]:
            #close short positions
            if short:
                positions = binance_futures.fetch_positions_risk()
                if positions:
                    for position in positions:
                        binance_futures.create_market_buy_order('ETH/USDT:USDT', abs(float(position['info']['positionAmt'])))
                        short = False

                    #check total balance to inititate withdrawal if neccessary
                    if usdt_balance >= 600:
                        transfer_amount = usdt_balance - 100
                        binance_futures.sapi_post_futures_transfer({
                            'asset': 'USDT',
                            'amount': transfer_amount,
                            'type': 2  # Type 2 means transfer from futures to spot
                        })
                        usdt_balance = 100

            #create a long position
            if long != True:
                current_price = binance_futures.fetch_ticker('ETH/USDT:USDT')['last']
                amount = usdt_balance * 10 / current_price

                binance_futures.create_market_buy_order("ETH/USDT:USDT", amount)

                #set the position variable
                long = True

            #Add a 30 seconds break
            time.sleep(30)


        #DEATH CROSS
        if d[499] > k[499]:
            #close long positions
            if long:
                positions = binance_futures.fetch_positions_risk()
                if positions:
                    for position in positions:
                        binance_futures.create_market_sell_order('ETH/USDT:USDT', abs(float(position['info']['positionAmt'])))
                        long = False
                        
                    #check total balance to inititate withdrawal if neccessary
                    if usdt_balance >= 600:
                        transfer_amount = usdt_balance - 100
                        binance_futures.sapi_post_futures_transfer({
                            'asset': 'USDT',
                            'amount': transfer_amount,
                            'type': 2  # Type 2 means transfer from futures to spot
                        })
                        usdt_balance = 100

            #create a short position
            if short != True:
                current_price = binance_futures.fetch_ticker('ETH/USDT:USDT')['last']
                amount = usdt_balance * 10 / current_price

                binance_futures.create_market_buy_order("ETH/USDT:USDT", amount)

                #set the position variable
                short = True

            #Add a 30 seconds break
            time.sleep(30)


#General Function
def main():
    initial_transfer()
    while True:
        check_and_withdraw_spot_balance()
        manage_futures_positions_and_balance()
        time.sleep(60)  # Main loop delay

#CALLING THE GENERAL FUNCTION
main()