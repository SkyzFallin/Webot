"""
Technical indicators for trading signals
Includes: Moving Averages (SMA, EMA), RSI, etc.
"""

import logging
from typing import List, Optional, Tuple
from collections import deque
import math

logger = logging.getLogger(__name__)


class MovingAverages:
    """Moving Average indicators (SMA and EMA)"""
    
    def __init__(self, fast_period: int = 9, slow_period: int = 21):
        """
        Initialize moving average calculator
        
        Args:
            fast_period: Period for fast MA (default 9)
            slow_period: Period for slow MA (default 21)
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        
        self.prices = deque(maxlen=slow_period)
        self.fast_ema = None
        self.slow_ema = None
        self.fast_ema_prev = None
        self.slow_ema_prev = None
    
    def add_price(self, price: float) -> None:
        """
        Add a new price point
        
        Args:
            price: Price to add
        """
        self.prices.append(price)
        self._update_ema()
    
    def _update_ema(self) -> None:
        """Calculate EMA values"""
        if len(self.prices) < self.slow_period:
            return
        
        prices_list = list(self.prices)
        
        # Fast EMA
        self.fast_ema_prev = self.fast_ema
        self.fast_ema = self._calculate_ema(prices_list, self.fast_period)
        
        # Slow EMA
        self.slow_ema_prev = self.slow_ema
        self.slow_ema = self._calculate_ema(prices_list, self.slow_period)
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """
        Calculate EMA
        
        Args:
            prices: List of prices
            period: EMA period
        
        Returns:
            EMA value
        """
        if len(prices) < period:
            return sum(prices) / len(prices)
        
        # Calculate SMA for first value
        sma = sum(prices[:period]) / period
        
        # Calculate EMA using multiplier
        multiplier = 2 / (period + 1)
        ema = sma
        
        for price in prices[period:]:
            ema = price * multiplier + ema * (1 - multiplier)
        
        return ema
    
    def get_fast_ema(self) -> Optional[float]:
        """Get fast EMA value"""
        return self.fast_ema
    
    def get_slow_ema(self) -> Optional[float]:
        """Get slow EMA value"""
        return self.slow_ema
    
    def is_ready(self) -> bool:
        """Check if enough data for calculation"""
        return len(self.prices) >= self.slow_period
    
    def crossover_bullish(self) -> bool:
        """
        Check for bullish crossover (fast MA crosses above slow MA)
        
        Returns:
            True if bullish crossover detected
        """
        if not self.is_ready() or not self.fast_ema_prev or not self.slow_ema_prev:
            return False
        
        return (self.fast_ema_prev <= self.slow_ema_prev and 
                self.fast_ema > self.slow_ema)
    
    def crossover_bearish(self) -> bool:
        """
        Check for bearish crossover (fast MA crosses below slow MA)
        
        Returns:
            True if bearish crossover detected
        """
        if not self.is_ready() or not self.fast_ema_prev or not self.slow_ema_prev:
            return False
        
        return (self.fast_ema_prev >= self.slow_ema_prev and 
                self.fast_ema < self.slow_ema)
    
    def reset(self) -> None:
        """Reset all values"""
        self.prices.clear()
        self.fast_ema = None
        self.slow_ema = None
        self.fast_ema_prev = None
        self.slow_ema_prev = None


class RSI:
    """Relative Strength Index (RSI) indicator"""
    
    def __init__(self, period: int = 14, overbought: int = 70, oversold: int = 30):
        """
        Initialize RSI calculator
        
        Args:
            period: RSI period (default 14)
            overbought: Overbought threshold (default 70)
            oversold: Oversold threshold (default 30)
        """
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        
        self.prices = deque(maxlen=period + 1)
        self.gains = deque(maxlen=period)
        self.losses = deque(maxlen=period)
        self.rsi = None
        self.avg_gain = None
        self.avg_loss = None
    
    def add_price(self, price: float) -> None:
        """
        Add a new price point
        
        Args:
            price: Price to add
        """
        self.prices.append(price)
        
        if len(self.prices) > 1:
            change = price - self.prices[-2]
            if change > 0:
                self.gains.append(change)
                self.losses.append(0)
            else:
                self.gains.append(0)
                self.losses.append(abs(change))
        
        self._update_rsi()
    
    def _update_rsi(self) -> None:
        """Calculate RSI value"""
        if len(self.gains) < self.period:
            return
        
        # Calculate average gain and loss
        avg_gain = sum(self.gains) / self.period
        avg_loss = sum(self.losses) / self.period
        
        self.avg_gain = avg_gain
        self.avg_loss = avg_loss
        
        # Calculate RS and RSI
        if avg_loss == 0:
            self.rsi = 100 if avg_gain > 0 else 50
        else:
            rs = avg_gain / avg_loss
            self.rsi = 100 - (100 / (1 + rs))
    
    def get_rsi(self) -> Optional[float]:
        """Get RSI value"""
        return self.rsi
    
    def is_ready(self) -> bool:
        """Check if enough data for calculation"""
        return len(self.gains) >= self.period
    
    def is_overbought(self) -> bool:
        """Check if RSI is overbought"""
        return self.rsi is not None and self.rsi > self.overbought
    
    def is_oversold(self) -> bool:
        """Check if RSI is oversold"""
        return self.rsi is not None and self.rsi < self.oversold
    
    def reset(self) -> None:
        """Reset all values"""
        self.prices.clear()
        self.gains.clear()
        self.losses.clear()
        self.rsi = None
        self.avg_gain = None
        self.avg_loss = None


class MACD:
    """MACD (Moving Average Convergence Divergence) indicator"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        Initialize MACD calculator
        
        Args:
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period
        """
        self.fast_ma = MovingAverages(fast_period, fast_period)
        self.slow_ma = MovingAverages(slow_period, slow_period)
        self.signal_period = signal_period
        
        self.prices = deque(maxlen=max(slow_period, signal_period))
        self.macd_line = None
        self.signal_line = None
        self.histogram = None
        self.macd_values = deque(maxlen=signal_period)
    
    def add_price(self, price: float) -> None:
        """Add a new price point"""
        self.prices.append(price)
        self.fast_ma.add_price(price)
        self.slow_ma.add_price(price)
        
        if self.fast_ma.get_fast_ema() and self.slow_ma.get_slow_ema():
            self.macd_line = self.fast_ma.get_fast_ema() - self.slow_ma.get_slow_ema()
            self.macd_values.append(self.macd_line)
            
            if len(self.macd_values) >= self.signal_period:
                self.signal_line = sum(self.macd_values) / len(self.macd_values)
                self.histogram = self.macd_line - self.signal_line
    
    def get_macd(self) -> Optional[float]:
        """Get MACD line value"""
        return self.macd_line
    
    def get_signal(self) -> Optional[float]:
        """Get signal line value"""
        return self.signal_line
    
    def get_histogram(self) -> Optional[float]:
        """Get histogram value"""
        return self.histogram
    
    def is_ready(self) -> bool:
        """Check if ready for signals"""
        return self.signal_line is not None
    
    def reset(self) -> None:
        """Reset all values"""
        self.fast_ma.reset()
        self.slow_ma.reset()
        self.prices.clear()
        self.macd_values.clear()
        self.macd_line = None
        self.signal_line = None
        self.histogram = None
