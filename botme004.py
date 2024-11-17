import ccxt
import pandas as pd
import talib as ta
import time
import math
import numpy as np

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

# #Function For Transfer Of The Capital To The Futures Account
# def initial_transfer():
#     balance = binance_spot.fetch_balance()['total']['USDT']
#     if balance > 0:
#         binance_spot.sapi_post_futures_transfer({
#             'asset': 'USDT',
#             'amount': balance,
#             'type': 1  # Type 1 means transfer from spot to futures
#         })
#     time.sleep(10)  # add a break for safety

#Function For Tranfering Profit From Futures To Spot
def transfer_and_withdraw_profit():
    try:
        # Fetch balances
        profit_balance = binance_futures.fetch_balance()['total']['USDT']

        # Check if the prifit balance  is greater than or equal to 600
        if profit_balance >= 600:
            orders = binance_futures.fetch_open_orders('BTC/USDT:USDT')
            # Cancel all open orders
            for order in orders:
                try:
                    binance_futures.cancel_order(order['id'], 'BTC/USDT:USDT')
                    time.sleep(10)  # Add a break for safety
                except Exception as e:
                    print(f"Failed to cancel order {order['id']} to withdraw profit: {e}")

            # Fetch positions
            positions = binance_futures.fetch_positions_risk()
            # Close all positions
            for position in positions:
                try:
                    close_amount = abs(float(position['info']['positionAmt']))
                    if position['side'] == 'long':
                        binance_futures.create_order(
                            symbol='BTC/USDT:USDT',  # Symbol for the asset
                            side='SELL',                  # Sell to close the long position
                            type='MARKET',                # Market order
                            amount=close_amount,          # Amount to sell (the amount of the long position)
                            params={"positionSide": "LONG"}       # Specify "LONG" to close the long position
                        )
                    elif position['side'] == 'short':
                        binance_futures.create_order(
                            symbol='BTC/USDT:USDT',  # Symbol for the asset
                            side='BUY',                  # Sell to close the long position
                            type='MARKET',                # Market order
                            amount=close_amount,          # Amount to sell (the amount of the short position)
                            params={"positionSide": "SHORT"}           # Specify "SHORT" to close the short position
                        )
                except Exception as e:
                    print(f"Failed to close positions to withdraw profit: {e}")

            # Transfer the profit to Spot
            try:
                binance_spot.sapi_post_futures_transfer({
                    'asset': 'USDT',
                    'amount': 502,
                    'type': 2  # Transfer from Futures to Spot
                })
                time.sleep(10)  # Add a break for safety
            except Exception as e:
                print(f"Failed to transfer USDT: {e}")

            # Check Spot balance before withdrawal
            spot_balance = binance_spot.fetch_balance()['total']['USDT']
            if spot_balance >= 501:
                # Withdraw the transferred profit
                binance_spot.withdraw('USDT', 501, ADDRESS_ONE, tag=None, params={'network': 'BEP20'})
            else:
                print(f"Insufficient Spot balance for withdrawal: {spot_balance}")
    
    except Exception as e:
        print(f"Error in transfer_and_withdraw_profit: {e}")



