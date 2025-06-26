"""
Entrypoint: orchestrates fetch → strategy → portfolio trading → ML → logging → alerts
"""
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

import yaml
from pathlib import Path
import pandas as pd

from data.data_fetcher import fetch_ohlcv
from strategy.rsi_ma_strategy import RSIMAStrategy, RSIMAStrategyConfig
from strategy.portfolio_manager import PortfolioManager, PortfolioConfig
from strategy.backtester import Backtester
from utils.google_sheets import SheetsClient
from utils.telegram_alerts import TelegramAlert
from utils.logger import setup_logger
from ml_model.model import MovementPredictor

cfg = yaml.safe_load(Path("config.yaml").read_text())
logger = setup_logger(cfg["logging"]["level"])

def run_portfolio_backtest(data_dict: dict, cfg: dict) -> tuple:
    """
    Run backtesting using the new portfolio manager for multi-stock trading.
    Returns (portfolio_manager, all_signals_df)
    """
    # Initialize portfolio manager
    portfolio_config = PortfolioConfig(
        initial_cash=cfg["backtest"]["initial_cash"],
        commission=cfg["backtest"]["commission"],
        max_position_size=0.25,  # 25% max per stock
        min_cash_reserve=0.1     # 10% cash reserve
    )
    
    portfolio = PortfolioManager(portfolio_config, list(data_dict.keys()))
    
    # Initialize strategy
    strategy = RSIMAStrategy(RSIMAStrategyConfig(**cfg["strategy"]))
    
    # Generate signals for all stocks
    all_signals = {}
    for ticker, df in data_dict.items():
        signals_df = strategy.generate_signals(df)
        all_signals[ticker] = signals_df
        logger.info(f"Generated signals for {ticker}: {signals_df['buy'].sum()} BUY, {signals_df['sell'].sum()} SELL")
    
    # Get all unique dates
    all_dates = sorted(set().union(*[df.index for df in all_signals.values()]))
    
    # Simulate trading day by day
    for date in all_dates:
        # Get current prices for all stocks
        current_prices = {}
        for ticker, df in all_signals.items():
            if date in df.index:
                current_prices[ticker] = df.loc[date, 'close']
        
        # Process trading signals for this date
        for ticker in current_prices.keys():
            if date in all_signals[ticker].index:
                signals = all_signals[ticker].loc[date]
                price = current_prices[ticker]
                
                # Execute buy signals
                if signals['buy']:
                    portfolio.execute_buy(ticker, price, date, current_prices)
                
                # Execute sell signals
                elif signals['sell']:
                    portfolio.execute_sell(ticker, price, date)
        
        # Update daily portfolio value
        if current_prices:  # Only if we have price data
            portfolio.update_daily_value(date, current_prices)
    
    return portfolio, all_signals

def create_enhanced_dashboard(gs, portfolio: PortfolioManager, tickers: list):
    """Create comprehensive dashboard with portfolio overview."""
    try:
        # Overall portfolio summary
        summary = portfolio.get_summary()
        
        portfolio_summary = pd.DataFrame([{
            'Metric': 'Total Portfolio Value',
            'Value': f"₹{summary['final_value']:,.0f}",
            'Details': f"{summary['total_return_pct']:+.2f}% return"
        }, {
            'Metric': 'Cash Available',
            'Value': f"₹{summary['current_cash']:,.0f}",
            'Details': f"{(summary['current_cash']/summary['final_value']*100):.1f}% of portfolio"
        }, {
            'Metric': 'Active Positions',
            'Value': f"{summary['current_positions']} stocks",
            'Details': f"Max drawdown: {summary['max_drawdown']:.2f}%"
        }, {
            'Metric': 'Total Trades',
            'Value': f"{summary['total_trades']} trades",
            'Details': 'Includes both BUY and SELL'
        }])
        
        gs.log_dataframe(portfolio_summary, "Portfolio_Dashboard", append=False)
        
        # Position details
        trades_df = portfolio.get_trades_df()
        if not trades_df.empty:
            # Summary by stock
            stock_summary = []
            for ticker in tickers:
                stock_trades = trades_df[trades_df['stock'] == ticker]
                if not stock_trades.empty:
                    buys = stock_trades[stock_trades['type'] == 'BUY']
                    sells = stock_trades[stock_trades['type'] == 'SELL']
                    
                    total_invested = buys['value'].sum() if not buys.empty else 0
                    total_received = sells['value'].sum() if not sells.empty else 0
                    net_pnl = total_received - total_invested
                    
                    current_position = portfolio.positions.get(ticker, 0)
                    
                    stock_summary.append({
                        'Stock': ticker,
                        'Current Position': f"{current_position} shares",
                        'Total Invested': f"₹{total_invested:,.0f}",
                        'Total Received': f"₹{total_received:,.0f}",
                        'Net P&L': f"₹{net_pnl:+,.0f}",
                        'Trades': len(stock_trades)
                    })
            
            if stock_summary:
                stock_summary_df = pd.DataFrame(stock_summary)
                gs.log_dataframe(stock_summary_df, "Stock_Performance", append=False)
        
        logger.info("✓ Enhanced dashboard created with portfolio overview")
        
    except Exception as e:
        logger.error(f"Failed to create enhanced dashboard: {e}")

