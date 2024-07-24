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
    df['upper_band'], df['middle_band'], df['lower_band'] = ta.BBANDS(
        df['close'], timeperiod=20, nbdevup=2, nbdevdn=2
    )
    print(df['upper_band'], df['middle_band'], df['lower_band'])

    #STOCHASTIC OSILLATOR
    rsi = ta.RSI(df['close'].values, timeperiod=14)
    k, d = ta.STOCH(rsi, rsi, rsi, fastk_period=14, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
    print(k[500],d[500])

df = fetch_OHLCV('1000PEPE/USDT', '5m')
calculate_indicators(df)