"""
Webull API Client wrapper
Abstracts Webull API interactions with error handling and retry logic
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Position data"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    pnl: float
    pnl_percent: float


@dataclass
class Order:
    """Order data"""
    order_id: str
    symbol: str
    side: str  # BUY or SELL
    quantity: float
    order_price: float
    order_type: str  # MARKET, LIMIT, etc
    status: str  # PENDING, FILLED, CANCELLED, etc
    filled_quantity: float
    timestamp: datetime


class WebullClient:
    """
    Webull API client with error handling and retry logic
    
    This is a wrapper around the webull-api library that provides
    simplified methods for common trading operations.
    """
    
    def __init__(self, username: str, password: str, did: str, trading_pin: str, max_retries: int = 3):
        """
        Initialize Webull client
        
        Args:
            username: Webull username/email
            password: Webull password
            did: Device ID
            trading_pin: Trading PIN
            max_retries: Max API call retries on failure
        """
        self.username = username
        self.password = password
        self.did = did
        self.trading_pin = trading_pin
        self.max_retries = max_retries
        
        # Try to import webull-api
        try:
            from webull import webull
            self.wb = webull(did)
            self._is_connected = False
        except ImportError:
            logger.warning("webull-api library not found. Install with: pip install webull-api")
            self.wb = None
            self._is_connected = False
        
        self._last_api_call = 0
        self._api_rate_limit = 1.0  # Min seconds between API calls
    
    def connect(self) -> bool:
        """
        Connect to Webull and authenticate
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.wb:
            logger.error("Webull client not initialized. Install webull-api library.")
            return False
        
        try:
            # Login
            login_result = self.wb.login(self.username, self.password)
            if not login_result:
                logger.error("Webull login failed")
                return False
            
            logger.info("Webull login successful")
            
            # Get trading permissions (if needed)
            # self.wb.get_account()
            
            self._is_connected = True
            return True
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            return False
    
    def is_connected(self) -> bool:
        """Check if connected to Webull"""
        return self._is_connected
    
    def _rate_limit(self):
        """Rate limiting for API calls"""
        elapsed = time.time() - self._last_api_call
        if elapsed < self._api_rate_limit:
            time.sleep(self._api_rate_limit - elapsed)
        self._last_api_call = time.time()
    
    def _call_with_retry(self, func, *args, **kwargs) -> Any:
        """
        Call API function with retry logic
        
        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Function result or None if all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                self._rate_limit()
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"API call failed (attempt {attempt + 1}): {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API call failed after {self.max_retries} attempts: {e}", exc_info=True)
                    return None
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get account information
        
        Returns:
            Dictionary with account info or None
        """
        if not self._is_connected:
            logger.error("Not connected to Webull")
            return None
        
        try:
            account = self._call_with_retry(self.wb.get_account)
            if account:
                logger.debug(f"Account info retrieved: {account}")
            return account
        except Exception as e:
            logger.error(f"Error getting account info: {e}", exc_info=True)
            return None
    
    def get_account_balance(self) -> Optional[Dict[str, float]]:
        """
        Get account balance
        
        Returns:
            Dictionary with balance info {'cash': float, 'total_value': float, ...}
        """
        if not self._is_connected:
            logger.error("Not connected to Webull")
            return None
        
        try:
            account = self._call_with_retry(self.wb.get_account)
            if account:
                return {
                    'cash': float(account.get('cash', 0)),
                    'total_value': float(account.get('totalValue', 0)),
                    'buying_power': float(account.get('buyingPower', 0)),
                }
            return None
        except Exception as e:
            logger.error(f"Error getting balance: {e}", exc_info=True)
            return None
    
    def get_positions(self) -> Optional[List[Position]]:
        """
        Get current positions
        
        Returns:
            List of Position objects or None
        """
        if not self._is_connected:
            logger.error("Not connected to Webull")
            return None
        
        try:
            positions_data = self._call_with_retry(self.wb.get_positions)
            if not positions_data:
                return []
            
            positions = []
            for pos in positions_data:
                try:
                    position = Position(
                        symbol=pos.get('symbol', 'UNKNOWN'),
                        quantity=float(pos.get('quantity', 0)),
                        entry_price=float(pos.get('costPrice', 0)),
                        current_price=float(pos.get('lastPrice', 0)),
                        pnl=float(pos.get('unrealizedPL', 0)),
                        pnl_percent=float(pos.get('unrealizedPLPercent', 0)),
                    )
                    positions.append(position)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error parsing position: {e}")
                    continue
            
            logger.debug(f"Retrieved {len(positions)} positions")
            return positions
        except Exception as e:
            logger.error(f"Error getting positions: {e}", exc_info=True)
            return None
    
    def get_stock_price(self, symbol: str) -> Optional[float]:
        """
        Get current stock price
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
        
        Returns:
            Current price or None
        """
        if not self._is_connected:
            logger.error("Not connected to Webull")
            return None
        
        try:
            quote = self._call_with_retry(self.wb.get_quote, symbol)
            if quote and 'lastPrice' in quote:
                price = float(quote['lastPrice'])
                logger.debug(f"{symbol}: ${price}")
                return price
            return None
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}", exc_info=True)
            return None
    
    def get_option_price(self, symbol: str, strike: float, expiration: str, option_type: str = 'CALL') -> Optional[float]:
        """
        Get option price
        
        Args:
            symbol: Stock symbol
            strike: Strike price
            expiration: Expiration date (YYYY-MM-DD)
            option_type: CALL or PUT
        
        Returns:
            Option price or None
        """
        if not self._is_connected:
            logger.error("Not connected to Webull")
            return None
        
        try:
            # This is a simplified version - actual implementation depends on Webull API
            option_chain = self._call_with_retry(self.wb.get_option_chain, symbol)
            if option_chain:
                # Find matching option
                for exp_date, options in option_chain.items():
                    if exp_date == expiration:
                        for opt in options:
                            if opt.get('strike') == strike and opt.get('optType') == option_type:
                                price = float(opt.get('bid', opt.get('ask', 0)))
                                logger.debug(f"{symbol} {option_type} {strike} {expiration}: ${price}")
                                return price
            return None
        except Exception as e:
            logger.error(f"Error getting option price: {e}", exc_info=True)
            return None
    
    def place_stock_order(self, symbol: str, quantity: int, side: str = 'BUY', 
                         order_type: str = 'MARKET', price: Optional[float] = None) -> Optional[str]:
        """
        Place a stock order
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: BUY or SELL
            order_type: MARKET or LIMIT
            price: Limit price (required for LIMIT orders)
        
        Returns:
            Order ID or None
        """
        if not self._is_connected:
            logger.error("Not connected to Webull")
            return None
        
        try:
            # Validate inputs
            if quantity <= 0:
                logger.error(f"Invalid quantity: {quantity}")
                return None
            
            if side.upper() not in ['BUY', 'SELL']:
                logger.error(f"Invalid side: {side}")
                return None
            
            if order_type == 'LIMIT' and price is None:
                logger.error("Limit price required for LIMIT orders")
                return None
            
            # Place order
            if order_type == 'MARKET':
                order_result = self._call_with_retry(
                    self.wb.place_order,
                    symbol=symbol,
                    quantity=quantity,
                    side=side.upper(),
                    order_type='MKT'
                )
            else:  # LIMIT
                order_result = self._call_with_retry(
                    self.wb.place_order,
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    side=side.upper(),
                    order_type='LMT'
                )
            
            if order_result and 'orderId' in order_result:
                order_id = order_result['orderId']
                logger.info(f"Stock order placed: {side} {quantity} {symbol} - Order ID: {order_id}")
                return str(order_id)
            
            logger.error(f"Failed to place order: {order_result}")
            return None
        except Exception as e:
            logger.error(f"Error placing order: {e}", exc_info=True)
            return None
    
    def place_option_order(self, symbol: str, contracts: int, strike: float, expiration: str,
                          option_type: str = 'CALL', side: str = 'BUY') -> Optional[str]:
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
        if not self._is_connected:
            logger.error("Not connected to Webull")
            return None
        
        try:
            # Validate inputs
            if contracts <= 0:
                logger.error(f"Invalid number of contracts: {contracts}")
                return None
            
            # Place order (simplified - actual implementation varies by API)
            order_result = self._call_with_retry(
                self.wb.place_option_order,
                symbol=symbol,
                quantity=contracts,
                strike=strike,
                expiration=expiration,
                optType=option_type.upper(),
                side=side.upper()
            )
            
            if order_result and 'orderId' in order_result:
                order_id = order_result['orderId']
                logger.info(f"Option order placed: {side} {contracts} {symbol} {option_type} {strike} - Order ID: {order_id}")
                return str(order_id)
            
            logger.error(f"Failed to place option order: {order_result}")
            return None
        except Exception as e:
            logger.error(f"Error placing option order: {e}", exc_info=True)
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            True if successful, False otherwise
        """
        if not self._is_connected:
            logger.error("Not connected to Webull")
            return False
        
        try:
            result = self._call_with_retry(self.wb.cancel_order, order_id)
            if result:
                logger.info(f"Order cancelled: {order_id}")
                return True
            logger.error(f"Failed to cancel order: {order_id}")
            return False
        except Exception as e:
            logger.error(f"Error cancelling order: {e}", exc_info=True)
            return False
    
    def get_order_status(self, order_id: str) -> Optional[Order]:
        """
        Get order status
        
        Args:
            order_id: Order ID
        
        Returns:
            Order object or None
        """
        if not self._is_connected:
            logger.error("Not connected to Webull")
            return None
        
        try:
            order_data = self._call_with_retry(self.wb.get_order, order_id)
            if order_data:
                order = Order(
                    order_id=str(order_data.get('orderId', order_id)),
                    symbol=order_data.get('symbol', 'UNKNOWN'),
                    side=order_data.get('side', 'UNKNOWN'),
                    quantity=float(order_data.get('quantity', 0)),
                    order_price=float(order_data.get('price', 0)),
                    order_type=order_data.get('orderType', 'UNKNOWN'),
                    status=order_data.get('status', 'UNKNOWN'),
                    filled_quantity=float(order_data.get('filledQuantity', 0)),
                    timestamp=datetime.fromisoformat(order_data.get('timestamp', datetime.now().isoformat())),
                )
                return order
            return None
        except Exception as e:
            logger.error(f"Error getting order status: {e}", exc_info=True)
            return None
    
    def disconnect(self):
        """Disconnect from Webull"""
        self._is_connected = False
        logger.info("Disconnected from Webull")
