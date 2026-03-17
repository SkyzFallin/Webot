"""
Order execution module
Handles placing and managing real orders through Webull API
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum

from bot.api.client import WebullClient

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order statuses"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderExecutor:
    """Manages order placement and execution through Webull API"""
    
    def __init__(self, api_client: WebullClient, dry_run: bool = False):
        """
        Initialize order executor
        
        Args:
            api_client: WebullClient instance
            dry_run: If True, only log orders without actually placing them
        """
        self.client = api_client
        self.dry_run = dry_run
        self.pending_orders = {}  # Track open orders
    
    def place_market_order(self, symbol: str, quantity: int, side: str) -> Optional[str]:
        """
        Place a market order
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: BUY or SELL
        
        Returns:
            Order ID or None
        """
        if self.dry_run:
            order_id = f"DRY_RUN_{datetime.now().timestamp()}"
            logger.info(f"[DRY RUN] Market order: {side} {quantity} {symbol}")
            return order_id
        
        try:
            order_id = self.client.place_stock_order(
                symbol=symbol,
                quantity=quantity,
                side=side,
                order_type='MARKET'
            )
            
            if order_id:
                self.pending_orders[order_id] = {
                    'symbol': symbol,
                    'quantity': quantity,
                    'side': side,
                    'type': OrderType.MARKET.value,
                    'status': OrderStatus.PENDING.value,
                    'timestamp': datetime.now(),
                }
                logger.info(f"Market order placed: {side} {quantity} {symbol} - Order ID: {order_id}")
                return order_id
            return None
        except Exception as e:
            logger.error(f"Error placing market order: {e}", exc_info=True)
            return None
    
    def place_limit_order(self, symbol: str, quantity: int, side: str, 
                         price: float) -> Optional[str]:
        """
        Place a limit order
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: BUY or SELL
            price: Limit price
        
        Returns:
            Order ID or None
        """
        if self.dry_run:
            order_id = f"DRY_RUN_{datetime.now().timestamp()}"
            logger.info(f"[DRY RUN] Limit order: {side} {quantity} {symbol} @ ${price}")
            return order_id
        
        try:
            order_id = self.client.place_stock_order(
                symbol=symbol,
                quantity=quantity,
                side=side,
                order_type='LIMIT',
                price=price
            )
            
            if order_id:
                self.pending_orders[order_id] = {
                    'symbol': symbol,
                    'quantity': quantity,
                    'side': side,
                    'price': price,
                    'type': OrderType.LIMIT.value,
                    'status': OrderStatus.PENDING.value,
                    'timestamp': datetime.now(),
                }
                logger.info(f"Limit order placed: {side} {quantity} {symbol} @ ${price} - Order ID: {order_id}")
                return order_id
            return None
        except Exception as e:
            logger.error(f"Error placing limit order: {e}", exc_info=True)
            return None
    
    def place_option_order(self, symbol: str, contracts: int, strike: float,
                          expiration: str, option_type: str, side: str) -> Optional[str]:
        """
        Place an option order
        
        Args:
            symbol: Stock symbol
            contracts: Number of contracts
            strike: Strike price
            expiration: Expiration date (YYYY-MM-DD)
            option_type: CALL or PUT
            side: BUY or SELL
        
        Returns:
            Order ID or None
        """
        if self.dry_run:
            order_id = f"DRY_RUN_{datetime.now().timestamp()}"
            logger.info(f"[DRY RUN] Option order: {side} {contracts} {symbol} {option_type} ${strike} {expiration}")
            return order_id
        
        try:
            order_id = self.client.place_option_order(
                symbol=symbol,
                contracts=contracts,
                strike=strike,
                expiration=expiration,
                option_type=option_type,
                side=side
            )
            
            if order_id:
                self.pending_orders[order_id] = {
                    'symbol': symbol,
                    'contracts': contracts,
                    'strike': strike,
                    'expiration': expiration,
                    'option_type': option_type,
                    'side': side,
                    'type': 'OPTION',
                    'status': OrderStatus.PENDING.value,
                    'timestamp': datetime.now(),
                }
                logger.info(f"Option order placed: {side} {contracts} {symbol} {option_type} ${strike} - Order ID: {order_id}")
                return order_id
            return None
        except Exception as e:
            logger.error(f"Error placing option order: {e}", exc_info=True)
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Cancel order: {order_id}")
            if order_id in self.pending_orders:
                del self.pending_orders[order_id]
            return True
        
        try:
            result = self.client.cancel_order(order_id)
            if result:
                if order_id in self.pending_orders:
                    self.pending_orders[order_id]['status'] = OrderStatus.CANCELLED.value
                logger.info(f"Order cancelled: {order_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error cancelling order: {e}", exc_info=True)
            return False
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """
        Get order status
        
        Args:
            order_id: Order ID
        
        Returns:
            Order status dictionary or None
        """
        try:
            order = self.client.get_order_status(order_id)
            if order:
                return {
                    'order_id': order.order_id,
                    'symbol': order.symbol,
                    'side': order.side,
                    'quantity': order.quantity,
                    'filled_quantity': order.filled_quantity,
                    'status': order.status,
                    'price': order.order_price,
                    'timestamp': order.timestamp,
                }
            return None
        except Exception as e:
            logger.error(f"Error getting order status: {e}", exc_info=True)
            return None
    
    def get_pending_orders(self) -> List[Dict]:
        """Get all pending orders"""
        return list(self.pending_orders.values())
    
    def update_order_status(self, order_id: str) -> bool:
        """
        Update order status from Webull
        
        Args:
            order_id: Order ID
        
        Returns:
            True if status updated, False otherwise
        """
        status = self.get_order_status(order_id)
        if status and order_id in self.pending_orders:
            self.pending_orders[order_id]['status'] = status['status']
            self.pending_orders[order_id]['filled_quantity'] = status['filled_quantity']
            return True
        return False
    
    def clear_pending_orders(self) -> None:
        """Clear pending orders list"""
        self.pending_orders.clear()
        logger.info("Cleared pending orders")
