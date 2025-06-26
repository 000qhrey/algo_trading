import pandas as pd
import numpy as np

def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Minimal feature set:
    * Daily returns
    * RSI
    * MACD
    * Normalised volume
    * 5‑day & 20‑day momentum
    """
    df = df.copy()
    # daily return
    df["ret"] = df["close"].pct_change()
    # RSI (already pre‑computed by strategy.indicators)
    if "rsi" not in df:
        from strategy.indicators import rsi
        df["rsi"] = rsi(df["close"])
    # MACD
    from strategy.indicators import sma
    df["ema12"] = df["close"].ewm(span=12).mean()
    df["ema26"] = df["close"].ewm(span=26).mean()
    df["macd"] = df["ema12"] - df["ema26"]
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    # ─── volume z-score (handles constant volume -> 0) ─────────────
    vol_mean = df["volume"].rolling(20).mean()
    vol_std  = df["volume"].rolling(20).std(ddof=0).replace(0, np.nan)
    df["vol_z"] = ((df["volume"] - vol_mean) / vol_std).fillna(0)
    # momentum
    df["mom5"] = df["close"].pct_change(5)
    df["mom20"] = df["close"].pct_change(20)
    return df.dropna() 