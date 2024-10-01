import ccxt
import pandas as pd
import talib as ta
import time

# The User's API keys and addresses
SPOT_API_KEY = 'lwObDP3Fcjia0OxQfombVxtG032NZWuFE4ctgKZPxBJYzblviFUd3ONUFAuOwcJq'
SPOT_SECRET_KEY = 'PIx7RsETsxoqkJUaltX5pssmHnCMSXqUmb0lJv5OHR4RxS9kOtN2UCeYAtqFFAVm'
FUTURES_API_KEY = 'FGqsynCXzPJoBJvcLG28EkQg2HvWlE4ANzt9Q3IIVH1iCqvuZ3jQh4Ipw2SzcpYn'
FUTURES_SECRET_KEY = 'Tg0IcgRO3Xh7PhxfSUs6MfheM46uWa7BIydrLy2Q3ker2VWIQlMvHBmiq566EVEz'
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
    time.sleep(10)  # add a break for safety

#Function For Tranfering Profit From Futures To Spot
def transfer_and_withdraw_profit():
    futures_usdt_profit = binance_futures.fetch_balance()['total']['USDT']
    if futures_usdt_profit >= 600 : 
        positions = binance_futures.fetch_positions_risk()
        orders = binance_futures.fetch_open_orders('BTC/USDT:USDT')
        #cancel all orders
        for order in orders:
            binance_futures.cancel_order(order['id'], 'BTC/USDT:USDT')
            time.sleep(10)  # add a break for safety
        #close all poitions
        for position in positions:
            if position['side'] == 'short':
                close_amount = abs(float(position['info']['positionAmt']))
                binance_futures.create_market_buy_order('BTC/USDT:USDT', close_amount)
            elif position['side'] == 'long':
                close_amount = abs(float(position['info']['positionAmt']))
                binance_futures.create_market_sell_order('BTC/USDT:USDT', close_amount)

        #transfering the profit
        binance_spot.sapi_post_futures_transfer({
            'asset': 'USDT',
            'amount': 502,
            'type': 2  # Type 2 means transfer from futures to spot
        })
        time.sleep(10)  # add a break for safety

        #Withdrawing The Tranferred Profit
        binance_spot.withdraw('USDT', 501, ADDRESS_ONE, tag=None, params={'network': 'BEP20'})

