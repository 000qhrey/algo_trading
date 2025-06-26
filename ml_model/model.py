from __future__ import annotations

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
import numpy as np

from ml_model.features import make_features
from utils.logger import setup_logger

logger = setup_logger()

class MovementPredictor:
    """
    Binary classification: 1 = next day close > today close, else 0.
    """

    def __init__(self):
        self.clf: LogisticRegression | None = None
        self.feature_cols = []

    def fit(self, df: pd.DataFrame):
        feats = make_features(df)
        feats["target"] = (feats["close"].shift(-1) > feats["close"]).astype(int)
        feats = feats.dropna()
        X = feats.drop(columns=["target", "date"], errors="ignore")
        y = feats["target"]
        self.feature_cols = X.columns.tolist()

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        self.clf = LogisticRegression(max_iter=400, solver="lbfgs", n_jobs=-1)
        self.clf.fit(X_train, y_train)
        y_pred = self.clf.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        logger.info(f"ML model accuracy: {acc:.4f}")
        return acc

    def predict(self, latest_row: pd.Series) -> int:
        if self.clf is None:
            raise ValueError("Call fit() first.")
        X = latest_row[self.feature_cols].values.reshape(1, -1)
        return int(self.clf.predict(X)[0])

    def save(self, path: str = "model.joblib"):
        if self.clf:
            joblib.dump((self.clf, self.feature_cols), path)

    def load(self, path: str = "model.joblib"):
        self.clf, self.feature_cols = joblib.load(path)

    def fit_and_predict_next(self, df: pd.DataFrame) -> tuple[float, float]:
        """
        Fits on df[:-1]   → returns (prob_up, accuracy_on_hold-out)
        Uses df[-1]       → features for tomorrow's prediction.
        """
        feats = make_features(df)
        if len(feats) < 2:
            raise ValueError("Not enough data after feature engineering for prediction.")
        # separate last row
        pred_row = feats.iloc[-1]
        train_df = feats.iloc[:-1]

        # ----- train -----
        X = train_df.drop(columns=["date"], errors="ignore")
        y = (train_df["close"].shift(-1) > train_df["close"]).astype(int).dropna()
        X = X.loc[y.index]             # align indexes

        self.feature_cols = X.columns.tolist()
        # If y has only one unique class we can't train LR – fallback to dummy
        unique_classes = pd.Series(np.ravel(y)).nunique()
        if unique_classes < 2:
            logger.warning("Only one class in training window – using 0.5 prob.")
            return 0.5, 0.0

        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, shuffle=False)

        self.clf = LogisticRegression(max_iter=400, solver="lbfgs", n_jobs=-1)
        self.clf.fit(X_train, y_train)
        val_acc = accuracy_score(y_val, self.clf.predict(X_val))

        # ----- predict tomorrow -----
        prob_up = float(self.clf.predict_proba(
            pred_row[self.feature_cols].values.reshape(1, -1))[0, 1])
        return prob_up, val_acc 