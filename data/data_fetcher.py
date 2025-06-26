"""
Centralised market‑data fetcher.

Currently uses yfinance (free ) 
(Alpha Vantage, IEX Cloud, zerodha kiteconnect, etc.)
"""
from datetime import datetime, timedelta
from typing import List

import pandas as pd
import yfinance as yf
from utils.logger import setup_logger

logger = setup_logger()

def fetch_ohlcv(
    tickers: List[str],
    months: int = 6,
    interval: str = "1d",
) -> dict[str, pd.DataFrame]:
    """
    Download OHLCV DataFrame for each ticker over `months` months.
    Returns a dict: {ticker: df}
    """
    end = datetime.utcnow()
    start = end - timedelta(days=months * 30)

    data = {}
    for tkr in tickers:
        logger.info(f"Downloading {tkr} history ({interval}) …")
        try:
            df = yf.download(tkr, start=start, end=end, interval=interval, progress=False)
            if df.empty:
                logger.warning(f"No data for {tkr} (market closed/holiday?); skipping.")
                continue
            
            # Handle MultiIndex columns from yfinance
            if isinstance(df.columns, pd.MultiIndex):
                # Flatten MultiIndex columns - take the first level (price type)
                df.columns = [col[0] for col in df.columns]
            
            # Ensure we have minimum required data
            if len(df) < 30:  # Need at least ~1 month for indicators
                logger.warning(f"Insufficient data for {tkr} ({len(df)} rows); skipping.")
                continue
                
            df.rename(
                columns={
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Adj Close": "adj_close",
                    "Volume": "volume",
                },
                inplace=True,
            )
            df.index.name = "date"
            
            # Basic data validation - use column name after rename
            if "close" in df.columns and df["close"].isna().all():
                logger.warning(f"All close prices are NaN for {tkr}; skipping.")
                continue
                
            data[tkr] = df
            logger.info(f"✓ {tkr}: {len(df)} rows from {df.index[0].date()} to {df.index[-1].date()}")
            
        except Exception as e:
            logger.error(f"Failed to fetch {tkr}: {e}")
            continue
            
    if not data:
        logger.warning("No valid data fetched for any ticker!")
        
    return data 