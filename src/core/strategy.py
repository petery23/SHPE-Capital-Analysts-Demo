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


def calculate_macd(prices, fast=12, slow=26, signal_period=9):
    """Calculate MACD histogram (MACD line minus signal line)."""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    return macd_line - signal_line


def generate_signals(data, short_window=20, long_window=50, use_rsi=True,
                     rsi_oversold=35, rsi_overbought=70):
    """
    Generates trading signals with graded position sizing.

    Uses a three-factor scoring model instead of a binary all-in/all-out approach:

      1. SMA crossover (20/50)  — trend gate: zero exposure in a downtrend
      2. RSI                    — trims size when overbought, holds when healthy
      3. MACD histogram         — adds size when momentum confirms the trend

    Target allocation tiers (fraction of portfolio to hold):
      0.00 — SMA downtrend → no position
      0.33 — uptrend, both RSI overbought AND MACD negative
      0.67 — uptrend + one confirming factor (RSI ok OR MACD positive)
      1.00 — uptrend + RSI healthy + MACD positive → full position

    The 'positions' column marks every meaningful tier change so downstream
    code sees more frequent, graded signals rather than rare binary crossovers:
      +1.0  allocation increased  (scale in / add to position)
      -1.0  allocation decreased  (scale out / trim position)
    """
    if len(data) < long_window:
        print(f"\nError: Not enough data. Need {long_window} points, got {len(data)}.")
        return None

    signals = data.copy()

    # ── Indicators ────────────────────────────────────────────────────────────
    signals['short_mavg'] = data['Adj Close'].rolling(window=short_window, min_periods=1).mean()
    signals['long_mavg']  = data['Adj Close'].rolling(window=long_window,  min_periods=1).mean()
    signals['rsi']        = calculate_rsi(data['Adj Close'], period=14)
    signals['macd_hist']  = calculate_macd(data['Adj Close'])

    # ── Three-factor target allocation ───────────────────────────────────────
    # Gate: SMA uptrend required — no position at all in a downtrend.
    sma_bull = signals['short_mavg'] > signals['long_mavg']

    # RSI factor: healthy momentum range (not overbought)
    rsi_ok   = (signals['rsi'] >= rsi_oversold) & (signals['rsi'] < rsi_overbought)

    # MACD factor: positive momentum (histogram above zero)
    macd_ok  = signals['macd_hist'] > 0

    if use_rsi:
        confirming = rsi_ok.astype(int) + macd_ok.astype(int)   # 0, 1, or 2
    else:
        confirming = macd_ok.astype(int) + 1                    # 1 or 2 (RSI disabled)

    # In uptrend: 33% base + 33% per confirming factor → tiers: 0.33, 0.67, 1.00
    # In downtrend: 0%
    raw_alloc = sma_bull.astype(float) * ((1 + confirming) / 3.0)

    signals['target_alloc'] = 0.0
    signals.loc[signals.index[long_window:], 'target_alloc'] = (
        raw_alloc.iloc[long_window:].values
    )

    # ── Positions column: marks meaningful tier changes for chart + metrics ──
    # A change of ±0.25 catches every valid tier step (minimum step = 0.33).
    alloc_change = signals['target_alloc'].diff().fillna(0)
    signals['positions'] = 0.0
    signals.loc[alloc_change >=  0.25, 'positions'] =  1.0   # scaling in
    signals.loc[alloc_change <= -0.25, 'positions'] = -1.0   # scaling out

    # Keep signal column for backward compatibility
    signals['signal'] = signals['target_alloc']

    return signals
