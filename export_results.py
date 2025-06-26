"""
Export Portfolio Trading Results to Excel
=========================================

Quick script to export the enhanced portfolio results to Excel format
"""

import pandas as pd
import yaml
from pathlib import Path
from data.data_fetcher import fetch_ohlcv
from strategy.rsi_ma_strategy import RSIMAStrategy, RSIMAStrategyConfig
from strategy.portfolio_manager import PortfolioManager, PortfolioConfig

def export_portfolio_results():
    """Export portfolio trading results to Excel"""
    
    # Load config
    cfg = yaml.safe_load(Path("config.yaml").read_text())
    
    print("Fetching data and running portfolio simulation...")
    
    # Fetch data
    data = fetch_ohlcv(
        tickers=cfg["stocks"],
        months=cfg["data"]["lookback_months"],
        interval=cfg["data"]["interval"],
    )
    
    # Initialize portfolio manager
    portfolio_config = PortfolioConfig(
        initial_cash=cfg["backtest"]["initial_cash"],
        commission=cfg["backtest"]["commission"],
        max_position_size=0.25,
        min_cash_reserve=0.1
    )
    
    portfolio = PortfolioManager(portfolio_config, list(data.keys()))
    strategy = RSIMAStrategy(RSIMAStrategyConfig(**cfg["strategy"]))
    
    # Generate signals for all stocks
    all_signals = {}
    for ticker, df in data.items():
        signals_df = strategy.generate_signals(df)
        all_signals[ticker] = signals_df
    
    # Get all unique dates and simulate trading
    all_dates = sorted(set().union(*[df.index for df in all_signals.values()]))
    
    for date in all_dates:
        current_prices = {}
        for ticker, df in all_signals.items():
            if date in df.index:
                current_prices[ticker] = df.loc[date, 'close']
        
        for ticker in current_prices.keys():
            if date in all_signals[ticker].index:
                signals = all_signals[ticker].loc[date]
                price = current_prices[ticker]
                
                if signals['buy']:
                    portfolio.execute_buy(ticker, price, date, current_prices)
                elif signals['sell']:
                    portfolio.execute_sell(ticker, price, date)
        
        if current_prices:
            portfolio.update_daily_value(date, current_prices)
    
    # Get results
    trades_df = portfolio.get_trades_df()
    daily_values_df = portfolio.get_daily_values_df()
    summary = portfolio.get_summary()
    
    # Create portfolio summary
    portfolio_summary = pd.DataFrame([{
        'Metric': 'Initial Portfolio Value',
        'Value': f"₹{summary['initial_value']:,.0f}",
        'Details': 'Starting capital'
    }, {
        'Metric': 'Final Portfolio Value',
        'Value': f"₹{summary['final_value']:,.0f}",
        'Details': f"{summary['total_return_pct']:+.2f}% total return"
    }, {
        'Metric': 'Current Cash',
        'Value': f"₹{summary['current_cash']:,.0f}",
        'Details': f"{(summary['current_cash']/summary['final_value']*100):.1f}% of portfolio"
    }, {
        'Metric': 'Active Positions',
        'Value': f"{summary['current_positions']} stocks",
        'Details': f"Max drawdown: {summary['max_drawdown']:.2f}%"
    }, {
        'Metric': 'Total Trades',
        'Value': f"{summary['total_trades']} trades",
        'Details': 'Buy and sell orders combined'
    }])
    
    # Create stock performance summary
    stock_performance = []
    if not trades_df.empty:
        for ticker in cfg["stocks"]:
            stock_trades = trades_df[trades_df['stock'] == ticker]
            if not stock_trades.empty:
                buys = stock_trades[stock_trades['type'] == 'BUY']
                sells = stock_trades[stock_trades['type'] == 'SELL']
                
                total_invested = buys['value'].sum() if not buys.empty else 0
                total_received = sells['value'].sum() if not sells.empty else 0
                net_pnl = total_received - total_invested
                
                current_position = portfolio.positions.get(ticker, 0)
                
                # Get current price for position valuation
                current_price = 0
                if ticker in data and not data[ticker].empty:
                    current_price = data[ticker]['close'].iloc[-1]
                
                position_value = current_position * current_price
                
                stock_performance.append({
                    'Stock': ticker.replace('.NS', ''),
                    'Current Position': f"{current_position} shares",
                    'Position Value': f"₹{position_value:,.0f}",
                    'Total Invested': f"₹{total_invested:,.0f}",
                    'Total Received': f"₹{total_received:,.0f}",
                    'Realized P&L': f"₹{net_pnl:+,.0f}",
                    'Total Trades': len(stock_trades)
                })
    
    stock_performance_df = pd.DataFrame(stock_performance)
    
    # Format trades for export
    if not trades_df.empty:
        trades_export = trades_df.copy()
        trades_export['date'] = trades_export['date'].dt.date
        trades_export['stock'] = trades_export['stock'].str.replace('.NS', '')
        trades_export['value_formatted'] = trades_export['value'].apply(lambda x: f"₹{x:,.0f}")
        trades_export['commission_formatted'] = trades_export['commission'].apply(lambda x: f"₹{x:.0f}")
        trades_export['cash_after_formatted'] = trades_export['cash_after'].apply(lambda x: f"₹{x:,.0f}")
    
    # Format daily values for export
    if not daily_values_df.empty:
        daily_export = daily_values_df.copy()
        daily_export['date'] = daily_export['date'].dt.date
        daily_export['cash_formatted'] = daily_export['cash'].apply(lambda x: f"₹{x:,.0f}")
        daily_export['stock_value_formatted'] = daily_export['stock_value'].apply(lambda x: f"₹{x:,.0f}")
        daily_export['total_value_formatted'] = daily_export['total_value'].apply(lambda x: f"₹{x:,.0f}")
    
    # Export to Excel
    output_file = "Portfolio_Trading_Results.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Portfolio overview
        portfolio_summary.to_excel(writer, sheet_name='Portfolio_Summary', index=False)
        
        # Stock performance
        if not stock_performance_df.empty:
            stock_performance_df.to_excel(writer, sheet_name='Stock_Performance', index=False)
        
        # All trades
        if not trades_df.empty:
            trades_export[['date', 'stock', 'type', 'price', 'quantity', 'value_formatted', 'commission_formatted', 'cash_after_formatted']].to_excel(
                writer, sheet_name='All_Trades', index=False
            )
        
        # Daily portfolio values (last 30 days)
        if not daily_values_df.empty:
            recent_days = daily_export.tail(30)
            recent_days[['date', 'cash_formatted', 'stock_value_formatted', 'total_value_formatted']].to_excel(
                writer, sheet_name='Recent_Daily_Values', index=False
            )
    
    print(f"\n✅ Results exported to: {output_file}")
    print(f"\n📊 SUMMARY:")
    print(f"   Initial Value: ₹{summary['initial_value']:,.0f}")
    print(f"   Final Value:   ₹{summary['final_value']:,.0f}")
    print(f"   Total Return:  {summary['total_return_pct']:+.2f}%")
    print(f"   Total Trades:  {summary['total_trades']}")
    print(f"   Max Drawdown:  {summary['max_drawdown']:.2f}%")
    print(f"\n📈 The Excel file contains:")
    print(f"   - Portfolio_Summary: Overall performance metrics")
    print(f"   - Stock_Performance: P&L breakdown by stock")
    print(f"   - All_Trades: Complete trading history")
    print(f"   - Recent_Daily_Values: Last 30 days portfolio values")

if __name__ == "__main__":
    export_portfolio_results() 