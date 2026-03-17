"""
Webull Autonomous Trading Bot
Main package initialization
"""

__version__ = "1.0.0"
__author__ = "Trading Bot"

from bot.main import TradingBot
from bot.config import Config

__all__ = ["TradingBot", "Config"]
