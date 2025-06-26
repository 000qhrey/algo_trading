import pandas as pd
import numpy as np
from strategy.rsi_ma_strategy import RSIMAStrategy, RSIMAStrategyConfig
from ml_model.model import MovementPredictor

def test_generate_signals_no_errors():
    dates = pd.date_range("2024-01-01", periods=100)
    df = pd.DataFrame(
        {
            "close": range(100, 200),
            "volume": [1_000_000] * 100,
        },
        index=dates,
    )
    strat = RSIMAStrategy(RSIMAStrategyConfig())
    out = strat.generate_signals(df)
    assert "buy" in out.columns
    assert "sell" in out.columns
    assert out["buy"].dtype == bool
    assert out["sell"].dtype == bool

def test_fit_and_predict_next_runs():
    dates = pd.date_range("2024-01-01", periods=300)
    df = pd.DataFrame(
        {
            "close": np.sin(np.linspace(0, 20, 300)).cumsum() * 10 + 500,
            "volume": [1_000_000] * 300,
        },
        index=dates,
    )
    ml = MovementPredictor()
    prob_up, val_acc = ml.fit_and_predict_next(df)
    assert 0.0 <= prob_up <= 1.0
    assert 0.0 <= val_acc <= 1.0 