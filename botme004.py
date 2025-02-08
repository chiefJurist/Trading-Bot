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


# Function for fetching OHLCV
def fetch_OHLCV(symbol, timeframe, limit=1500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

#Function For Calculating Bollinger Bands
def calculate_bollinger_bands(close_prices, timeperiod=20, nbdevup=1, nbdevdn=1):
    upperband, middleband, lowerband = ta.BBANDS(
        close_prices, timeperiod=timeperiod, nbdevup=nbdevup, nbdevdn=nbdevdn, matype=0
    )
    return upperband, middleband, lowerband


#Manage Futures Position And Balance
def manage_futures_positions_and_balance():
    #Setting leverage
    binance_futures.set_leverage(20, 'ETH/USDT:USDT')

    #Fetching USDT Balance
    total_usdt_balance = binance_futures.fetch_balance()['total']['USDT']
    free_usdt_balance = binance_futures.fetch_balance()['free']['USDT']

    #Fetching OHLCV
    df = fetch_OHLCV('ETH/USDT:USDT', '1m')

    #Calculating indicators
    upperband, middleband, lowerband = calculate_bollinger_bands(df)

    #Points in The Chart
    last_open = df['open'].iloc[-2]                     #last candle open price
    last_close = df['close'].iloc[-2]                   #last candle close price
    last_upperband = df['upperband'].iloc[-2]           #last candle upperband
    last_lowerband = df['lowerband'].iloc[-2]           #last candle lowerband
    second_last_open = df['open'].iloc[-3]              #second to the last candle open price
    second_last_close = df['close'].iloc[-3]            #second to the last candle close price
    second_last_upperband = df['upperband'].iloc[-3]    #second to the last candle upperband
    second_last_lowerband = df['lowerband'].iloc[-3]    #second to the last candle lowerband
    third_last_open = df['open'].iloc[-4]               #third to the last candle open price
    third_last_close = df['close'].iloc[-4]             #third to the last candle close price
    third_last_upperband = df['upperband'].iloc[-4]     #third to the last candle upperband
    third_last_lowerband = df['lowerband'].iloc[-4]     #third to the last candle lowerband
    fourth_last_open = df['open'].iloc[-5]              #fourth to the last candle open price
    fourth_last_close = df['close'].iloc[-5]            #fourth to the last candle close price
    fourth_last_upperband = df['upperband'].iloc[-5]    #fourth to the last candle upperband
    fourth_last_lowerband = df['lowerband'].iloc[-5]    #fourth to the last candle lowerband

    #Checking for open positions and open orders
    positions = binance_futures.fetch_positions_risk()
    orders = binance_futures.fetch_open_orders('ETH/USDT:USDT')

    # Check if there is an open long or short position
    long_position_open = any(pos['side'] == 'long' for pos in positions)
    short_position_open = any(pos['side'] == 'short' for pos in positions)
    
    #Getting the current price of the asset
    current_price = binance_futures.fetch_ticker('ETH/USDT:USDT')['last'] #fetching the current price


    #MAIN TRADING LOGIC
    if total_usdt_balance < 200:
        # MANAGING LONG POSITIONS
        if not long_position_open: #ensure no long position is opened 
            if last_close > last_lowerband and second_last_close > second_last_lowerband and third_last_close < third_last_lowerband and second_last_close > second_last_open and last_close > last_open: #trading logic
                try:
                    amount = total_usdt_balance * 20 / current_price #using the entire capital
                    binance_futures.create_order(
                        symbol="ETH/USDT:USDT",  # Symbol for the asset
                        side="BUY",                     # Buy to open a long position
                        type="MARKET",                  # Market order
                        amount=amount,                  # Amount of asset to buy
                        params={"positionSide": "LONG"} # Specify "LONG" since you're in Hedge Mode
                    )
                    print("Successfully opened long position")
                    time.sleep(10) #add a break for safety
                except Exception as e:
                    print(f"Error in opening long positions when no position is opened : {e}")
                # Closing the position
                try:
                    open_price = binance_futures.fetch_closed_orders('ETH/USDT:USDT')[-1]['average']
                    target_price = open_price + (open_price * 0.01)
                    stop_loss_price = open_price - (open_price * 0.001)  # Stop-Loss price
                    close_amount = float(amount)
                    # A take-profit order
                    binance_futures.create_order(
                        symbol='ETH/USDT:USDT',  # Symbol for the asset
                        side='SELL',                  # Sell to close the long position
                        type='LIMIT',                 # Limit order
                        amount=close_amount,          # Amount to sell
                        price=target_price,           # Target price for the limit order
                        params = {
                            "positionSide": "LONG",  # Specify "LONG" to close the long position
                            "timeInForce": "GTC"     # Good 'til canceled; adjust as necessary
                        }
                    )
                    # A stop-loss order
                    binance_futures.create_order(
                        symbol='ETH/USDT:USDT',  # Symbol for the asset
                        side='SELL',            # Sell to close the long position
                        type='STOP_MARKET',     # Stop market order
                        amount=close_amount,    # Amount to sell
                        params={
                            "positionSide": "LONG",  # Specify "LONG" to close the long position
                            "stopPrice": stop_loss_price,  # Stop price for the order
                        }
                    )
                    time.sleep(10)  # add a break for safety
                except Exception as e:
                    print(f"Error in creating close order for long positions when no position is opened : {e}")
                
        # MANAGING SHORT POSITIONS
        if not short_position_open: #ensure no short position is opened 
            if k[498] < d[498] and last_close < upperband[498] and second_last_close > upperband[497] and k[498] < d[498]:  #normal trading logic
                if (big_upperband[498] - big_last_high) <= 5 : #proceeding if we are at a top on a larger scale
                    try:
                        amount = usdt_balance * 50 / current_price #using half of the capital
                        binance_futures.create_order(
                            symbol='ETH/USDT:USDT',  # Symbol for the asset
                            side='SELL',                        # Sell to open a short position
                            type='MARKET',                      # Market order
                            amount=amount,                      # Amount to sell
                            params={"positionSide": "SHORT"}    # Specify "SHORT" to open the short position
                        )
                        time.sleep(10) #add a break for safety
                    except Exception as e:
                        print(f"Error in opening short positions when no position is opened : {e}")
                    # Closing the position
                    try:
                        open_price = binance_futures.fetch_closed_orders('ETH/USDT:USDT')[-1]['average']
                        target_price = open_price - (open_price * 0.01)
                        stop_loss_price = open_price + (open_price * 0.001)  # Stop-Loss price
                        close_amount = float(amount)
                        # A take-profit order
                        binance_futures.create_order(
                            symbol='ETH/USDT:USDT',      # Symbol for the asset
                            side='BUY',                   # Buy to close the short position
                            type='LIMIT',                 # Limit order
                            amount=close_amount,          # Amount to buy
                            price=target_price,           # Target price for the limit order
                            params = {
                                "positionSide": "SHORT",  # Specify "SHORT" to close the short position
                                "timeInForce": "GTC"      # Good 'til canceled; adjust as necessary
                            }
                        )
                        # A stoploss order
                        binance_futures.create_order(
                            symbol='ETH/USDT:USDT',  # Symbol for the asset
                            side='BUY',             # Buy to close the short position
                            type='STOP_MARKET',     # Stop market order
                            amount=close_amount,    # Amount to buy
                            params={
                                "positionSide": "SHORT",  # Specify "SHORT" to close the short position
                                "stopPrice": stop_loss_price,  # Stop price for the order
                            }
                        )
                        time.sleep(10)  # add a break for safety
                    except Exception as e:
                        print(f"Error in creating close order for short positions when no position is opened : {e}")
    elif total_usdt_balance > 200:
        pass
    
            


#General Function
def main():
    # initial_transfer()
    
    while True:
        try: 
            manage_futures_positions_and_balance()
            time.sleep(5)  # Main loop delay
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(10)  # Wait for 10 seconds before retrying

#CALLING THE GENERAL FUNCTION
main()