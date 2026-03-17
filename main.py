"""
Main trading bot orchestrator
Coordinates strategy, execution, and portfolio management
"""

import logging
import signal
import time
import random
from typing import Dict, Optional
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

from bot.config import Config
from bot.logger import get_logger
from bot.api.client import WebullClient
from bot.strategy.signals import SignalGenerator, Signal
from bot.strategy.risk import RiskManager
from bot.execution.executor import OrderExecutor
from bot.execution.paper_trading import PaperTradingExecutor
from bot.portfolio.manager import PortfolioManager

logger = get_logger(__name__)

# Eastern Time zone for market hours
ET = ZoneInfo("America/New_York")


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

        # NOTE: setup_logging() is called by the entry point (main.py) before
        # TradingBot is instantiated. We do NOT call it again here to avoid
        # clearing handlers and losing the caller's log-level override.

        logger.info(f"Initializing TradingBot - Mode: {mode}, Dry Run: {dry_run}")

        # Initialize components
        self.api_client = None
        self.risk_manager = RiskManager(config.config)
        self.executor = None
        self.paper_executor = None
        self.portfolio = PortfolioManager(
            config.get('logging.trades_file', 'logs/trades.csv')
        )

        # --- FIX #1: Per-symbol signal generators ---
        self.signal_generators: Dict[str, SignalGenerator] = {}
        for symbol in config.get_watchlist():
            self.signal_generators[symbol] = SignalGenerator(config.config)

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

        # Tracking
        self.market_prices: Dict[str, float] = {}
        self.symbol_signals: Dict[str, Signal] = {}
        self.last_data_fetch: Optional[datetime] = None
        self.start_time: Optional[datetime] = None

        # --- FIX #4: Paper mode simulated price state ---
        self._sim_prices: Dict[str, float] = {
            'AAPL': 150.00, 'MSFT': 380.00, 'TSLA': 250.00,
            'SPY': 450.00, 'QQQ': 380.00,
        }

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

        # --- FIX #11: Register SIGTERM for graceful shutdown ---
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

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

    def _handle_signal(self, signum, frame) -> None:
        """Handle SIGTERM/SIGINT for graceful shutdown"""
        sig_name = signal.Signals(signum).name
        logger.info(f"Received {sig_name}, shutting down gracefully...")
        self.is_running = False

    def _run_loop(self) -> None:
        """Main trading loop"""
        refresh_interval = self.config.get('indicators.candle_interval', 5) * 60

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

    # --- FIX #3: Use Eastern Time for market hours ---
    def _is_trading_hours(self) -> bool:
        """Check if within trading hours (Eastern Time)"""
        market_config = self.config.get('market', {})
        if not market_config.get('trading_hours_enabled', True):
            return True

        now_et = datetime.now(ET).time()
        start_hour = market_config.get('start_hour', 9)
        end_hour = market_config.get('end_hour', 16)

        return dt_time(start_hour, 30) <= now_et <= dt_time(end_hour, 0)

    def _fetch_market_data(self) -> bool:
        """Fetch current market prices"""
        try:
            watchlist = self.config.get_watchlist()

            for symbol in watchlist:
                try:
                    if self.mode == 'live' and self.api_client:
                        price = self.api_client.get_stock_price(symbol)
                    else:
                        price = self._get_simulated_price(symbol)

                    if price:
                        self.market_prices[symbol] = price
                except Exception as e:
                    logger.warning(f"Error fetching price for {symbol}: {e}")

            self.last_data_fetch = datetime.now()
            return len(self.market_prices) > 0

        except Exception as e:
            logger.error(f"Error fetching market data: {e}", exc_info=True)
            return False

    # --- FIX #4: Random walk so paper mode actually generates signals ---
    def _get_simulated_price(self, symbol: str) -> Optional[float]:
        """
        Get simulated price with random walk for paper trading.
        Prices drift ±0.5% per tick so indicators can generate real signals.
        """
        if symbol not in self._sim_prices:
            logger.warning(f"No simulated price for {symbol}, skipping")
            return None

        current = self._sim_prices[symbol]
        # Random walk: ±0.5% per tick
        pct_change = random.uniform(-0.005, 0.005)
        new_price = round(current * (1 + pct_change), 2)
        self._sim_prices[symbol] = new_price
        return new_price

    # --- FIX #1: Each symbol gets its own SignalGenerator ---
    def _process_signals(self) -> None:
        """Generate and process signals for each symbol independently"""
        watchlist = self.config.get_watchlist()

        for symbol in watchlist:
            if symbol not in self.market_prices:
                continue

            price = self.market_prices[symbol]

            # Get this symbol's dedicated signal generator
            if symbol not in self.signal_generators:
                self.signal_generators[symbol] = SignalGenerator(self.config.config)

            sig_gen = self.signal_generators[symbol]
            sig_gen.add_candle(price)
            signal_val, reason = sig_gen.generate_signal()

            if signal_val != Signal.HOLD:
                logger.info(f"{symbol} - Signal: {signal_val.value} ({reason.value})")
                self.symbol_signals[symbol] = signal_val

            if signal_val == Signal.BUY and self._can_buy(symbol):
                self._execute_buy(symbol, price)
            elif signal_val == Signal.SELL and self._can_sell(symbol):
                self._execute_sell(symbol, price)

    def _can_buy(self, symbol: str) -> bool:
        """Check if can buy a symbol"""
        if self.portfolio.get_position(symbol):
            return False
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

            quantity, sizing_details = self.risk_manager.calculate_position_size(
                price, account_balance, asset_type='stock'
            )

            if quantity <= 0:
                logger.warning(f"Invalid position size for {symbol}: {quantity}")
                return

            stop_loss = self.risk_manager.calculate_stop_loss(price)
            take_profit = self.risk_manager.calculate_take_profit(price)

            logger.info(f"BUY Signal: {quantity} {symbol} @ ${price:.2f} "
                        f"(SL: ${stop_loss:.2f}, TP: ${take_profit:.2f})")

            if self.mode == 'paper':
                order_id = self.paper_executor.place_market_order(symbol, quantity, 'BUY', price)
            else:
                order_id = self.executor.place_market_order(symbol, quantity, 'BUY')

            if order_id:
                self.portfolio.add_position(symbol, quantity, price, stop_loss, take_profit, order_id)
                logger.info(f"Position opened: {quantity} {symbol}")
            else:
                logger.error(f"Failed to place buy order for {symbol}")

        except Exception as e:
            logger.error(f"Error executing buy for {symbol}: {e}", exc_info=True)

    def _execute_sell(self, symbol: str, price: float) -> None:
        """Execute sell order"""
        try:
            position = self.portfolio.get_position(symbol)
            if not position:
                return

            logger.info(f"SELL Signal: {position.quantity} {symbol} @ ${price:.2f}")

            if self.mode == 'paper':
                order_id = self.paper_executor.place_market_order(symbol, position.quantity, 'SELL', price)
            else:
                order_id = self.executor.place_market_order(symbol, position.quantity, 'SELL')

            if order_id:
                self.portfolio.close_position(symbol, price, reason="SIGNAL")
                self.risk_manager.log_trade(symbol, 'BUY', position.quantity,
                                            position.entry_price, price)
                logger.info(f"Position closed: {symbol}")
            else:
                logger.error(f"Failed to place sell order for {symbol}")

        except Exception as e:
            logger.error(f"Error executing sell for {symbol}: {e}", exc_info=True)

    # --- FIX #2: Exit conditions now place actual sell orders ---
    def _check_exit_conditions(self) -> None:
        """Check for stop losses and take profits, placing real sell orders"""
        # Snapshot the list so we don't modify during iteration
        positions = list(self.portfolio.get_all_positions())

        for position in positions:
            price = self.market_prices.get(position.symbol)
            if not price:
                continue

            reason = None
            if price <= position.stop_loss:
                reason = "STOP_LOSS"
                logger.warning(f"Stop loss hit: {position.symbol} @ ${price:.2f}")
            elif price >= position.take_profit:
                reason = "TAKE_PROFIT"
                logger.info(f"Take profit hit: {position.symbol} @ ${price:.2f}")

            if reason:
                # Place the actual sell order (was missing before!)
                order_id = None
                if self.mode == 'paper':
                    order_id = self.paper_executor.place_market_order(
                        position.symbol, position.quantity, 'SELL', price)
                else:
                    if self.executor:
                        order_id = self.executor.place_market_order(
                            position.symbol, position.quantity, 'SELL')

                if order_id:
                    self.portfolio.close_position(position.symbol, price, reason=reason)
                    self.risk_manager.log_trade(
                        position.symbol, 'BUY', position.quantity,
                        position.entry_price, price)
                else:
                    logger.error(f"Failed to place exit order for {position.symbol} "
                                 f"({reason}) — position still open!")

    def _get_account_balance(self) -> float:
        """Get account balance"""
        if self.mode == 'paper':
            return self.paper_executor.get_portfolio_value()
        else:
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
        if self.start_time:
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
