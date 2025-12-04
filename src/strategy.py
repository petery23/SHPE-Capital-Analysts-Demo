import pandas as pd
import numpy as np


def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def generate_signals(data, short_window=20, long_window=50, use_rsi=True, rsi_oversold=35, rsi_overbought=70):
    """
    Generates trading signals using SMA crossover + RSI filter for better entries.

    Strategy improvements:
    - Faster SMAs (20/50) to catch trends earlier
    - RSI filter: Only BUY when RSI < 70 (not overbought)
    - RSI filter: Only SELL when RSI > 30 (not oversold)

    Args:
        data (pd.DataFrame): DataFrame with historical price data.
        short_window (int): Short-term SMA window (default: 20 days).
        long_window (int): Long-term SMA window (default: 50 days).
        use_rsi (bool): Whether to use RSI filtering.
        rsi_oversold (int): RSI level below which is considered oversold.
        rsi_overbought (int): RSI level above which is considered overbought.

    Returns:
        pd.DataFrame or None: DataFrame with signals, or None if insufficient data.
    """
    if len(data) < long_window:
        print(f"\nError: Not enough data. Need {long_window} points, got {len(data)}.")
        return None

    signals = data.copy()
    
    # Calculate moving averages
    signals['short_mavg'] = data['Adj Close'].rolling(window=short_window, min_periods=1).mean()
    signals['long_mavg'] = data['Adj Close'].rolling(window=long_window, min_periods=1).mean()
    
    # Calculate RSI
    signals['rsi'] = calculate_rsi(data['Adj Close'], period=14)

    # Base signal: 1 when short MA > long MA (uptrend)
    signals['signal'] = 0.0
    signals.loc[signals.index[long_window:], 'signal'] = np.where(
        signals['short_mavg'][long_window:] > signals['long_mavg'][long_window:], 
        1.0, 
        0.0
    )

    # Calculate raw position changes
    signals['positions'] = signals['signal'].diff()

    if use_rsi:
        # Filter out bad entries using RSI
        # Don't buy if overbought (RSI > 70)
        overbought_buys = (signals['positions'] == 1.0) & (signals['rsi'] > rsi_overbought)
        signals.loc[overbought_buys, 'positions'] = 0.0
        
        # Don't sell if oversold (RSI < 30) - might bounce back
        oversold_sells = (signals['positions'] == -1.0) & (signals['rsi'] < rsi_oversold)
        signals.loc[oversold_sells, 'positions'] = 0.0

    return signals
