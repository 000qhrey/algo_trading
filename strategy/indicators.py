"""
Lightweight TA indicators (RSI, SMA) implemented in pure pandas/numpy

"""
import numpy as np
import pandas as pd

def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.rolling(period).mean()
    roll_down = down.rolling(period).mean()
    rs = roll_up / roll_down
    return 100 - (100 / (1 + rs)) 