"""
Risk management module
Handles position sizing, stop-loss, take-profit, and portfolio risk
"""

import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class RiskParameters:
    """Risk parameters for a trade"""
    entry_price: float
    account_balance: float
    risk_percent: float  # % of account to risk
    stop_loss_percent: float  # % below entry
    take_profit_percent: float  # % above entry
    max_position_percent: float  # Max % of account per position


class RiskManager:
    """Manages position sizing and risk metrics"""
    
    def __init__(self, config: Dict):
        """
        Initialize risk manager
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Get risk settings
        risk_config = config.get('risk', {})
        account_config = config.get('account', {})
        position_config = config.get('position_sizing', {})
        
        self.stop_loss_percent = risk_config.get('stop_loss_percent', 2)
        self.take_profit_percent = risk_config.get('take_profit_percent', 4)
        self.trailing_stop_percent = risk_config.get('trailing_stop_percent', 1.5)
        self.max_concurrent_positions = risk_config.get('max_concurrent_positions', 3)
        
        self.max_position_size_percent = account_config.get('max_position_size_percent', 5)
        self.max_daily_loss_percent = account_config.get('max_daily_loss_percent', 2)
        
        self.position_sizing_method = position_config.get('method', 'risk_based')
        self.fixed_shares = position_config.get('fixed_shares', 10)
        self.risk_per_trade_percent = position_config.get('risk_per_trade_percent', 1)
        
        # Track daily P&L
        self.daily_pnl = 0
        self.daily_trades = []
    
    def calculate_position_size(self, entry_price: float, account_balance: float,
                               asset_type: str = 'stock') -> Tuple[int, Dict]:
        """
        Calculate position size based on risk management rules

        Args:
            entry_price: Entry price for the trade
            account_balance: Current account balance
            asset_type: 'stock' or 'option'

        Returns:
            Tuple of (quantity/contracts, details dict)
        """
        # Guard against bad inputs that would cause division by zero
        if entry_price <= 0 or account_balance <= 0:
            logger.warning(f"Invalid inputs: entry_price={entry_price}, balance={account_balance}")
            return 0, {'quantity': 0, 'position_value': 0, 'position_percent': 0,
                        'risk_amount': 0, 'method': self.position_sizing_method}

        if self.stop_loss_percent <= 0:
            logger.warning(f"stop_loss_percent is {self.stop_loss_percent}, must be > 0")
            return 0, {'quantity': 0, 'position_value': 0, 'position_percent': 0,
                        'risk_amount': 0, 'method': self.position_sizing_method}

        if self.position_sizing_method == 'fixed':
            quantity = self.fixed_shares
            risk_amount = entry_price * quantity * self.stop_loss_percent / 100
        else:  # risk_based
            risk_amount = account_balance * self.risk_per_trade_percent / 100
            risk_per_share = entry_price * self.stop_loss_percent / 100
            quantity = int(risk_amount / risk_per_share)

        # Check against max position size
        position_value = entry_price * quantity
        max_position_value = account_balance * self.max_position_size_percent / 100

        if position_value > max_position_value:
            quantity = int(max_position_value / entry_price)

        # Ensure minimum quantity of 1
        if quantity < 1:
            quantity = 1

        details = {
            'quantity': quantity,
            'position_value': entry_price * quantity,
            'position_percent': (entry_price * quantity) / account_balance * 100,
            'risk_amount': risk_amount,
            'method': self.position_sizing_method,
        }

        return quantity, details
    
    def calculate_stop_loss(self, entry_price: float, 
                           stop_loss_percent: Optional[float] = None) -> float:
        """
        Calculate stop loss price
        
        Args:
            entry_price: Entry price
            stop_loss_percent: Override stop loss % (uses config default if None)
        
        Returns:
            Stop loss price
        """
        sl_percent = stop_loss_percent or self.stop_loss_percent
        stop_loss = entry_price * (1 - sl_percent / 100)
        return round(stop_loss, 2)
    
    def calculate_take_profit(self, entry_price: float,
                             take_profit_percent: Optional[float] = None) -> float:
        """
        Calculate take profit price
        
        Args:
            entry_price: Entry price
            take_profit_percent: Override take profit % (uses config default if None)
        
        Returns:
            Take profit price
        """
        tp_percent = take_profit_percent or self.take_profit_percent
        take_profit = entry_price * (1 + tp_percent / 100)
        return round(take_profit, 2)
    
    def calculate_trailing_stop(self, entry_price: float, current_price: float,
                               previous_highest: Optional[float] = None) -> float:
        """
        Calculate trailing stop price
        
        Args:
            entry_price: Entry price
            current_price: Current price
            previous_highest: Previous highest price (for updating stop)
        
        Returns:
            Updated stop loss price
        """
        highest = max(entry_price, current_price, previous_highest or entry_price)
        trailing_stop = highest * (1 - self.trailing_stop_percent / 100)
        return round(trailing_stop, 2)
    
    def can_open_new_position(self, num_open_positions: int) -> bool:
        """
        Check if a new position can be opened
        
        Args:
            num_open_positions: Number of currently open positions
        
        Returns:
            True if new position allowed, False otherwise
        """
        if num_open_positions >= self.max_concurrent_positions:
            logger.warning(f"Max concurrent positions ({self.max_concurrent_positions}) reached")
            return False
        return True
    
    def check_daily_loss_limit(self, daily_pnl: float, account_balance: float) -> bool:
        """
        Check if daily loss limit has been exceeded
        
        Args:
            daily_pnl: Daily P&L so far
            account_balance: Current account balance
        
        Returns:
            True if trading allowed, False if limit exceeded
        """
        daily_loss_limit = account_balance * self.max_daily_loss_percent / 100
        
        if daily_pnl < -daily_loss_limit:
            logger.warning(f"Daily loss limit exceeded: ${daily_pnl:.2f} < -${daily_loss_limit:.2f}")
            return False
        return True
    
    def calculate_pnl(self, entry_price: float, exit_price: float, quantity: int,
                     side: str = 'BUY') -> Tuple[float, float]:
        """
        Calculate P&L for a trade
        
        Args:
            entry_price: Entry price
            exit_price: Exit price
            quantity: Position size
            side: BUY or SELL
        
        Returns:
            Tuple of (pnl_dollars, pnl_percent)
        """
        if side.upper() == 'BUY':
            pnl_dollars = (exit_price - entry_price) * quantity
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        else:  # SELL
            pnl_dollars = (entry_price - exit_price) * quantity
            pnl_percent = ((entry_price - exit_price) / entry_price) * 100
        
        return round(pnl_dollars, 2), round(pnl_percent, 2)
    
    def log_trade(self, symbol: str, side: str, quantity: int, entry_price: float,
                 exit_price: float) -> None:
        """
        Log a completed trade for daily tracking
        
        Args:
            symbol: Stock symbol
            side: BUY or SELL
            quantity: Position size
            entry_price: Entry price
            exit_price: Exit price
        """
        pnl_dollars, pnl_percent = self.calculate_pnl(entry_price, exit_price, quantity, side)
        
        trade = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_dollars': pnl_dollars,
            'pnl_percent': pnl_percent,
        }
        
        self.daily_trades.append(trade)
        self.daily_pnl += pnl_dollars
        
        logger.info(f"Trade logged: {side} {quantity} {symbol} - P&L: ${pnl_dollars:.2f} ({pnl_percent:.2f}%)")
    
    def get_daily_stats(self) -> Dict:
        """Get daily trading statistics"""
        if not self.daily_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'daily_pnl': 0,
            }
        
        winning = sum(1 for t in self.daily_trades if t['pnl_dollars'] > 0)
        losing = sum(1 for t in self.daily_trades if t['pnl_dollars'] < 0)
        total = len(self.daily_trades)
        
        return {
            'total_trades': total,
            'winning_trades': winning,
            'losing_trades': losing,
            'win_rate': (winning / total * 100) if total > 0 else 0,
            'daily_pnl': self.daily_pnl,
        }
    
    def reset_daily_stats(self) -> None:
        """Reset daily statistics"""
        self.daily_pnl = 0
        self.daily_trades = []
        logger.info("Daily statistics reset")
