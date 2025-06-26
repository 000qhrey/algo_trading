import pandas as pd
from strategy.indicators import rsi, sma

def test_sma():
    s = pd.Series([1, 2, 3, 4, 5])
    assert sma(s, 2).iloc[-1] == 4.5

def test_rsi_shape():
    s = pd.Series(range(1, 100))
    r = rsi(s)
    assert len(r) == len(s) 