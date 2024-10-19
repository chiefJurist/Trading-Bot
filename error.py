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
def significant_figures(num):
    # Convert the number to a string to loop through digits
    num_str = str(num)

    # To store the first six digits we care about
    result = []
    found_first_non_zero = False
    
    # Loop through the digits
    for i, digit in enumerate(num_str):
        if digit != '0' and not found_first_non_zero:
            # Found the first non-zero digit, begin collecting digits
            found_first_non_zero = True

        if found_first_non_zero:
            result.append(int(digit))
        
        # Stop once we collect 6 digits
        if len(result) == 6:
            # Now check the 7th digit if it exists
            if i + 1 < len(num_str) and int(num_str[i + 1]) >= 5:
                # Add 1 to the 6th digit if the 7th is 5 or greater
                result[-1] += 1
            break

    # Join the digits back into a single number
    return int(''.join(map(str, result)))

# Example
num = 123456789
print(significant_figures(num))  # Output: 123457


# Function For Calculating Bollinger Bands with rounding to 6 significant figures
def calculate_bollinger_bands(df, window=20, num_std_dev=0.975):
    # Calculate the moving average (middle band) and round it to 6 significant figures
    middle_band_calc = df['close'].rolling(window=window, min_periods=1).mean()
    middle_band = significant_figures(middle_band_calc)

    # Calculate the standard deviation and use it to derive the upper and lower bands
    std_dev = df['close'].rolling(window=window, min_periods=1).std()

    # Calculate the upper and lower bands and round them to 6 significant figures
    upper_band = significant_figures((middle_band_calc + (std_dev * num_std_dev)))
    lower_band = significant_figures((middle_band_calc - (std_dev * num_std_dev))) 

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