#Function For Fetching OHLCV
def fetch_OHLCV(symbol, timeframe, limit=500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Function to approximate to 6 significant figures and handle NaN values
def significant_figures(x):
    if pd.isna(x) or x == 0:  # Check for NaN or zero
        return np.nan if pd.isna(x) else 0
    else:
        return round(x, 6 - int(math.floor(math.log10(abs(x)))) - 1)
    
#Function For Calculating Indicators
def calculate_indicators(df, window=20, num_std_dev=0.975):
    #Stochastic Oscillator
    rsi = ta.RSI(df['close'].values, timeperiod=14)
    k, d = ta.STOCH(rsi, rsi, rsi, 
                    fastk_period=14, 
                    slowk_period=3, 
                    slowk_matype=0, 
                    slowd_period=3, 
                    slowd_matype=0)
    #Bollinger Bands
    # Calculate the moving average (middle band) and round it to 6 significant figures
    middle_band_calc = df['close'].rolling(window=window, min_periods=1).mean()
    middleband = middle_band_calc.apply(significant_figures)
    # Calculate the standard deviation and use it to derive the upper and lower bands
    std_dev = df['close'].rolling(window=window, min_periods=1).std()
    # Calculate the upper and lower bands and round them to 6 significant figures
    upperband = (middleband + (std_dev * num_std_dev)).apply(significant_figures)
    lowerband = (middleband - (std_dev * num_std_dev)) .apply(significant_figures)
    
    return k, d, upperband, middleband, lowerband

#Manage Futures Position And Balance
def manage_futures_positions_and_balance():
    #Setting leverage
    binance_futures.set_leverage(15, 'BTC/USDT:USDT')

    #Fetching USDT Balance
    usdt_balance = binance_futures.fetch_balance()['total']['USDT']

    #Fetching OHLCV
    df = fetch_OHLCV('BTC/USDT:USDT', '5m')

    #Calculating indicators
    k, d, upperband, middleband, lowerband = calculate_indicators(df)

    #Closing Prices of candles
    last_close = df['close'].iloc[-2]       # Last candle close
    second_last_close = df['close'].iloc[-3] # Second to last candle close
    third_last_close = df['close'].iloc[-4] # third to last candle close

    #Checking positions and orders
    positions = binance_futures.fetch_positions_risk()
    orders = binance_futures.fetch_open_orders('BTC/USDT:USDT')

    # Check if there is an open long or short position
    long_position_open = any(pos['side'] == 'long' for pos in positions)
    short_position_open = any(pos['side'] == 'short' for pos in positions)
    
    current_price = binance_futures.fetch_ticker('BTC/USDT:USDT')['last'] #fetching the current price


    #MAIN TRADING LOGIC WHEN NO POSITION IS OPENED
    if len(positions) == 0:
        # Managing Long Positions
        if not long_position_open: #ensure no long position is opened 
            if k[498] > d[498] and k[497] > d[497]:  
                if last_close > lowerband[498] and second_last_close > lowerband[497] and third_last_close < lowerband[496]:
                    try:
                        amount = usdt_balance * 5 / current_price #using half of the capital
                        binance_futures.create_order(
                            symbol="BTC/USDT:USDT",  # Symbol for the asset
                            side="BUY",                   # Buy to open a long position
                            type="MARKET",                 # Market order
                            amount=amount,                 # Amount of asset to buy
                            params={"positionSide": "LONG"} # Specify "LONG" since you're in Hedge Mode
                        )
                        time.sleep(10) #add a break for safety
                    except Exception as e:
                        print(f"Error in opening long positions when no position is opened : {e}")
                    # Taking profit order
                    try:
                        open_price = binance_futures.fetch_closed_orders('BTC/USDT:USDT')[-1]['average']
                        target_price = open_price + (open_price * 0.0155)
                        close_amount = float(amount)
                        binance_futures.create_order(
                            symbol='BTC/USDT:USDT',  # Symbol for the asset
                            side='SELL',                  # Sell to close the long position
                            type='LIMIT',                 # Limit order
                            amount=close_amount,          # Amount to sell
                            price=target_price,           # Target price for the limit order
                            params = {
                                "positionSide": "LONG",  # Specify "LONG" to close the long position
                                "timeInForce": "GTC"     # Good 'til canceled; adjust as necessary
                            }
                        )
                        time.sleep(10)  # add a break for safety
                    except Exception as e:
                        print(f"Error in creating close order for long positions when no position is opened : {e}")

        # Managing Short Poitions
        if not short_position_open: #ensure no short position is opened 
            if k[498] < d[498] and k[497] < d[497]:  
                if last_close < upperband[498] and second_last_close < upperband[497] and third_last_close > upperband[496] :
                    try:
                        amount = usdt_balance * 5 / current_price #using half of the capital
                        binance_futures.create_order(
                            symbol='BTC/USDT:USDT',  # Symbol for the asset
                            side='SELL',                  # Sell to open a short position
                            type='MARKET',                # Market order
                            amount=amount,                # Amount to sell
                            params={"positionSide": "SHORT"}          # Specify "SHORT" to open the short position
                        )
                        time.sleep(10) #add a break for safety
                    except Exception as e:
                        print(f"Error in opening short positions when no position is opened : {e}")
                    # Taking profit order
                    try:
                        open_price = binance_futures.fetch_closed_orders('BTC/USDT:USDT')[-1]['average']
                        target_price = open_price - (open_price * 0.0155)
                        close_amount = float(amount)
                        binance_futures.create_order(
                            symbol='BTC/USDT:USDT',  # Symbol for the asset
                            side='BUY',                   # Buy to close the short position
                            type='LIMIT',                 # Limit order
                            amount=close_amount,          # Amount to buy
                            price=target_price,           # Target price for the limit order
                            params = {
                                "positionSide": "SHORT",  # Specify "SHORT" to close the short position
                                "timeInForce": "GTC"     # Good 'til canceled; adjust as necessary
                            }
                        )
                        time.sleep(10)  # add a break for safety
                    except Exception as e:
                        print(f"Error in creating close order for short positions when no position is opened : {e}")



#MAIN TRADING LOGIC WHEN A POSITION IS OPENED
    if len(positions) > 0:
        #Remaining balance
        remaining_balance = (usdt_balance) - (positions[-1]["initialMargin"])

        # Managing Long Positions
        if not long_position_open: #ensure no long position is opened 
            if k[498] > d[498] and k[497] > d[497]:  
                if last_close > lowerband[498] and second_last_close > lowerband[497] and third_last_close < lowerband[496]:
                    try:
                        amount = remaining_balance * 5 / current_price #using half of the capital
                        binance_futures.create_order(
                            symbol="BTC/USDT:USDT",  # Symbol for the asset
                            side="BUY",                   # Buy to open a long position
                            type="MARKET",                 # Market order
                            amount=amount,                 # Amount of asset to buy
                            params={"positionSide": "LONG"} # Specify "LONG" since you're in Hedge Mode
                        )
                        time.sleep(10) #add a break for safety
                    except Exception as e:
                        print(f"Error in opening long positions when no position is opened : {e}")
                    # Taking profit order
                    try:
                        open_price = binance_futures.fetch_closed_orders('BTC/USDT:USDT')[-1]['average']
                        target_price = open_price + (open_price * 0.0155)
                        close_amount = float(amount)
                        binance_futures.create_order(
                            symbol='BTC/USDT:USDT',  # Symbol for the asset
                            side='SELL',                  # Sell to close the long position
                            type='LIMIT',                 # Limit order
                            amount=close_amount,          # Amount to sell
                            price=target_price,           # Target price for the limit order
                            params = {
                                "positionSide": "LONG",  # Specify "LONG" to close the long position
                                "timeInForce": "GTC"     # Good 'til canceled; adjust as necessary
                            }
                        )
                        time.sleep(10)  # add a break for safety
                    except Exception as e:
                        print(f"Error in creating close order long positions when no position is opened : {e}")

        # Managing Short Poitions
        if not short_position_open: #ensure no short position is opened 
            if k[498] < d[498] and k[497] < d[497]:  
                if last_close < upperband[498] and second_last_close < upperband[497] and third_last_close > upperband[496] :
                    try:
                        amount = remaining_balance * 5 / current_price #using half of the capital
                        binance_futures.create_order(
                            symbol='BTC/USDT:USDT',  # Symbol for the asset
                            side='SELL',                  # Sell to open a short position
                            type='MARKET',                # Market order
                            amount=amount,                # Amount to sell
                            params={"positionSide": "SHORT"}          # Specify "SHORT" to open the short position
                        )
                        time.sleep(10) #add a break for safety
                    except Exception as e:
                        print(f"Error in opening short positions : {e}")
                    # Taking profit order
                    try:
                        open_price = binance_futures.fetch_closed_orders('BTC/USDT:USDT')[-1]['average']
                        target_price = open_price - (open_price * 0.0155)
                        close_amount = float(amount)
                        binance_futures.create_order(
                            symbol='BTC/USDT:USDT',  # Symbol for the asset
                            side='BUY',                   # Buy to close the short position
                            type='LIMIT',                 # Limit order
                            amount=close_amount,          # Amount to buy
                            price=target_price,           # Target price for the limit order
                            params = {
                                "positionSide": "SHORT",  # Specify "SHORT" to close the short position
                                "timeInForce": "GTC"     # Good 'til canceled; adjust as necessary
                            }
                        )
                        time.sleep(10)  # add a break for safety
                    except Exception as e:
                        print(f"Error in creating close order for short positions: {e}")




    #Managing Open Long Positions For Risk Management
    if k[498] < d[498] and last_close < lowerband[498]:
        if positions:
            for position in positions:
                if position['side'] == 'long':
                    #canceling the take profit order before creating a market order for closing position
                    for order in orders:
                        if order['side'] == 'sell' and order['type'] == 'limit':  # Only cancel orders for long
                            try:
                                binance_futures.cancel_order(order['id'], 'BTC/USDT:USDT')
                                time.sleep(10)  # add a break for safety
                            except Exception as e:
                                print(f"Error in canceling close order for long position so that we can close position: {e}")

                    #creating a market order for closing position
                    try:
                        close_amount = abs(float(position['contracts']))
                        binance_futures.create_order(
                            symbol='BTC/USDT:USDT',  # Symbol for the asset
                            side='SELL',                  # Sell to close the long position
                            type='MARKET',                # Market order
                            amount=close_amount,          # Amount to sell (the amount of the long position)
                            params={"positionSide": "LONG"}       # Specify "LONG" to close the long position
                        )
                    except Exception as e:
                        print(f"Error in closing long position for risk management: {e}")

    #Managing Open Short Positions For Risk Management
    if k[498] > d[498] and last_close > upperband[498]:
         if positions:
            for position in positions:
                if position['side'] == 'short':
                        #canceling the take profit order before creating a market order for closing position
                        for order in orders:
                            if order['side'] == 'buy' and order['type'] == 'limit':  # Only cancel buy orders
                                try:
                                    binance_futures.cancel_order(order['id'], 'BTC/USDT:USDT')
                                    time.sleep(10)  # add a break for safety
                                except Exception as e:
                                    print(f"Error in canceling close order for short position so that we can close position: {e}")

                        #creating a market order for closing position
                        try:
                            close_amount = abs(float(position['contracts']))
                            binance_futures.create_order(
                                symbol='BTC/USDT:USDT',  # Symbol for the asset
                                side='BUY',                  # Sell to close the long position
                                type='MARKET',                # Market order
                                amount=close_amount,          # Amount to sell (the amount of the short position)
                                params={"positionSide": "SHORT"}           # Specify "SHORT" to close the short position
                            )
                        except Exception as e:
                            print(f"Error in closing long position for risk management: {e}")



#General Function
def main():
    # initial_transfer()
    
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