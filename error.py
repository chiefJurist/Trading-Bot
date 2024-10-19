import ccxt
import pandas as pd
import talib as ta
import numpy as np
import time
import datetime

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


#Function For Fetching OHLCV
def fetch_OHLCV(symbol, timeframe, limit=500):
    bars = binance_futures.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Function to approximate to 6 significant figures and handle NaN values
def round_to_six_sig_figs(value):
    if pd.isna(value):  # Check if the value is NaN
        return np.nan
    if value == 0:
        return 0
    # Calculate the magnitude (order of magnitude)
    magnitude = int(np.floor(np.log10(abs(value))))
    # Normalize the value to the range [1, 10) by dividing by 10^magnitude
    normalized_value = value / 10**magnitude
    # Multiply by 10^6 to retain the first six significant figures
    scaled_value = normalized_value * 10**5
    # Round the scaled value, rounding the 7th digit into the 6th
    rounded_scaled_value = round(scaled_value)
    # Scale back down to the original magnitude and return the rounded value
    return rounded_scaled_value * 10**(magnitude - 6)


# Function For Calculating Bollinger Bands with rounding to 6 significant figures
def calculate_bollinger_bands(df, window=20, num_std_dev=0.975):
    # Calculate the moving average (middle band) and round it to 6 significant figures
    middle_band_calc = df['close'].rolling(window=window, min_periods=1).mean()
    middle_band = middle_band_calc.apply(round_to_six_sig_figs)

    # Calculate the standard deviation and use it to derive the upper and lower bands
    std_dev = df['close'].rolling(window=window, min_periods=1).std()

    # Calculate the upper and lower bands and round them to 6 significant figures
    upper_band = (middle_band_calc + (std_dev * num_std_dev)).apply(round_to_six_sig_figs)
    lower_band = (middle_band_calc - (std_dev * num_std_dev)).apply(round_to_six_sig_figs)

    return upper_band, middle_band, lower_band

# Fetching OHLCV data
df = fetch_OHLCV('BTC/USDT:USDT', '5m')

# Calculating Bollinger Bands with rounding
upper_band, middle_band, lower_band = calculate_bollinger_bands(df)

# Closing Prices of candles
last_close = df['close'].iloc[-2]       # Last candle close
second_last_close = df['close'].iloc[-3] # Second to last candle close
third_last_close = df['close'].iloc[-4] # third to last candle close

# Print Bollinger Band results for the last few candles
print('upperband[498] =', upper_band.iloc[-2])
print('upperband[497] =', upper_band.iloc[-3])
print('upperband[496] =', upper_band.iloc[-4])
print('middleband[498] =', middle_band.iloc[-2])
print('middleband[497] =', middle_band.iloc[-3])
print('middleband[496] =', middle_band.iloc[-4])
print('lowerband[498] =', lower_band.iloc[-2])
print('lowerband[497] =', lower_band.iloc[-3])
print('lowerband[496] =', lower_band.iloc[-4])
print('last_close, second_last_close, third_last_close =', last_close, second_last_close, third_last_close)