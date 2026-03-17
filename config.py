"""
Configuration loader for the trading bot
Loads from YAML config and environment variables
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for the trading bot"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration from file and environment variables
        
        Args:
            config_file: Path to YAML config file (uses CONFIG_FILE env var if not provided)
        """
        # Load environment variables
        load_dotenv()
        
        # Determine config file path
        if config_file is None:
            config_file = os.getenv('CONFIG_FILE', 'config/trading_config.yaml')
        
        self.config_path = Path(config_file)
        self.config = self._load_config()
        self._apply_env_overrides()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return self._get_defaults()
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            logger.info(f"Loaded config from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading config file: {e}, using defaults", exc_info=True)
            return self._get_defaults()
    
    def _apply_env_overrides(self):
        """Override config with environment variables"""
        # Webull credentials (from environment)
        if 'webull' not in self.config:
            self.config['webull'] = {}
        
        self.config['webull']['username'] = os.getenv('WEBULL_USERNAME')
        self.config['webull']['password'] = os.getenv('WEBULL_PASSWORD')
        self.config['webull']['did'] = os.getenv('WEBULL_DID')
        self.config['webull']['trading_pin'] = os.getenv('WEBULL_TRADING_PIN')
        
        # Trading mode
        if trading_mode := os.getenv('TRADING_MODE'):
            if 'paper_trading' not in self.config:
                self.config['paper_trading'] = {}
            self.config['paper_trading']['enabled'] = trading_mode == 'paper'
        
        # Logging level
        if log_level := os.getenv('LOG_LEVEL'):
            if 'logging' not in self.config:
                self.config['logging'] = {}
            self.config['logging']['level'] = log_level
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            'paper_trading': {
                'enabled': True,
                'initial_balance': 100000,
            },
            'account': {
                'max_position_size_percent': 5,
                'max_daily_loss_percent': 2,
            },
            'watchlist': ['AAPL', 'MSFT', 'TSLA'],
            'indicators': {
                'rsi': {
                    'period': 14,
                    'overbought': 70,
                    'oversold': 30,
                },
                'moving_averages': {
                    'fast_period': 9,
                    'slow_period': 21,
                },
                'candle_interval': 5,
            },
            'signals': {
                'rsi_divergence_enabled': True,
                'ma_crossover_enabled': True,
                'require_volume_confirmation': False,
            },
            'risk': {
                'stop_loss_percent': 2,
                'take_profit_percent': 4,
                'trailing_stop_percent': 1.5,
                'max_concurrent_positions': 3,
            },
            'position_sizing': {
                'method': 'risk_based',
                'fixed_shares': 10,
                'risk_per_trade_percent': 1,
            },
            'market': {
                'trading_hours_enabled': True,
                'start_hour': 9,
                'end_hour': 16,
            },
            'logging': {
                'level': 'INFO',
                'log_file': 'logs/trading.log',
                'trades_file': 'logs/trades.csv',
            },
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports dot notation)"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def get_webull_creds(self) -> Dict[str, str]:
        """Get Webull credentials"""
        return {
            'username': self.get('webull.username'),
            'password': self.get('webull.password'),
            'did': self.get('webull.did'),
            'trading_pin': self.get('webull.trading_pin'),
        }
    
    def is_paper_trading(self) -> bool:
        """Check if paper trading mode is enabled"""
        return self.get('paper_trading.enabled', True)
    
    def get_watchlist(self) -> list:
        """Get list of symbols to watch"""
        return self.get('watchlist', [])
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.get('logging', {})
    
    def __repr__(self) -> str:
        """String representation"""
        return f"<Config from {self.config_path}>"
