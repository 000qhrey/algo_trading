# sanity.py -----------------------------------------------------------
"""
Fetch UBER prices with yfinance and build a signal column that your
back-tester can consume.  Signals:
  +1  -> BUY  (short MA above long MA **and** RSI < 30  → oversold up-trend)
  -1  -> SELL (short MA below long MA **and** RSI > 70  → overbought down-trend)
   0  -> stay flat
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import yfinance as yf

TICKER         = "UBER"
START_PERIOD   = "6mo"           # make this ≥ long_window so MAs have room
INTERVAL       = "1d"
SHORT_WINDOW   = 50
LONG_WINDOW    = 200
RSI_PERIOD     = 14
RSI_OVERSOLD   = 30
RSI_OVERBOUGHT = 70

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(message)s",
    force=True,
)
log = logging.getLogger(__name__)


def download_prices(ticker: str,
                    period: str = "6mo",
                    interval: str = "1d") -> pd.Series:
    """Return a *Series* of adjusted close prices."""
    log.debug("Downloading price data for %s …", ticker)
    raw = yf.download(ticker, period=period, interval=interval)["Close"]

    # `raw` is a DataFrame even for one ticker; pick the first column => Series
    close = raw.iloc[:, 0].rename("close")
    close.dropna(inplace=True)
    log.debug("Price series head\n%s", close.head())
    return close


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Plain-vanilla Wilder RSI implementation."""
    delta = series.diff()
    gain  = delta.where(delta > 0, 0.0)
    loss  = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs  = avg_gain / avg_loss
    rsi = 100 - 100 / (1 + rs)
    return rsi


def build_signals(close: pd.Series) -> pd.DataFrame:
    """Return DataFrame with close, rsi, MAs and final signal column."""
    df = close.to_frame()

    df["ma_short"] = df["close"].rolling(SHORT_WINDOW).mean()
    df["ma_long"]  = df["close"].rolling(LONG_WINDOW).mean()
    df["rsi"]      = rsi(df["close"], RSI_PERIOD)

    # Booleans for clarity
    df["up_trend"]   = df["ma_short"] > df["ma_long"]
    df["down_trend"] = ~df["up_trend"]

    # Start with neutral, then set BUY / SELL where conditions meet
    df["signal"] = 0
    df.loc[df["up_trend"]   & (df["rsi"] < RSI_OVERSOLD),   "signal"] = 1
    df.loc[df["down_trend"] & (df["rsi"] > RSI_OVERBOUGHT), "signal"] = -1

    log.debug("Signals head\n%s", df[["close", "rsi", "ma_short",
                                      "ma_long", "signal"]].head(10))
    return df


def main() -> None:
    close = download_prices(TICKER, START_PERIOD, INTERVAL)
    df    = build_signals(close)

    # The back-tester probably needs just ["close", "signal"]
    final = df[["close", "signal"]].dropna()
    log.debug("Final frame shape=%s, head\n%s", final.shape, final.head())

    # (Optional) save to CSV so you can eyeball it
    out = Path("signals_uber.csv")
    final.to_csv(out)
    log.info("Wrote %s", out.resolve())


if __name__ == "__main__":
    main()
