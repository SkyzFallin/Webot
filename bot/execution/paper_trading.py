"""
Paper trading simulator
Simulates order execution without real money
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum
import random

logger = logging.getLogger(__name__)


class PaperTradingExecutor:
    """Simulates order execution for paper trading"""
    
    def __init__(self, initial_balance: float = 100000):
        """
        Initialize paper trading executor
        
        Args:
            initial_balance: Starting balance for simulated account
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = {}  # {symbol: {'quantity': int, 'entry_price': float, ...}}
        self.orders = {}  # {order_id: order_data}
        self.trade_history = []
        self.order_counter = 0
        self.slippage = 0.001  # 0.1% slippage simulation
    
    def place_market_order(self, symbol: str, quantity: int, side: str, 
                          current_price: float) -> Optional[str]:
        """
        Simulate market order placement
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: BUY or SELL
            current_price: Current market price
        
        Returns:
            Order ID or None
        """
        try:
            # Apply slippage
            if side.upper() == 'BUY':
                execution_price = current_price * (1 + self.slippage)
                cost = execution_price * quantity
                
                if cost > self.balance:
                    logger.warning(f"Insufficient balance for {side} {quantity} {symbol}")
                    return None
                
                self.balance -= cost
            else:  # SELL
                execution_price = current_price * (1 - self.slippage)
                proceeds = execution_price * quantity
                
                if symbol not in self.positions or self.positions[symbol]['quantity'] < quantity:
                    logger.warning(f"Insufficient position for {side} {quantity} {symbol}")
                    return None
                
                self.balance += proceeds
            
            # Create order
            self.order_counter += 1
            order_id = f"PAPER_{self.order_counter}"
            
            order = {
                'order_id': order_id,
                'symbol': symbol,
                'quantity': quantity,
                'side': side.upper(),
                'execution_price': round(execution_price, 2),
                'status': 'FILLED',
                'timestamp': datetime.now(),
                'type': 'MARKET',
            }
            
            self.orders[order_id] = order
            
            # Update positions
            self._update_position(symbol, quantity, side, execution_price)
            
            logger.info(f"Paper order filled: {side} {quantity} {symbol} @ ${execution_price:.2f}")
            return order_id
        except Exception as e:
            logger.error(f"Error placing paper order: {e}")
            return None
    
    def place_limit_order(self, symbol: str, quantity: int, side: str,
                         limit_price: float, current_price: float) -> Optional[str]:
        """
        Simulate limit order placement
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: BUY or SELL
            limit_price: Limit price
            current_price: Current market price
        
        Returns:
            Order ID or None
        """
        try:
            # Check if order would be filled immediately
            would_fill = False
            if side.upper() == 'BUY' and current_price <= limit_price:
                would_fill = True
            elif side.upper() == 'SELL' and current_price >= limit_price:
                would_fill = True
            
            self.order_counter += 1
            order_id = f"PAPER_{self.order_counter}"
            
            if would_fill:
                # Fill immediately at limit price (or better)
                execution_price = min(limit_price, current_price) if side.upper() == 'BUY' else max(limit_price, current_price)
                
                if side.upper() == 'BUY':
                    cost = execution_price * quantity
                    if cost > self.balance:
                        logger.warning(f"Insufficient balance for {side} limit order")
                        return None
                    self.balance -= cost
                else:  # SELL
                    if symbol not in self.positions or self.positions[symbol]['quantity'] < quantity:
                        logger.warning(f"Insufficient position for {side} limit order")
                        return None
                    proceeds = execution_price * quantity
                    self.balance += proceeds
                
                order = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'quantity': quantity,
                    'side': side.upper(),
                    'limit_price': limit_price,
                    'execution_price': execution_price,
                    'status': 'FILLED',
                    'timestamp': datetime.now(),
                    'type': 'LIMIT',
                }
                
                self._update_position(symbol, quantity, side, execution_price)
                logger.info(f"Paper limit order filled: {side} {quantity} {symbol} @ ${execution_price:.2f}")
            else:
                # Order pending
                order = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'quantity': quantity,
                    'side': side.upper(),
                    'limit_price': limit_price,
                    'status': 'PENDING',
                    'timestamp': datetime.now(),
                    'type': 'LIMIT',
                }
                logger.info(f"Paper limit order pending: {side} {quantity} {symbol} @ ${limit_price:.2f}")
            
            self.orders[order_id] = order
            return order_id
        except Exception as e:
            logger.error(f"Error placing paper limit order: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order
        
        Args:
            order_id: Order ID
        
        Returns:
            True if successful
        """
        if order_id not in self.orders:
            logger.warning(f"Order not found: {order_id}")
            return False
        
        order = self.orders[order_id]
        if order['status'] == 'PENDING':
            order['status'] = 'CANCELLED'
            logger.info(f"Paper order cancelled: {order_id}")
            return True
        
        logger.warning(f"Cannot cancel {order['status']} order: {order_id}")
        return False
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get order status"""
        return self.orders.get(order_id)
    
    def update_pending_orders(self, symbol: str, current_price: float) -> None:
        """
        Update pending limit orders based on current price
        
        Args:
            symbol: Stock symbol
            current_price: Current market price
        """
        for order_id, order in list(self.orders.items()):
            if order['status'] != 'PENDING' or order['symbol'] != symbol:
                continue
            
            # Check if limit order should be filled
            should_fill = False
            if order['side'] == 'BUY' and current_price <= order['limit_price']:
                should_fill = True
            elif order['side'] == 'SELL' and current_price >= order['limit_price']:
                should_fill = True
            
            if should_fill:
                execution_price = min(order['limit_price'], current_price) if order['side'] == 'BUY' else max(order['limit_price'], current_price)
                order['execution_price'] = execution_price
                order['status'] = 'FILLED'
                
                # Update position and balance
                if order['side'] == 'BUY':
                    self.balance -= execution_price * order['quantity']
                else:  # SELL
                    self.balance += execution_price * order['quantity']
                
                self._update_position(symbol, order['quantity'], order['side'], execution_price)
                logger.info(f"Paper pending order filled: {order_id}")
    
    def _update_position(self, symbol: str, quantity: int, side: str, price: float) -> None:
        """Update position after order fill"""
        side = side.upper()
        
        if symbol not in self.positions:
            self.positions[symbol] = {
                'quantity': 0,
                'entry_price': 0,
                'current_price': price,
                'pnl': 0,
            }
        
        pos = self.positions[symbol]
        
        if side == 'BUY':
            # Add to position
            total_cost = pos['quantity'] * pos['entry_price'] + quantity * price
            pos['quantity'] += quantity
            pos['entry_price'] = total_cost / pos['quantity'] if pos['quantity'] > 0 else 0
        else:  # SELL
            # Close or reduce position
            pos['quantity'] -= quantity
            if pos['quantity'] < 0:
                # Opened short position
                pos['entry_price'] = price
                pos['quantity'] = abs(pos['quantity'])
        
        pos['current_price'] = price
        self._update_pnl(symbol)
        
        if pos['quantity'] == 0:
            del self.positions[symbol]
    
    def _update_pnl(self, symbol: str) -> None:
        """Update P&L for a position"""
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        pnl = (pos['current_price'] - pos['entry_price']) * pos['quantity']
        pos['pnl'] = round(pnl, 2)
    
    def update_market_prices(self, prices: Dict[str, float]) -> None:
        """
        Update market prices and P&L
        
        Args:
            prices: Dictionary of {symbol: price}
        """
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol]['current_price'] = price
                self._update_pnl(symbol)
    
    def get_balance(self) -> float:
        """Get current cash balance"""
        return round(self.balance, 2)
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        position_value = sum(pos['quantity'] * pos['current_price'] 
                            for pos in self.positions.values())
        return round(self.balance + position_value, 2)
    
    def get_positions(self) -> Dict:
        """Get all open positions"""
        return self.positions.copy()
    
    def get_total_pnl(self) -> float:
        """Get total unrealized P&L"""
        return round(sum(pos['pnl'] for pos in self.positions.values()), 2)
    
    def get_trade_history(self) -> List[Dict]:
        """Get trade history"""
        return self.trade_history.copy()
    
    def get_account_summary(self) -> Dict:
        """Get account summary"""
        portfolio_value = self.get_portfolio_value()
        total_pnl = self.get_total_pnl()
        
        return {
            'initial_balance': self.initial_balance,
            'cash_balance': self.get_balance(),
            'portfolio_value': portfolio_value,
            'unrealized_pnl': total_pnl,
            'unrealized_pnl_percent': (total_pnl / self.initial_balance * 100) if self.initial_balance > 0 else 0,
            'positions': len(self.positions),
            'pending_orders': sum(1 for o in self.orders.values() if o['status'] == 'PENDING'),
        }
    
    def reset(self) -> None:
        """Reset simulator"""
        self.balance = self.initial_balance
        self.positions.clear()
        self.orders.clear()
        self.trade_history.clear()
        self.order_counter = 0
        logger.info("Paper trading simulator reset")