#Function For Fetching OHLCV
def fetch_OHLCV(symbol, timeframe, limit=500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

#Function For Calculating Indicators
def calculate_indicators(df, window=20, num_std_dev=1):
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

#Manage Futures Position And Balance
def manage_futures_positions_and_balance():
    #Setting leverage
    binance_futures.set_leverage(10, 'BTC/USDT:USDT')

    #Fetching USDT Balance
    usdt_balance = binance_futures.fetch_balance()['total']['USDT']

    #Fetching OHLCV
    df = fetch_OHLCV('BTC/USDT', '5m')

    #Calculating indicators
    k, d, upperband, middleband, lowerband = calculate_indicators(df)

    #Closing Prices of candles
    last_close = df['close'].iloc[-2]       # Last candle close
    second_last_close = df['close'].iloc[-3] # Second to last candle close
    third_last_close = df['close'].iloc[-4] # third to last candle close

    #Checking positions and orders
    positions = binance_futures.fetch_positions_risk()
    orders = binance_futures.fetch_open_orders('BTC/USDT:USDT')
    current_price = binance_futures.fetch_ticker('BTC/USDT:USDT')['last']

    #MAIN TRADING LOGIC
    # Managing Positions When There Is No Open Position
    if len(positions) == 0: 
        # Managing Long Positions
        if k[498] > d[498] and k[497] > d[497] and k[496] > d[496]:  
            if last_close > lowerband and second_last_close > lowerband and third_last_close < lowerband:
                amount = usdt_balance * 5 / current_price #using half of the capital
                binance_futures.create_market_buy_order("BTC/USDT:USDT", amount)   
                time.sleep(10) #add a break for safety
                # Taking profit order
                recent_order = binance_futures.fetch_closed_orders('BTC/USDT:USDT')[-1]
                open_price = float(recent_order['info']['avgPrice'])
                target_price = open_price + (open_price * 0.0155)
                close_amount = float(amount)
                binance_futures.create_limit_sell_order('BTC/USDT:USDT', close_amount, target_price)
                time.sleep(10)  # add a break for safety

        # Managing Short Poitions
        if k[498] < d[498]:  
            if last_close < upperband and second_last_close > upperband :
                amount = usdt_balance * 5 / current_price #using half of the capital
                binance_futures.create_market_sell_order("BTC/USDT:USDT", amount)   
                time.sleep(10) #add a break for safety
                # Taking profit order
                recent_order = binance_futures.fetch_closed_orders('BTC/USDT:USDT')[-1]
                open_price = float(recent_order['info']['avgPrice'])
                target_price = open_price + (open_price * 0.0155)
                close_amount = float(amount)
                binance_futures.create_limit_buy_order('BTC/USDT:USDT', close_amount, target_price)
                time.sleep(10)  # add a break for safety


    # Managing Long Positions When A Short Position Is Open
    elif len(positions) == 1 and positions[0]['side'] == 'short': 
        if k[498] > d[498] and k[497] > d[497] and k[496] > d[496]:  
            if last_close < upperband and second_last_close > upperband :
                amount = usdt_balance * 5 / current_price #using half of the capital
                binance_futures.create_market_buy_order("BTC/USDT:USDT", amount)   
                time.sleep(10) #add a break for safety
                # Taking profit order
                recent_order = binance_futures.fetch_closed_orders('BTC/USDT:USDT')[-1]
                open_price = float(recent_order['info']['avgPrice'])
                target_price = open_price + (open_price * 0.0155)
                close_amount = float(amount)
                binance_futures.create_limit_sell_order('BTC/USDT:USDT', close_amount, target_price)
                time.sleep(10)  # add a break for safety
                    

    # Managing Short Positions When A Long Position Is Open
    elif len(positions) == 1 and positions[0]['side'] == 'long': 
        if k[498] < d[498]:  
            if last_close < upperband and second_last_close > upperband :
                amount = usdt_balance * 5 / current_price #using half of the capital
                binance_futures.create_market_sell_order("BTC/USDT:USDT", amount)   
                time.sleep(10) #add a break for safety
                # Taking profit order
                recent_order = binance_futures.fetch_closed_orders('BTC/USDT:USDT')[-1]
                open_price = float(recent_order['info']['avgPrice'])
                target_price = open_price + (open_price * 0.0155)
                close_amount = float(amount)
                binance_futures.create_limit_buy_order('BTC/USDT:USDT', close_amount, target_price)
                time.sleep(10)  # add a break for safety


    #Managing Open Long Positions For Risk Management
    if k[498] < d[498] and last_close < lowerband:
        if positions:
            for position in positions:
                if position['side'] == 'long':
                    #canceling the take profit order before creating a market order for closing position
                    for order in orders:
                        if order['side'] == 'sell' and order['type'] == 'limit':  # Only cancel orders for long
                            binance_futures.cancel_order(order['id'], 'BTC/USDT:USDT')
                            time.sleep(10)  # add a break for safety

                    #creating a market order for closing position
                    close_amount = abs(float(position['info']['positionAmt']))
                    binance_futures.create_market_sell_order('BTC/USDT:USDT', close_amount)

    #Managing Open Short Positions For Risk Management
    if k[498] > d[498] and last_close > upperband:
         if positions:
            for position in positions:
                if position['side'] == 'short':
                        #canceling the take profit order before creating a market order for closing position
                        for order in orders:
                            if order['side'] == 'buy' and order['type'] == 'limit':  # Only cancel buy orders
                                binance_futures.cancel_order(order['id'], 'BTC/USDT:USDT')
                                time.sleep(10)  # add a break for safety

                        #creating a market order for closing position
                        close_amount = abs(float(position['info']['positionAmt']))
                        binance_futures.create_market_buy_order('BTC/USDT:USDT', close_amount)



#General Function
def main():
    initial_transfer()
    
    while True:
        try: 
            transfer_and_withdraw_profit()
            manage_futures_positions_and_balance()
            time.sleep(5)  # Main loop delay
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(10)  # Wait for 10 seconds before retrying

#CALLING THE GENERAL FUNCTION
main()