def run():
    # 1) Data
    data = fetch_ohlcv(
        tickers=cfg["stocks"],
        months=cfg["data"]["lookback_months"],
        interval=cfg["data"]["interval"],
    )

    if not data:
        logger.error("No data fetched, aborting run.")
        return

    # Initialize Google Sheets
    gs = SheetsClient(
        creds_path=cfg["google_sheets"]["creds_json"],
        sheet_id=cfg["google_sheets"]["spreadsheet_name"],
    )
    
    tg = None
    if cfg["telegram"]["enabled"]:
        tg = TelegramAlert(
            bot_token=cfg["telegram"]["bot_token"],
            chat_id=cfg["telegram"]["chat_id"],
        )

    # Run enhanced portfolio backtesting
    logger.info("Starting portfolio backtesting...")
    portfolio, all_signals = run_portfolio_backtest(data, cfg)
    
    # Get portfolio results
    trades_df = portfolio.get_trades_df()
    daily_values_df = portfolio.get_daily_values_df()
    summary = portfolio.get_summary()
    
    logger.info(f"Portfolio Results: ₹{summary['final_value']:,.0f} final value ({summary['total_return_pct']:+.2f}% return)")
    logger.info(f"Total trades executed: {summary['total_trades']}")
    
    # Log portfolio-wide results to Google Sheets
    try:
        if not trades_df.empty:
            gs.log_dataframe(trades_df, "All_Trades", append=False)
        
        if not daily_values_df.empty:
            # Format daily values for sheets
            daily_formatted = daily_values_df.copy()
            daily_formatted['date'] = daily_formatted['date'].dt.date.astype(str)
            gs.log_dataframe(daily_formatted[['date', 'cash', 'stock_value', 'total_value']], "Portfolio_Daily_Values", append=False)
        
        # Portfolio summary
        summary_df = pd.DataFrame([summary])
        gs.log_dataframe(summary_df, "Portfolio_Summary", append=False)
        
    except Exception as e:
        logger.error(f"Failed to log portfolio results: {e}")

    # Process individual stock analysis and ML predictions
    processed_tickers = []
    for ticker, df in data.items():
        logger.info(f"Processing ML predictions for {ticker}")

        # Get signals for this stock
        signals_df = all_signals[ticker]

        # ML: fit on data window, predict tomorrow
        try:
            ml = MovementPredictor()
            prob_up, val_acc = ml.fit_and_predict_next(df)
        except Exception as e:
            logger.warning(f"ML prediction failed for {ticker}: {e}")
            prob_up, val_acc = 0.5, 0.0

        direction = "BUY ↑" if prob_up > 0.6 else ("SELL ↓" if prob_up < 0.4 else "HOLD →")
        pred_record = pd.DataFrame(
            {
                "date":   [str(df.index[-1].date())],
                "prob_up": [prob_up],
                "call":   [direction],
                "val_acc": [val_acc],
            }
        )

        # Individual stock backtesting for comparison
        try:
            gs.log_dataframe(pred_record, f"{ticker}_predictions", append=True)

            # Run individual stock backtest for comparison
            bt = Backtester(
                initial_cash=cfg["backtest"]["initial_cash"],
                commission=cfg["backtest"]["commission"]
            )
            
            price_df = df[["open", "high", "low", "close", "volume"]]
            individual_signals_df = signals_df[["buy", "sell"]]
            
            ind_trades_df, ind_pnl_df, ind_summary_df = bt.run(price_df, individual_signals_df)

            gs.log_dataframe(ind_trades_df, f"{ticker}_individual_trades", append=False)
            gs.log_dataframe(ind_summary_df, f"{ticker}_individual_summary", append=False)
            
            # Add date column for PnL
            ind_pnl_with_date = ind_pnl_df.reset_index().rename(columns={"date": "timestamp"})
            ind_pnl_with_date["date"] = ind_pnl_with_date["timestamp"].dt.date.astype(str)
            gs.log_dataframe(ind_pnl_with_date[["date", "equity"]], f"{ticker}_individual_pnl", append=False)
            
            processed_tickers.append(ticker)

        except Exception as e:
            logger.error(f"Failed to process {ticker} individual analysis: {e}")
            continue

        # Telegram alerts
        if tg:
            try:
                # Include portfolio info in telegram message
                current_position = portfolio.positions.get(ticker, 0)
                position_text = f" (Holdings: {current_position} shares)" if current_position > 0 else ""
                
                tg.send(
                    f"{ticker} {direction}{position_text}  •  P(up)={prob_up:.1%}  "
                    f"|  Val Acc {val_acc:.2%}"
                )
            except Exception as e:
                logger.warning(f"Telegram alert failed for {ticker}: {e}")

    # Create enhanced dashboard
    create_enhanced_dashboard(gs, portfolio, processed_tickers)

if __name__ == "__main__":
    run() 