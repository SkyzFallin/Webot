"""
Portfolio management and position tracking
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass
import csv

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Active position"""
    symbol: str
    quantity: int
    entry_price: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    pnl: float
    pnl_percent: float
    order_id: Optional[str] = None


@dataclass
class ClosedTrade:
    """Closed trade record"""
    symbol: str
    side: str
    quantity: int
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_percent: float
    reason: str  # EXIT_REASON


class PortfolioManager:
    """Manages active positions and trade history"""
    
    def __init__(self, trades_log_file: str = "logs/trades.csv"):
        """
        Initialize portfolio manager
        
        Args:
            trades_log_file: Path to CSV file for trade logging
        """
        self.positions = {}  # {symbol: Position}
        self.closed_trades = []  # List of ClosedTrade
        self.trades_log_file = trades_log_file
        self._init_trades_log()
    
    def _init_trades_log(self) -> None:
        """Initialize trades log file"""
        try:
            with open(self.trades_log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                # Check if file is empty
                f.seek(0, 2)
                if f.tell() == 0:
                    writer.writerow([
                        'timestamp', 'symbol', 'side', 'quantity', 
                        'entry_price', 'exit_price', 'pnl', 'pnl_percent', 'reason'
                    ])
        except Exception as e:
            logger.warning(f"Could not initialize trades log: {e}")
    
    def add_position(self, symbol: str, quantity: int, entry_price: float,
                    stop_loss: float, take_profit: float, 
                    order_id: Optional[str] = None) -> None:
        """
        Add a new position
        
        Args:
            symbol: Stock symbol
            quantity: Position size
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            order_id: Associated order ID
        """
        position = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            entry_time=datetime.now(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            pnl=0,
            pnl_percent=0,
            order_id=order_id,
        )
        
        self.positions[symbol] = position
        logger.info(f"Position added: {quantity} {symbol} @ ${entry_price} (SL: ${stop_loss}, TP: ${take_profit})")
    
    def close_position(self, symbol: str, exit_price: float, reason: str = "MANUAL") -> Optional[ClosedTrade]:
        """
        Close a position
        
        Args:
            symbol: Stock symbol
            exit_price: Exit price
            reason: Close reason (e.g., STOP_LOSS, TAKE_PROFIT, MANUAL)
        
        Returns:
            ClosedTrade object or None
        """
        if symbol not in self.positions:
            logger.warning(f"Position not found: {symbol}")
            return None
        
        pos = self.positions[symbol]
        
        # Calculate P&L
        pnl = (exit_price - pos.entry_price) * pos.quantity
        pnl_percent = ((exit_price - pos.entry_price) / pos.entry_price) * 100
        
        # Create closed trade record
        closed_trade = ClosedTrade(
            symbol=symbol,
            side="BUY",  # Simplified - assumes all are long
            quantity=pos.quantity,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            entry_time=pos.entry_time,
            exit_time=datetime.now(),
            pnl=round(pnl, 2),
            pnl_percent=round(pnl_percent, 2),
            reason=reason,
        )
        
        self.closed_trades.append(closed_trade)
        
        # Log to file
        self._log_trade(closed_trade)
        
        # Remove position
        del self.positions[symbol]
        
        logger.info(f"Position closed: {symbol} @ ${exit_price} - P&L: ${pnl:.2f} ({pnl_percent:.2f}%) - Reason: {reason}")
        
        return closed_trade
    
    def _log_trade(self, trade: ClosedTrade) -> None:
        """Log closed trade to CSV file"""
        try:
            with open(self.trades_log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    trade.symbol,
                    trade.side,
                    trade.quantity,
                    round(trade.entry_price, 2),
                    round(trade.exit_price, 2),
                    trade.pnl,
                    trade.pnl_percent,
                    trade.reason,
                ])
        except Exception as e:
            logger.error(f"Error logging trade: {e}")
    
    def update_position_pnl(self, symbol: str, current_price: float) -> None:
        """
        Update P&L for a position
        
        Args:
            symbol: Stock symbol
            current_price: Current market price
        """
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        pnl = (current_price - pos.entry_price) * pos.quantity
        pnl_percent = ((current_price - pos.entry_price) / pos.entry_price) * 100
        
        pos.pnl = round(pnl, 2)
        pos.pnl_percent = round(pnl_percent, 2)
    
    def update_all_positions(self, prices: Dict[str, float]) -> None:
        """
        Update P&L for all positions
        
        Args:
            prices: Dictionary of {symbol: current_price}
        """
        for symbol, price in prices.items():
            self.update_position_pnl(symbol, price)
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get a specific position"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> List[Position]:
        """Get all open positions"""
        return list(self.positions.values())
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary statistics"""
        positions = self.get_all_positions()
        
        total_invested = sum(pos.quantity * pos.entry_price for pos in positions)
        total_current_value = sum(pos.quantity * (pos.pnl / pos.quantity + pos.entry_price) 
                                 if pos.quantity != 0 else 0 for pos in positions)
        total_unrealized_pnl = sum(pos.pnl for pos in positions)
        
        closed_trades = self.get_closed_trades()
        total_realized_pnl = sum(trade.pnl for trade in closed_trades)
        
        num_winning = sum(1 for trade in closed_trades if trade.pnl > 0)
        num_losing = sum(1 for trade in closed_trades if trade.pnl < 0)
        win_rate = (num_winning / (num_winning + num_losing) * 100) if (num_winning + num_losing) > 0 else 0
        
        return {
            'open_positions': len(positions),
            'total_invested': round(total_invested, 2),
            'total_current_value': round(total_current_value, 2),
            'unrealized_pnl': round(total_unrealized_pnl, 2),
            'realized_pnl': round(total_realized_pnl, 2),
            'total_pnl': round(total_realized_pnl + total_unrealized_pnl, 2),
            'closed_trades': len(closed_trades),
            'winning_trades': num_winning,
            'losing_trades': num_losing,
            'win_rate': round(win_rate, 2),
        }
    
    def get_closed_trades(self) -> List[ClosedTrade]:
        """Get closed trade history"""
        return self.closed_trades.copy()
    
    def check_stop_losses(self, prices: Dict[str, float]) -> List[str]:
        """
        Check which positions hit stop loss
        
        Args:
            prices: Dictionary of {symbol: current_price}
        
        Returns:
            List of symbols that hit stop loss
        """
        stopped_out = []
        for symbol, price in prices.items():
            if symbol in self.positions:
                pos = self.positions[symbol]
                if price <= pos.stop_loss:
                    stopped_out.append(symbol)
                    logger.warning(f"Stop loss hit: {symbol} @ ${price} (SL: ${pos.stop_loss})")
        
        return stopped_out
    
    def check_take_profits(self, prices: Dict[str, float]) -> List[str]:
        """
        Check which positions hit take profit
        
        Args:
            prices: Dictionary of {symbol: current_price}
        
        Returns:
            List of symbols that hit take profit
        """
        taken_profit = []
        for symbol, price in prices.items():
            if symbol in self.positions:
                pos = self.positions[symbol]
                if price >= pos.take_profit:
                    taken_profit.append(symbol)
                    logger.info(f"Take profit hit: {symbol} @ ${price} (TP: ${pos.take_profit})")
        
        return taken_profit
    
    def reset(self) -> None:
        """Reset portfolio (clear all positions and history)"""
        self.positions.clear()
        self.closed_trades.clear()
        logger.info("Portfolio reset")
