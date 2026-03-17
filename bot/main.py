"""
Main trading bot orchestrator
Coordinates strategy, execution, and portfolio management
"""

import logging
import time
from typing import Dict, Optional
from datetime import datetime, time as dt_time
import threading

from bot.config import Config
from bot.logger import setup_logging, get_logger
from bot.api.client import WebullClient
from bot.strategy.signals import SignalGenerator, Signal
from bot.strategy.risk import RiskManager
from bot.execution.executor import OrderExecutor
from bot.execution.paper_trading import PaperTradingExecutor
from bot.portfolio.manager import PortfolioManager

logger = get_logger(__name__)


class TradingBot:
    """Main trading bot class"""
    
    def __init__(self, config: Config, mode: str = 'paper', dry_run: bool = False):
        """
        Initialize trading bot
        
        Args:
            config: Config object
            mode: 'paper' or 'live'
            dry_run: If True, log actions without executing
        """
        self.config = config
        self.mode = mode
        self.dry_run = dry_run
        self.is_running = False
        
        # Setup logging
        logging_config = config.get_logging_config()
        setup_logging(logging_config)
        
        logger.info(f"Initializing TradingBot - Mode: {mode}, Dry Run: {dry_run}")
        
        # Initialize components
        self.api_client = None
        self.signal_generator = None
        self.risk_manager = RiskManager(config.config)
        self.executor = None
        self.paper_executor = None
        self.portfolio = PortfolioManager(
            config.get('logging.trades_file', 'logs/trades.csv')
        )
        
        # Initialize API for live trading
        if mode == 'live':
            creds = config.get_webull_creds()
            if not all(creds.values()):
                raise ValueError("Missing Webull credentials for live trading")
            
            self.api_client = WebullClient(
                username=creds['username'],
                password=creds['password'],
                did=creds['did'],
                trading_pin=creds['trading_pin']
            )
            self.executor = OrderExecutor(self.api_client, dry_run=dry_run)
        
        # Initialize paper trading executor
        if mode == 'paper':
            initial_balance = config.get('paper_trading.initial_balance', 100000)
            self.paper_executor = PaperTradingExecutor(initial_balance)
        
        # Initialize signal generator
        self.signal_generator = SignalGenerator(config.config)
        
        # Tracking
        self.market_prices = {}  # Current prices for all symbols
        self.symbol_signals = {}  # Last signal per symbol
        self.last_data_fetch = None
        self.start_time = None
    
    def start(self) -> None:
        """Start the trading bot"""
        logger.info("=" * 60)
        logger.info("TRADING BOT STARTED")
        logger.info(f"Mode: {self.mode.upper()}")
        logger.info(f"Dry Run: {self.dry_run}")
        logger.info(f"Symbols: {', '.join(self.config.get_watchlist())}")
        logger.info("=" * 60)
        
        self.is_running = True
        self.start_time = datetime.now()
        
        # Connect to Webull if live trading
        if self.mode == 'live' and self.api_client:
            if not self.api_client.connect():
                logger.error("Failed to connect to Webull")
                return
        
        # Start main loop
        self._run_loop()
    
    def stop(self) -> None:
        """Stop the trading bot"""
        logger.info("Stopping trading bot...")
        self.is_running = False
        
        if self.api_client:
            self.api_client.disconnect()
        
        self._print_summary()
        logger.info("Bot stopped")
    
    def _run_loop(self) -> None:
        """Main trading loop"""
        refresh_interval = self.config.get('indicators.candle_interval', 5) * 60  # Convert to seconds
        
        try:
            while self.is_running:
                try:
                    # Check trading hours
                    if not self._is_trading_hours():
                        logger.debug("Market closed, sleeping...")
                        time.sleep(60)
                        continue
                    
                    # Fetch current prices
                    if not self._fetch_market_data():
                        logger.warning("Failed to fetch market data, retrying...")
                        time.sleep(30)
                        continue
                    
                    # Update portfolio P&L
                    self.portfolio.update_all_positions(self.market_prices)
                    
                    # Check risk limits
                    daily_stats = self.risk_manager.get_daily_stats()
                    daily_pnl = daily_stats.get('daily_pnl', 0)
                    account_balance = self._get_account_balance()
                    
                    if not self.risk_manager.check_daily_loss_limit(daily_pnl, account_balance):
                        logger.critical("Daily loss limit exceeded - stopping trading")
                        self.is_running = False
                        break
                    
                    # Check stop losses and take profits
                    self._check_exit_conditions()
                    
                    # Generate signals for each symbol
                    self._process_signals()
                    
                    # Wait for next candle
                    logger.debug(f"Waiting {refresh_interval}s for next candle...")
                    time.sleep(refresh_interval)
                
                except Exception as e:
                    logger.error(f"Error in trading loop: {e}", exc_info=True)
                    time.sleep(30)
        
        except KeyboardInterrupt:
            logger.info("Bot interrupted by user")
        finally:
            self.stop()
    
    def _is_trading_hours(self) -> bool:
        """Check if within trading hours"""
        market_config = self.config.get('market', {})
        if not market_config.get('trading_hours_enabled', True):
            return True
        
        now = datetime.now().time()
        start_hour = market_config.get('start_hour', 9)
        end_hour = market_config.get('end_hour', 16)
        
        return dt_time(start_hour, 30) <= now <= dt_time(end_hour, 0)
    
    def _fetch_market_data(self) -> bool:
        """Fetch current market prices"""
        try:
            watchlist = self.config.get_watchlist()
            
            for symbol in watchlist:
                try:
                    if self.mode == 'live' and self.api_client:
                        price = self.api_client.get_stock_price(symbol)
                    else:
                        # For testing, use simulated prices
                        price = self._get_simulated_price(symbol)
                    
                    if price:
                        self.market_prices[symbol] = price
                except Exception as e:
                    logger.warning(f"Error fetching price for {symbol}: {e}")
            
            self.last_data_fetch = datetime.now()
            return len(self.market_prices) > 0
        
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return False
    
    def _get_simulated_price(self, symbol: str) -> Optional[float]:
        """Get simulated price for testing"""
        # Simplified: return a fixed price (in real implementation, use historical data)
        prices = {
            'AAPL': 150.00,
            'MSFT': 380.00,
            'TSLA': 250.00,
            'SPY': 450.00,
            'QQQ': 380.00,
        }
        return prices.get(symbol)
    
    def _process_signals(self) -> None:
        """Generate and process signals for each symbol"""
        watchlist = self.config.get_watchlist()
        
        for symbol in watchlist:
            if symbol not in self.market_prices:
                continue
            
            price = self.market_prices[symbol]
            
            # Add price to signal generator
            self.signal_generator.add_candle(price)
            
            # Generate signal
            signal, reason = self.signal_generator.generate_signal()
            
            # Log signal
            if signal != Signal.HOLD:
                logger.info(f"{symbol} - Signal: {signal.value} ({reason.value})")
                self.symbol_signals[symbol] = signal
            
            # Execute signal
            if signal == Signal.BUY and self._can_buy(symbol):
                self._execute_buy(symbol, price)
            elif signal == Signal.SELL and self._can_sell(symbol):
                self._execute_sell(symbol, price)
    
    def _can_buy(self, symbol: str) -> bool:
        """Check if can buy a symbol"""
        # Don't buy if already have position
        if self.portfolio.get_position(symbol):
            return False
        
        # Check concurrent positions limit
        num_positions = len(self.portfolio.get_all_positions())
        if not self.risk_manager.can_open_new_position(num_positions):
            return False
        
        return True
    
    def _can_sell(self, symbol: str) -> bool:
        """Check if can sell a symbol"""
        return self.portfolio.get_position(symbol) is not None
    
    def _execute_buy(self, symbol: str, price: float) -> None:
        """Execute buy order"""
        try:
            account_balance = self._get_account_balance()
            
            # Calculate position size
            quantity, sizing_details = self.risk_manager.calculate_position_size(
                price, account_balance, asset_type='stock'
            )
            
            if quantity <= 0:
                logger.warning(f"Invalid position size for {symbol}: {quantity}")
                return
            
            # Calculate risk levels
            stop_loss = self.risk_manager.calculate_stop_loss(price)
            take_profit = self.risk_manager.calculate_take_profit(price)
            
            logger.info(f"BUY Signal: {quantity} {symbol} @ ${price} (SL: ${stop_loss}, TP: ${take_profit})")
            
            # Place order
            if self.mode == 'paper':
                order_id = self.paper_executor.place_market_order(symbol, quantity, 'BUY', price)
            else:  # live
                order_id = self.executor.place_market_order(symbol, quantity, 'BUY')
            
            if order_id:
                # Add position to portfolio
                self.portfolio.add_position(symbol, quantity, price, stop_loss, take_profit, order_id)
                logger.info(f"Position opened: {quantity} {symbol}")
            else:
                logger.error(f"Failed to place buy order for {symbol}")
        
        except Exception as e:
            logger.error(f"Error executing buy for {symbol}: {e}")
    
    def _execute_sell(self, symbol: str, price: float) -> None:
        """Execute sell order"""
        try:
            position = self.portfolio.get_position(symbol)
            if not position:
                return
            
            logger.info(f"SELL Signal: {position.quantity} {symbol} @ ${price}")
            
            # Place order
            if self.mode == 'paper':
                order_id = self.paper_executor.place_market_order(symbol, position.quantity, 'SELL', price)
            else:  # live
                order_id = self.executor.place_market_order(symbol, position.quantity, 'SELL')
            
            if order_id:
                # Close position
                self.portfolio.close_position(symbol, price, reason="SIGNAL")
                logger.info(f"Position closed: {symbol}")
            else:
                logger.error(f"Failed to place sell order for {symbol}")
        
        except Exception as e:
            logger.error(f"Error executing sell for {symbol}: {e}")
    
    def _check_exit_conditions(self) -> None:
        """Check for stop losses and take profits"""
        positions = self.portfolio.get_all_positions()
        
        for position in positions:
            price = self.market_prices.get(position.symbol)
            if not price:
                continue
            
            # Check stop loss
            if price <= position.stop_loss:
                logger.warning(f"Stop loss hit: {position.symbol} @ ${price}")
                self.portfolio.close_position(position.symbol, price, reason="STOP_LOSS")
                self.risk_manager.log_trade(position.symbol, 'BUY', position.quantity, 
                                           position.entry_price, price)
            
            # Check take profit
            elif price >= position.take_profit:
                logger.info(f"Take profit hit: {position.symbol} @ ${price}")
                self.portfolio.close_position(position.symbol, price, reason="TAKE_PROFIT")
                self.risk_manager.log_trade(position.symbol, 'BUY', position.quantity,
                                           position.entry_price, price)
    
    def _get_account_balance(self) -> float:
        """Get account balance"""
        if self.mode == 'paper':
            return self.paper_executor.get_portfolio_value()
        else:  # live
            if self.api_client:
                balance_info = self.api_client.get_account_balance()
                if balance_info:
                    return balance_info['total_value']
        
        return 0
    
    def _print_summary(self) -> None:
        """Print trading summary"""
        summary = self.portfolio.get_portfolio_summary()
        daily_stats = self.risk_manager.get_daily_stats()
        
        logger.info("=" * 60)
        logger.info("TRADING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Session Duration: {datetime.now() - self.start_time}")
        logger.info(f"Open Positions: {summary['open_positions']}")
        logger.info(f"Closed Trades: {summary['closed_trades']}")
        logger.info(f"Unrealized P&L: ${summary['unrealized_pnl']:.2f}")
        logger.info(f"Realized P&L: ${summary['realized_pnl']:.2f}")
        logger.info(f"Total P&L: ${summary['total_pnl']:.2f}")
        logger.info(f"Win Rate: {summary['win_rate']:.2f}%")
        logger.info(f"Daily P&L: ${daily_stats['daily_pnl']:.2f}")
        logger.info("=" * 60)
    
    def get_metrics(self) -> Dict:
        """Get performance metrics"""
        summary = self.portfolio.get_portfolio_summary()
        daily_stats = self.risk_manager.get_daily_stats()
        
        return {
            'open_positions': summary['open_positions'],
            'closed_trades': summary['closed_trades'],
            'total_pnl': summary['total_pnl'],
            'unrealized_pnl': summary['unrealized_pnl'],
            'realized_pnl': summary['realized_pnl'],
            'win_rate': summary['win_rate'],
            'winning_trades': summary['winning_trades'],
            'losing_trades': summary['losing_trades'],
            'daily_pnl': daily_stats['daily_pnl'],
            'daily_trades': daily_stats['total_trades'],
        }
