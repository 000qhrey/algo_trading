"""
Vectorised back-tester with clean pandas

Usage:

bt = Backtester(initial_cash=1_000_000)
trades, pnl, summary = bt.run(price_df, signals_df)

* `price_df`   — must contain a *timezone-naive* datetime index and a `close` column
* `signals_df` — any DataFrame that has boolean `buy` / `sell` columns
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd


def _scalar(x):
    """Return a pure Python scalar from (possibly) pandas / NumPy scalars."""
    if isinstance(x, (pd.Series, pd.Index)):
        x = x.iloc[0]
    if hasattr(x, "item"):             # NumPy scalar
        return x.item()
    return x                            # already plain


@dataclass
class Backtester:
    initial_cash: float = 1_000_000.0
    commission: float = 0.0            # flat commission per trade (optional)

    # internal state – initialised in run()
    _cash: float = 0.0
    _position: int = 0                 # share count we're long (+) or short (–)

    # --------------------------------------------------------------------- #
    def run(
        self,
        price_df: pd.DataFrame,
        signals: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Execute trades, return (trades_df, pnl_df, summary_df)
        ------------------------------------------------------
        * trades_df — one row per execution
        * pnl_df    — equity curve
        * summary_df – one-row overview suitable for Google Sheets
        """
        if not pd.api.types.is_datetime64_any_dtype(price_df.index):
            raise ValueError("price_df index must be datetime64")

        df = price_df.copy()

        # Merge / align signals
        sigs = signals.reindex(df.index, method="ffill").fillna(False)
        df["buy"] = sigs["buy"].astype(bool)
        df["sell"] = sigs["sell"].astype(bool)

        # Preallocate columns
        df["qty"] = 0
        df["cash"] = np.nan
        df["equity"] = np.nan

        # Live state vars
        self._cash = self.initial_cash
        self._position = 0

        executed_trades = []

        for ts, row in df.iterrows():
            px = _scalar(row["close"])

            # entry / exit?
            if row["buy"] and self._position == 0:
                qty = int(self._cash // px)
                if qty:                      # guard against div-0
                    self._execute(
                        executed_trades, ts, "BUY", px, qty
                    )

            elif row["sell"] and self._position > 0:
                self._execute(
                    executed_trades, ts, "SELL", px, self._position
                )

            # Mark-to-market equity
            df.at[ts, "equity"] = self._cash + self._position * px

        # forward-fill equity where we skipped rows
        df = df.copy()  # Ensure we're working with a proper copy
        df["equity"] = df["equity"].ffill()

        trades_df = pd.DataFrame(executed_trades)
        pnl_df = df.loc[:, ["equity"]]

        summary_df = self._build_summary(trades_df, pnl_df)

        return trades_df, pnl_df, summary_df

    # ------------------------------------------------------------------ #
    def _execute(self, book: list, ts, side: str, price: float, qty: int):
        pv = price * qty
        sign = +1 if side == "BUY" else -1

        self._cash -= sign * pv + self.commission          # BUY  -> cash ↓
        self._position += sign * qty                       # SELL -> position ↓

        book.append(
            {
                "date": ts,
                "type": side,
                "price": round(price, 4),
                "qty": qty,
                "cash": round(self._cash, 4),
            }
        )

    # ------------------------------------------------------------------ #
    def _build_summary(
        self, trades: pd.DataFrame, pnl: pd.DataFrame
    ) -> pd.DataFrame:
        if pnl.empty:
            final_nav = self.initial_cash
        else:
            final_nav = _scalar(pnl["equity"].iloc[-1])

        total_return = (final_nav / self.initial_cash - 1.0) * 100.0

        win_ratio = (
            (trades["type"] == "SELL") & (trades["price"].diff() > 0.0)
        ).mean() if not trades.empty else np.nan

        summary = pd.DataFrame(
            {
                "Initial Cash": [self.initial_cash],
                "Final NAV": [round(final_nav, 2)],
                "Total Return %": [round(total_return, 2)],
                "Trades": [len(trades)],
                "Win Ratio": [round(win_ratio, 2) if not np.isnan(win_ratio) else ""],
            }
        )
        return summary
