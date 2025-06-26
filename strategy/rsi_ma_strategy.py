from dataclasses import dataclass

import pandas as pd

from strategy.indicators import rsi, sma
from utils.logger import setup_logger

logger = setup_logger()

@dataclass
class RSIMAStrategyConfig:
    rsi_period: int = 14
    fast_ma: int = 20
    slow_ma: int = 50
    buy_rsi: int = 30
    sell_rsi: int = 70

class RSIMAStrategy:
    """
    Enhanced RSI + MA Strategy with more realistic signals:
    
    BUY:  RSI < buy_rsi (30) OR (RSI < 45 AND 20-DMA crosses above 50-DMA)
    SELL: RSI > sell_rsi (70) OR (RSI > 55 AND fast MA crosses below slow MA)
    
    This creates more trading opportunities while maintaining strategy logic.
    """

    def __init__(self, cfg: RSIMAStrategyConfig):
        self.cfg = cfg

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["rsi"] = rsi(df["close"], self.cfg.rsi_period)
        df["ma_fast"] = sma(df["close"], self.cfg.fast_ma)
        df["ma_slow"] = sma(df["close"], self.cfg.slow_ma)
        df["ma_cross"] = df["ma_fast"] > df["ma_slow"]
        df["ma_cross_prev"] = df["ma_cross"].shift(1).fillna(False).infer_objects(copy=False).astype(bool)
        df["bullish_crossover"] = (df["ma_cross"]) & (~df["ma_cross_prev"])
        df["bearish_crossover"] = (~df["ma_cross"]) & (df["ma_cross_prev"])
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Returns df with 'buy' and 'sell' boolean columns.
        Enhanced with more practical trading conditions.
        """
        df = self._compute_indicators(df)

        # REMOVE any pre-existing signal columns to avoid duplicates
        for col in ["signal", "buy", "sell"]:
            if col in df.columns:
                df = df.drop(columns=[col])

        # Enhanced BUY conditions (either condition can trigger)
        buy_cond_1 = df["rsi"] < self.cfg.buy_rsi  # Simple oversold
        buy_cond_2 = (df["rsi"] < 45) & df["bullish_crossover"]  # RSI + MA cross
        buy_cond = buy_cond_1 | buy_cond_2

        # Enhanced SELL conditions (either condition can trigger)
        sell_cond_1 = df["rsi"] > self.cfg.sell_rsi  # Simple overbought
        sell_cond_2 = (df["rsi"] > 55) & df["bearish_crossover"]  # RSI + MA cross
        sell_cond = sell_cond_1 | sell_cond_2

        df["buy"] = buy_cond
        df["sell"] = sell_cond
        
        return df
