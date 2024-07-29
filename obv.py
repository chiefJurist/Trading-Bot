import ccxt
import pandas as pd
import talib
import numpy as np
import datetime

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

def fetch_ohlcv(symbol, timeframe='5m', limit=500):
    ohlcv = binance_futures.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calculate_obv(df):
    # Ensure the data is sorted by timestamp
    df = df.sort_values(by='timestamp')
    
    # Calculate OBV using talib
    obv = talib.OBV(df['close'], df['volume'])
    
    # Add OBV to the DataFrame
    df['OBV'] = obv
    
    return df

def main():
    symbol = '1000PEPE/USDT:USDT'
    timeframe = '5m'
    ohlcv_df = fetch_ohlcv(symbol, timeframe)
    obv_df = calculate_obv(ohlcv_df)
    
    print(obv_df.tail(10))

if __name__ == '__main__':
    main()
