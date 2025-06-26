"""
Google-Sheets helper 
-------------------------------------------
Relies on gspread.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Sequence, Union

import gspread
import numpy as np
import pandas as pd
from google.oauth2.service_account import Credentials


def _json_safe(x: Union[float, int, str, bool, None]):
    """
    Convert pandas / NumPy / weird objects into plain JSON-serialisable values.
    """
    if pd.isna(x):
        return ""                         # Sheets treats empty string as blank cell
    if isinstance(x, (np.generic,)):      # NumPy scalar
        x = x.item()
    if isinstance(x, (pd.Timestamp, pd.DatetimeIndex)):
        return str(x)
    if isinstance(x, date):  # Handle date objects
        return str(x)
    if hasattr(x, 'date') and callable(getattr(x, 'date')):  # datetime objects
        return str(x)
    if isinstance(x, float) and (math.isinf(x) or math.isnan(x)):
        return ""
    return x


class SheetsClient:
    def __init__(
        self,
        creds_path: str,
        sheet_id: str,
    ):
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        self.gc = gspread.authorize(creds)
        self.sh = self._open_or_create(sheet_id)

    def _open_or_create(self, name_or_id: str):
        """Try to open by ID first, then by name, finally create if needed."""
        try:
            # Try as sheet ID first
            return self.gc.open_by_key(name_or_id)
        except gspread.SpreadsheetNotFound:
            try:
                # Try as sheet name
                return self.gc.open(name_or_id)
            except gspread.SpreadsheetNotFound:
                # Create new sheet
                print(f"Spreadsheet '{name_or_id}' not found. Creating new one...")
                return self.gc.create(name_or_id)

    # ------------------------------------------------------------------ #
    def log_dataframe(
        self,
        df: pd.DataFrame,
        tab_name: str,
        *,
        append: bool = False,
        freeze_header: bool = True,
    ):
        """
        Write `df` to the worksheet named `tab_name`.
        If it doesn't exist, it is created.
        """
        if tab_name not in [ws.title for ws in self.sh.worksheets()]:
            self.sh.add_worksheet(tab_name, rows=1, cols=1)

        ws = self.sh.worksheet(tab_name)

        header = list(df.columns)
        rows: Sequence[Sequence] = (
            df.map(_json_safe).astype(object).values.tolist()
        )

        if append:
            ws.append_rows([header] + rows, value_input_option="USER_ENTERED")
        else:
            ws.clear()
            ws.update([header] + rows, value_input_option="USER_ENTERED")
            
            # Freeze header row for better readability
            if freeze_header:
                try:
                    ws.freeze(rows=1, cols=0)
                except Exception:
                    pass  # Ignore freeze errors
