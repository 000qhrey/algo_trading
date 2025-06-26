# Algo‑Trading System with ML & Automation

*Mini prototype built for the "Algo‑Trading System with ML & Automation" assessment*

---

## 📌 Objective

Develop a self‑contained Python application that

1. **Ingests** free market data for at least 3 NIFTY‑50 stocks.
2. **Generates trade signals** using an RSI + Moving‑Average crossover strategy.
3. **Back‑tests** the idea on \~6 months of history.
4. **Logs** every signal, trade & P/L to **Google Sheets** (JSON‑safe).
5. **(Bonus)** Trains a lightweight **Logistic‑Regression** model to predict the next‑day move and surfaces probabilities.
6. **(Bonus)** Sends **Telegram** alerts + ships with a **cron‑friendly scheduler**.

This repo delivers all mandatory items **plus** a multi‑asset *Portfolio Manager* layer for position sizing 

---

## 🗂️ Project Structure

| Path                                                                           | What it does                                                                               |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| **`main.py`**                                                                  | Orchestrator → fetch data ➜ generate signals ➜ portfolio trade‑sim ➜ ML ➜ Sheets/Telegram. |
| **`schedules/run_daily.py`**                                                   | Minimal cron wrapper (`schedule` lib) – run every day @ 16:00 IST.                         |
| **`sanity.py`**                                                                | Quick standalone demo on a single ticker (UBER) to validate yfinance & indicators.         |
| **`check_status.py`**                                                          | One‑shot health‑check that imports each major module, runs unit tests and prints ✅/❌.      |
| **`export_results.py`**                                                        | Writes a nice Excel workbook summarising portfolio results.                                |
| **`data/`**                                                                    | → **`data_fetcher.py`** (yfinance wrapper).                                                |
| **`strategy/`**                                                                | Pure‑Python TA + trading logic                                                             |
|   • `indicators.py` – RSI, SMA                                                 |                                                                                            |
|   • `rsi_ma_strategy.py` – core rule‑set                                       |                                                                                            |
|   • `backtester.py` – vectorised trade engine                                  |                                                                                            |
|   • `portfolio_manager.py` – *extra*: cash & risk control across many symbols. |                                                                                            |
| **`ml_model/`**                                                                | Feature engineering + `MovementPredictor` (sklearn LR).                                    |
| **`utils/`**                                                                   | Common helpers: logger, Google Sheets client, Telegram.                                    |
| **`tests/`**                                                                   | Tiny pytest suite for smoke coverage.                                                      |

---

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt  # pandas, yfinance, scikit‑learn, gspread, schedule …
```

> **Tip:** All warnings from yfinance & sklearn are silenced inside `main.py` to keep logs clean.

### Configuration

Everything lives in **`config.yaml`**:

## How to Run

```bash
# one‑off back‑test + sheet logging
python main.py

# keep it running every market day after close
python schedules/run_daily.py &
```

On first run the app will create:

* Google‑Sheets tabs, per‑stock tabs with PnL & ML predictions.
* A log file `algo_trading.log` with INFO/DEBUG output.

---

## Trading Logic (RSI ✚ MA)

1. **Indicators** – computed in‑house to avoid TA‑Lib install:

   * `RSI(14)` – classic Wilder.
   * `SMA(20)` & `SMA(50)`.
2. **Buy** if **(RSI < 35)** **OR** *(RSI < 45 & bullish MA crossover)*.
3. **Sell** if **(RSI > 65)** **OR** *(RSI > 55 & bearish crossover)*.

> The threshold “buffer” widens the assignment’s strict 30/70 to generate more trades during a 6‑month window.

Back‑tester walks forward, goes *all‑in* on buy, flat on sell (no shorting), charges flat commission, marks equity MTM daily.

---

## Machine‑Learning Layer 

* Features: returns, RSI, MACD, volume z‑score, 5‑ & 20‑day momentum.
* Model: **Logistic Regression** (sklearn) → predicts prob(next‑day close > today).
* Re‑trained each run on a rolling window; accuracy printed to logs & logged to Sheets.
* Edge‑case: if training split has only one class ➜ safe‑fallback to 50 % probability.

---

## Portfolio Manager (extra)

Although only single‑asset back‑test was required, a full **multi‑stock allocator** was implemented:

* Max 25 % of NAV per ticker, keep 10 % cash reserve.
* Tracks positions, trade log, daily NAV & drawdown.
* Excel exporter & Sheets dashboard included.

---

## 📝  Assumptions 

* *Data* – yfinance daily candles are sufficiently accurate for prototype; 6×30 days ≈ 6 months.
* *Execution* – Orders fill at the **EOD close price** with unlimited liquidity; slippage & taxes ignored.
* *Commission* – Fixed 0.05 % each side – easy to tweak in `config.yaml`.
* *Risk* – No leverage, no short selling; position sizing via simple cash ÷ price.
* *Tickers* – NIFTY symbols need the “.NS” suffix on Yahoo.
* *Time* – Runs at 16:00 IST (market close) – adjust scheduler to taste.
* *G‑Sheets* – Service‑account JSON has edit rights to the spreadsheet.
* *Model* – Logistic‑Regression is chosen for speed & explainability; not meant for production alpha.
* *Security* – Tokens & creds kept in local `config.yaml` / `creds.json` are not committed.

---

## ✅  Testing

```bash
pytest tests/ -q   # 5 basic unit tests pass
```

CI not wired (out of scope) but `check_status.py` offers a fast local sanity sweep.

---

##  Demo Video

![Demo Video](https://youtu.be/p5qeZKriw0M)

---

## Output Files

You can access the following generated files here:

- **output/algo_trading.log**  
  System logs with detailed execution information (generated by `main.py`).

- **output/trading-log.xlsx**  
  Google Sheets logs (generated by `main.py`).  
  Copy of the file is also attached here.
  [View the Google Sheet](https://docs.google.com/spreadsheets/d/1BJi-XT9sL4WTWAOJi-zxbrxhF3FX9mFSLRuoIFO3JkQ/edit?usp=sharing)

- **output/Portfolio_Trading_Results.xlsx**  
  Comprehensive trading results and portfolio analysis (generated by `export_results.py`).

## Closing Remarks
*Thanks for the assignment! I had a lot of fun building this algo-trading system. It was great getting to work with real market data, implement technical indicators, and create a full-stack solution with backtesting, alerts, and dashboards. The project really helped me understand the practical challenges of algorithmic trading while keeping it educational and safe.*


