"""
Portfolio Manager for Multi-Stock Trading
==========================================

Manages cash allocation across multiple stocks and tracks overall portfolio performance.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from utils.logger import setup_logger

logger = setup_logger()

@dataclass
class PortfolioConfig:
    initial_cash: float = 1_000_000.0
    commission: float = 0.0005  # 0.05%
    max_position_size: float = 0.25  # Max 25% of portfolio per stock
    min_cash_reserve: float = 0.1   # Keep 10% cash reserve

class PortfolioManager:
    """
    Manages a multi-stock portfolio with proper cash allocation.
    """
    
    def __init__(self, config: PortfolioConfig, stocks: List[str]):
        self.config = config
        self.stocks = stocks
        self.reset()
    
    def reset(self):
        """Reset portfolio to initial state."""
        self.cash = self.config.initial_cash
        self.positions = {stock: 0 for stock in self.stocks}  # shares held
        self.trade_log = []
        self.daily_values = []
        
    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """Calculate total portfolio value given current prices."""
        stock_value = sum(
            self.positions[stock] * prices.get(stock, 0) 
            for stock in self.stocks
        )
        return self.cash + stock_value
    
    def get_available_cash_for_stock(self, current_prices: Dict[str, float]) -> float:
        """
        Calculate how much cash is available for a new position.
        Considers max position size and cash reserve constraints.
        """
        current_portfolio_value = self.get_portfolio_value(current_prices)
        max_allocation = current_portfolio_value * self.config.max_position_size
        min_cash_needed = current_portfolio_value * self.config.min_cash_reserve
        
        available_cash = max(0, self.cash - min_cash_needed)
        return min(available_cash, max_allocation)
    
    def can_buy(self, stock: str, price: float, current_prices: Dict[str, float]) -> Tuple[bool, int]:
        """
        Check if we can buy a stock and return (can_buy, max_quantity).
        """
        # Don't buy if already have position
        if self.positions[stock] > 0:
            return False, 0
            
        available_cash = self.get_available_cash_for_stock(current_prices)
        
        if available_cash < price:
            return False, 0
            
        max_qty = int(available_cash / price)
        return max_qty > 0, max_qty
    
    def can_sell(self, stock: str) -> Tuple[bool, int]:
        """
        Check if we can sell a stock and return (can_sell, quantity).
        """
        qty = self.positions[stock]
        return qty > 0, qty
    
    def execute_buy(self, stock: str, price: float, date: pd.Timestamp, 
                   current_prices: Dict[str, float]) -> bool:
        """
        Execute a buy order if possible.
        Returns True if trade was executed.
        """
        can_buy, max_qty = self.can_buy(stock, price, current_prices)
        
        if not can_buy:
            return False
            
        # Use available quantity
        trade_value = price * max_qty
        commission = trade_value * self.config.commission
        total_cost = trade_value + commission
        
        # Execute trade
        self.cash -= total_cost
        self.positions[stock] += max_qty
        
        # Log trade
        self.trade_log.append({
            'date': date,
            'stock': stock,
            'type': 'BUY',
            'price': price,
            'quantity': max_qty,
            'value': trade_value,
            'commission': commission,
            'cash_after': self.cash
        })
        
        logger.info(f"BUY: {max_qty} shares of {stock} at ₹{price:.2f} (Total: ₹{trade_value:,.0f})")
        return True
    
    def execute_sell(self, stock: str, price: float, date: pd.Timestamp) -> bool:
        """
        Execute a sell order if possible.
        Returns True if trade was executed.
        """
        can_sell, qty = self.can_sell(stock)
        
        if not can_sell:
            return False
            
        trade_value = price * qty
        commission = trade_value * self.config.commission
        total_received = trade_value - commission
        
        # Execute trade
        self.cash += total_received
        self.positions[stock] = 0
        
        # Log trade
        self.trade_log.append({
            'date': date,
            'stock': stock,
            'type': 'SELL',
            'price': price,
            'quantity': qty,
            'value': trade_value,
            'commission': commission,
            'cash_after': self.cash
        })
        
        logger.info(f"SELL: {qty} shares of {stock} at ₹{price:.2f} (Total: ₹{trade_value:,.0f})")
        return True
    
    def update_daily_value(self, date: pd.Timestamp, prices: Dict[str, float]):
        """Record daily portfolio value."""
        portfolio_value = self.get_portfolio_value(prices)
        
        self.daily_values.append({
            'date': date,
            'cash': self.cash,
            'stock_value': portfolio_value - self.cash,
            'total_value': portfolio_value,
            'positions': self.positions.copy()
        })
    
    def get_trades_df(self) -> pd.DataFrame:
        """Return trades as DataFrame."""
        if not self.trade_log:
            return pd.DataFrame(columns=['date', 'stock', 'type', 'price', 'quantity', 'value', 'commission', 'cash_after'])
        return pd.DataFrame(self.trade_log)
    
    def get_daily_values_df(self) -> pd.DataFrame:
        """Return daily portfolio values as DataFrame."""
        if not self.daily_values:
            return pd.DataFrame(columns=['date', 'cash', 'stock_value', 'total_value'])
        return pd.DataFrame(self.daily_values)
    
    def get_summary(self) -> Dict:
        """Get portfolio performance summary."""
        if not self.daily_values:
            return {
                'initial_value': self.config.initial_cash,
                'final_value': self.config.initial_cash,
                'total_return_pct': 0.0,
                'total_trades': 0,
                'current_cash': self.cash,
                'current_positions': sum(1 for pos in self.positions.values() if pos > 0)
            }
            
        initial_value = self.config.initial_cash
        final_value = self.daily_values[-1]['total_value']
        total_return_pct = ((final_value / initial_value) - 1) * 100
        
        return {
            'initial_value': initial_value,
            'final_value': final_value,
            'total_return_pct': total_return_pct,
            'total_trades': len(self.trade_log),
            'current_cash': self.cash,
            'current_positions': sum(1 for pos in self.positions.values() if pos > 0),
            'max_drawdown': self._calculate_max_drawdown()
        }
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown percentage."""
        if len(self.daily_values) < 2:
            return 0.0
            
        values = [day['total_value'] for day in self.daily_values]
        peak = values[0]
        max_drawdown = 0.0
        
        for value in values:
            if value > peak:
                peak = value
            drawdown = ((peak - value) / peak) * 100
            max_drawdown = max(max_drawdown, drawdown)
            
        return max_drawdown 