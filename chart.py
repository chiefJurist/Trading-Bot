import ccxt
import pandas as pd
import talib as ta
import time
import math
import numpy as np
import plotly.graph_objects as go

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
    return 

# Function to approximate to 6 significant figures and handle NaN values
def significant_figures_six(x):
    if pd.isna(x) or x == 0:  # Check for NaN or zero
        return np.nan if pd.isna(x) else 0
    else:
        return round(x, 6 - int(math.floor(math.log10(abs(x)))) - 1)
    
# Function to approximate to 4 significant figures and handle NaN values
def significant_figures_four(x):
    if pd.isna(x) or x == 0:  # Check for NaN or zero
        return np.nan if pd.isna(x) else 0
    else:
        return round(x, 4 - int(math.floor(math.log10(abs(x)))) - 1)

#Function For Calculating STOCHF
def calculate_stoch(df):
    #Stochastic Oscillator
    rsi = ta.RSI(df['close'].values, timeperiod=14)
    k, d = ta.STOCH(rsi, rsi, rsi, 
                    fastk_period=14, 
                    slowk_period=3, 
                    slowk_matype=0, 
                    slowd_period=3, 
                    slowd_matype=0)
    k = pd.Series(k).apply(significant_figures_four)
    d = pd.Series(d).apply(significant_figures_four)
    return k, d
    
#Function For Calculating Bollinger Bands
def calculate_bollinger(df, window=20, num_std_dev=0.975):
    # Calculate the moving average (middle band) and round it to 6 significant figures
    middle_band_calc = df['close'].rolling(window=window, min_periods=1).mean()
    middleband = middle_band_calc.apply(significant_figures_six)
    # Calculate the standard deviation and use it to derive the upper and lower bands
    std_dev = df['close'].rolling(window=window, min_periods=1).std()
    # Calculate the upper and lower bands and round them to 6 significant figures
    upperband = (middle_band_calc + (std_dev * num_std_dev)).apply(significant_figures_six)
    lowerband = (middle_band_calc - (std_dev * num_std_dev)) .apply(significant_figures_six)
    
    return upperband, middleband, lowerband

#Fetching ohlcv
df = fetch_OHLCV('ETH/USDT:USDT', '1m')

# Calculate StochF and Bollinger Bands
k, d = calculate_stoch(df)
df['stoch_k'] = k
df['stoch_d'] = d
upperband, middleband, lowerband = calculate_bollinger(df)
df['upperband'] = upperband
df['middleband'] = middleband
df['lowerband'] = lowerband

#Create candlestick chart
candlestick = go.Candlestick(
    x=df['timestamp'],
    open=df['open'],
    high=df['high'],
    low=df['low'],
    close=df['close'],
    increasing_line_color='green',
    decreasing_line_color='red',
    name='Candlesticks'
)

# Add Bollinger Bands
upper_band_trace = go.Scatter(
    x=df['timestamp'],
    y=df['upperband'],
    line=dict(color='gold', width=1),
    name='Upper Band'
)
middle_band_trace = go.Scatter(
    x=df['timestamp'],
    y=df['middleband'],
    line=dict(color='lightpurple', width=1),
    name='Middle Band'
)
lower_band_trace = go.Scatter(
    x=df['timestamp'],
    y=df['lowerband'],
    line=dict(color='darkpurple', width=1),
    name='Lower Band'
)

# Add StochF traces
stoch_k_trace = go.Scatter(
    x=df['timestamp'],
    y=df['stoch_k'],
    line=dict(color='gold', width=1),
    name='Stoch K'
)
stoch_d_trace = go.Scatter(
    x=df['timestamp'],
    y=df['stoch_d'],
    line=dict(color='lightpurple', width=1),
    name='Stoch D'
)

# Add layout for interactivity and axes
fig = go.Figure(data=[
    candlestick, 
    upper_band_trace, 
    middle_band_trace, 
    lower_band_trace, 
    stoch_k_trace,
    stoch_d_trace
])

fig.update_layout(
    title='Candlestick Chart with Bollinger Bands and StochF',
    xaxis_title='Time',
    yaxis_title='Price',
    template='plotly_dark',
    hovermode='x unified'
)

# Show the chart
fig.show()