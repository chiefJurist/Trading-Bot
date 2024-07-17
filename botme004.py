import ccxt
import pandas as pd
import talib as ta
import time
import math

# Replace these with your own API keys and addresses
SPOT_API_KEY = 'Io1hIHpNwK2PldQaV45ow3LlUbDW7CqzTnpiyWo3JSOQlm38RLKA0CfDQT0BuOhC'
SPOT_SECRET_KEY = '6bKn0jotdod18Y7fto7gDBVmO0zMMdR5OrhUpIy2f57qm7o4YE0AWAiQFLSa3GbW'
FUTURES_API_KEY = 'fvcNgcglEHAoouBoMn1s4NhlyK90CXs5wcjyi2HJm2fSIQpgCnpZHII6c295iUQM'
FUTURES_SECRET_KEY = 'nsjeRYY6nPxy1cfF07JNU8mhHnxwRB5FO8DHGtfZy9927u26ajnodnaSOLPvK5nV'

ADDRESS_ONE = '0x9D95d4751fCc02157d55527Ca4D50588bCC80590'

# Initialize the Binance Spot exchange
binance_spot = ccxt.binance({
    'apiKey': SPOT_API_KEY,
    'secret': SPOT_SECRET_KEY,
    'options': {
        'defaultType': 'spot'
    }
})

# Initialize the Binance Futures exchange
binance_futures = ccxt.binance({
    'apiKey': FUTURES_API_KEY,
    'secret': FUTURES_SECRET_KEY,
    'options': {
        'defaultType': 'future'
    }
})

def initial_transfer():
    usdt_balance = binance_spot.fetch_balance()['total']['USDT']
    if usdt_balance > 0:
        binance_spot.sapi_post_futures_transfer({
            'asset': 'USDT',
            'amount': usdt_balance,
            'type': 1  # Type 1 means transfer from spot to futures
        })

def check_and_withdraw_spot_balance():
    balance = binance_spot.fetch_balance()
    usdt_balance = balance['total']['USDT']
    
    if usdt_balance > 5000:
        binance_spot.withdraw('USDT', usdt_balance, ADDRESS_ONE, tag=None, params={'network': 'BEP20'})
        time.sleep(10)  # Sleep to ensure the withdrawals are processed

def set_leverage(symbol, leverage):
    # Fetch markets for Binance Futures
    markets = binance_futures.fetch_markets()

    if symbol in markets:
        market_id = markets[symbol]['id']
        binance_futures.fapiPrivate_post_leverage({
            'symbol': market_id,
            'leverage': leverage
        })


def check_and_manage_futures_balance():
    balance = binance_futures.fetch_balance()
    usdt_balance = balance['total']['USDT']
    
    if usdt_balance >= 5000:
        # Close all positions
        positions = binance_futures.private_get_positionrisk()
        for position in positions:
            if float(position['positionAmt']) != 0:
                side = 'sell' if float(position['positionAmt']) > 0 else 'buy'
                binance_futures.create_order(
                    symbol=position['symbol'],
                    type='market',
                    side=side,
                    amount=abs(float(position['positionAmt']))
                )
        
        # Calculate the amount to transfer back to spot
        transfer_amount = usdt_balance - 100
        if transfer_amount > 0:
            binance_futures.sapi_post_futures_transfer({
                'asset': 'USDT',
                'amount': transfer_amount,
                'type': 2  # Type 2 means transfer from futures to spot
            })

    return usdt_balance < 50000

def fetch_ohlcv(symbol, timeframe, limit=500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calculate_stoch_rsi(df):
    stoch_rsi_k, stoch_rsi_d = ta.STOCHRSI(df['close'], timeperiod=14)
    return stoch_rsi_k, stoch_rsi_d

def manage_positions():
    symbol = 'ETH/USDT'
    timeframe = '5m'
    set_leverage(symbol, 10)

    while True:
        usdt_balance = binance_futures.fetch_balance()['total']['USDT']

        # Fetch the OHLCV data
        df = fetch_ohlcv(symbol, timeframe)
        stoch_rsi_k, stoch_rsi_d = calculate_stoch_rsi(df)

        # Check if stoch_rsi_k and stoch_rsi_d have at least one element
        if len(stoch_rsi_k) > 0 and len(stoch_rsi_d) > 0:
            # Check open positions
            positions = binance_futures.private_get_positionrisk()

            open_long = any(float(position['positionAmt']) > 0 for position in positions)
            open_short = any(float(position['positionAmt']) < 0 for position in positions)

            if open_long:
                while open_long:
                    df = fetch_ohlcv(symbol, timeframe)
                    stoch_rsi_k, stoch_rsi_d = calculate_stoch_rsi(df)
                    if stoch_rsi_k[-1] < stoch_rsi_d[-1]:  # Death cross
                        for position in positions:
                            if position['symbol'] == 'ETH/USDT' and float(position['positionAmt']) > 0:
                                binance_futures.create_order(
                                    symbol='ETH/USDT',
                                    type='market',
                                    side='sell',
                                    amount=abs(float(position['positionAmt']))
                                )
                        open_long = False
                    time.sleep(60)  # Check every minute

            elif open_short:
                while open_short:
                    df = fetch_ohlcv(symbol, timeframe)
                    stoch_rsi_k, stoch_rsi_d = calculate_stoch_rsi(df)
                    if stoch_rsi_k[-1] > stoch_rsi_d[-1]:  # Golden cross
                        for position in positions:
                            if position['symbol'] == 'ETH/USDT' and float(position['positionAmt']) < 0:
                                binance_futures.create_order(
                                    symbol='ETH/USDT',
                                    type='market',
                                    side='buy',
                                    amount=abs(float(position['positionAmt']))
                                )
                        open_short = False
                    time.sleep(60)  # Check every minute

            else:
                if usdt_balance >= 50000:
                    transfer_amount = usdt_balance - 100
                    binance_futures.sapi_post_futures_transfer({
                        'asset': 'USDT',
                        'amount': transfer_amount,
                        'type': 2
                    })
                elif usdt_balance > 1:
                    df = fetch_ohlcv(symbol, timeframe)
                    stoch_rsi_k, stoch_rsi_d = calculate_stoch_rsi(df)
                    if stoch_rsi_k[-1] > stoch_rsi_d[-1]:  # Golden cross
                        binance_futures.create_order(
                            symbol='ETH/USDT',
                            type='market',
                            side='buy',
                            amount=math.floor((usdt_balance * 10) / df['close'].iloc[-1])
                        )
                    elif stoch_rsi_k[-1] < stoch_rsi_d[-1]:  # Death cross
                        binance_futures.create_order(
                            symbol='ETH/USDT',
                            type='market',
                            side='sell',
                            amount=math.floor((usdt_balance * 10) / df['close'].iloc[-1])
                        )

            time.sleep(60)  # Check every minute
        else:
            time.sleep(60)  # Wait and retry if stoch_rsi_k or stoch_rsi_d are empty

def main():
    initial_transfer()
    while True:
        check_and_withdraw_spot_balance()
        if check_and_manage_futures_balance():
            manage_positions()
        time.sleep(60)  # Main loop delay

if __name__ == "__main__":
    main()