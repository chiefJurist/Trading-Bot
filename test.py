import ccxt
import pandas as pd
import talib as ta
import time

# The User's API keys and addresses
SPOT_API_KEY = 'qeSMvIcWC80rj3Ns0pJV2oJzMxt4lLy4C2eXCU05MenQ9ssQLKJcRrRJEzLjGD4k'
SPOT_SECRET_KEY = 'aMXwE79fkF6PnbMzdOemYEMNgbmu2ze9aHUGHmtWBT3VUGnXRCkutZ0T5sQmagXn'
FUTURES_API_KEY = 'ZkUZDQgbuJkk5a1RRODbMpMKcEpcr9Qc81zVD0xmblaPlGbPKwUAA7K9HhvW0aIs'
FUTURES_SECRET_KEY = 'ReliyQQXHqcOZ14d4thxUTtN3Ei6MVHezNMS9ONB8kqIenZdmeLW0s5hjp3JEE2T'

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

#Function For Fetching OHLCV
def fetch_OHLCV(symbol, timeframe):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calculate_indicators(df):
    #BB
    upper_band, middle_band, lower_band = ta.BBANDS(
        df['close'], timeperiod=21, nbdevup=2, nbdevdn=2
    )
    print(upper_band, middle_band, lower_band)
    

    # #STOCHASTIC OSILLATOR
    # rsi = ta.RSI(df['close'].values, timeperiod=14)
    # k, d = ta.STOCH(rsi, rsi, rsi, fastk_period=14, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
    # print(k[499],d[499])

    #EMA 
    # EMA with different periods
    # ema1 = ta.EMA(df['close'], timeperiod=7)
    # ema2 = ta.EMA(df['close'], timeperiod=25)
    # ema3 = ta.EMA(df['close'], timeperiod=99)
    # print(ema1.tail(1), ema3.tail(1), ema3.tail(1))


    # #CCI
    # df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
    # cci = ta.CCI(df['high'], df['low'], df['close'], timeperiod=14)
    # print(cci, 'Last two CCI:', cci.tail(2))

    # # Williams %R
    # wr = ta.WILLR(df['high'], df['low'], df['close'], timeperiod=14)
    # df['WILLR'] = wr
    # print(wr, 'Last two Williams %R:', wr.tail(2))

    # # Momentum (MOM) / Momentum (MTM)
    # momentum = ta.MOM(df['close'], timeperiod=14)
    # df['MOM'] = momentum
    # print(momentum, 'Last two Momentum:', momentum.tail(2))

    # # On-Balance Volume (OBV)
    # obv = ta.OBV(df['close'], df['volume'])
    # df['OBV'] = obv
    # print(obv, 'Last two OBV:', obv.tail(2))

df = fetch_OHLCV('1000PEPE/USDT', '5m')
calculate_indicators(df)

###Orders
# orders = binance_futures.fetch_closed_orders('1000BONK/USDT:USDT')
# print(orders[-1])
# price = float(orders[-1]['info']['avgPrice'])
# target =  price + (price * 0.0055)
# target2 = price - (price * 0.0055)
# print(price, target, target2)

# #Position
# position = binance_futures.fetch_positions_ws('1000BONK/USDT:USDT')
# print(position[-1])