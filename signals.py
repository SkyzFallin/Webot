"""
Signal generation for trading decisions
Combines indicators to generate buy/sell signals
"""

import logging
from typing import Dict, Optional, Tuple
from enum import Enum
from datetime import datetime

from bot.strategy.indicators import MovingAverages, RSI, MACD

logger = logging.getLogger(__name__)


class Signal(Enum):
    """Signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalReason(Enum):
    """Reasons for signal generation"""
    RSI_OVERSOLD = "RSI_OVERSOLD"
    RSI_OVERBOUGHT = "RSI_OVERBOUGHT"
    MA_BULLISH_CROSSOVER = "MA_BULLISH_CROSSOVER"
    MA_BEARISH_CROSSOVER = "MA_BEARISH_CROSSOVER"
    MACD_BULLISH = "MACD_BULLISH"
    MACD_BEARISH = "MACD_BEARISH"
    VOLUME_CONFIRMATION = "VOLUME_CONFIRMATION"
    NONE = "NONE"


class SignalGenerator:
    """Generates trading signals based on technical indicators"""
    
    def __init__(self, config: Dict):
        """
        Initialize signal generator
        
        Args:
            config: Configuration dictionary with indicator settings
        """
        self.config = config
        
        # Initialize indicators
        indicator_config = config.get('indicators', {})
        ma_config = indicator_config.get('moving_averages', {})
        rsi_config = indicator_config.get('rsi', {})
        
        self.ma = MovingAverages(
            fast_period=ma_config.get('fast_period', 9),
            slow_period=ma_config.get('slow_period', 21)
        )
        
        self.rsi = RSI(
            period=rsi_config.get('period', 14),
            overbought=rsi_config.get('overbought', 70),
            oversold=rsi_config.get('oversold', 30)
        )
        
        self.macd = MACD()
        
        # Signal settings
        signal_config = config.get('signals', {})
        self.rsi_enabled = signal_config.get('rsi_divergence_enabled', True)
        self.ma_enabled = signal_config.get('ma_crossover_enabled', True)
        self.volume_check = signal_config.get('require_volume_confirmation', False)
        
        self.last_signal = Signal.HOLD
        self.last_reason = SignalReason.NONE
        self.signal_timestamp = None
    
    def add_candle(self, price: float, volume: Optional[int] = None) -> None:
        """
        Add new candle data
        
        Args:
            price: Close price
            volume: Trading volume (optional)
        """
        self.ma.add_price(price)
        self.rsi.add_price(price)
        self.macd.add_price(price)
    
    def generate_signal(self) -> Tuple[Signal, SignalReason]:
        """
        Generate trading signal based on indicators
        
        Returns:
            Tuple of (Signal, SignalReason)
        """
        if not self._is_ready():
            return Signal.HOLD, SignalReason.NONE
        
        signal = Signal.HOLD
        reason = SignalReason.NONE
        
        # Check MA crossover signal
        if self.ma_enabled:
            ma_signal, ma_reason = self._check_ma_signal()
            if ma_signal != Signal.HOLD:
                signal = ma_signal
                reason = ma_reason
        
        # Check RSI signal (if MA didn't trigger)
        if signal == Signal.HOLD and self.rsi_enabled:
            rsi_signal, rsi_reason = self._check_rsi_signal()
            if rsi_signal != Signal.HOLD:
                signal = rsi_signal
                reason = rsi_reason
        
        # Check MACD confirmation
        if signal != Signal.HOLD:
            if not self._check_macd_confirmation(signal):
                logger.debug(f"MACD doesn't confirm {signal.value} signal")
                signal = Signal.HOLD
                reason = SignalReason.NONE
        
        # Log signal
        if signal != Signal.HOLD:
            logger.info(f"Signal generated: {signal.value} ({reason.value})")
            self.last_signal = signal
            self.last_reason = reason
            self.signal_timestamp = datetime.now()
        
        return signal, reason
    
    def _is_ready(self) -> bool:
        """Check if indicators are ready"""
        return (self.ma.is_ready() and 
                self.rsi.is_ready() and 
                self.macd.is_ready())
    
    def _check_ma_signal(self) -> Tuple[Signal, SignalReason]:
        """Check moving average crossover signals"""
        if self.ma.crossover_bullish():
            return Signal.BUY, SignalReason.MA_BULLISH_CROSSOVER
        elif self.ma.crossover_bearish():
            return Signal.SELL, SignalReason.MA_BEARISH_CROSSOVER
        
        return Signal.HOLD, SignalReason.NONE
    
    def _check_rsi_signal(self) -> Tuple[Signal, SignalReason]:
        """Check RSI signals"""
        if self.rsi.is_oversold():
            return Signal.BUY, SignalReason.RSI_OVERSOLD
        elif self.rsi.is_overbought():
            return Signal.SELL, SignalReason.RSI_OVERBOUGHT
        
        return Signal.HOLD, SignalReason.NONE
    
    def _check_macd_confirmation(self, signal: Signal) -> bool:
        """
        Check if MACD confirms the signal.

        Uses histogram direction (positive = bullish momentum, negative = bearish)
        rather than requiring MACD line itself to be positive/negative.
        This allows early entries on crossovers where MACD is still negative
        but momentum is turning — which is often where the best entries are.

        Args:
            signal: Signal to confirm

        Returns:
            True if MACD confirms, False otherwise
        """
        if not self.macd.is_ready():
            return True  # Don't filter if MACD not ready

        histogram = self.macd.get_histogram()
        if histogram is None:
            return True

        if signal == Signal.BUY:
            return histogram > 0  # Momentum turning bullish
        else:  # SELL
            return histogram < 0  # Momentum turning bearish
    
    def get_indicator_values(self) -> Dict:
        """Get current indicator values for monitoring"""
        return {
            'fast_ema': self.ma.get_fast_ema(),
            'slow_ema': self.ma.get_slow_ema(),
            'rsi': self.rsi.get_rsi(),
            'macd': self.macd.get_macd(),
            'macd_signal': self.macd.get_signal(),
            'macd_histogram': self.macd.get_histogram(),
        }
    
    def reset(self) -> None:
        """Reset all indicators"""
        self.ma.reset()
        self.rsi.reset()
        self.macd.reset()
        self.last_signal = Signal.HOLD
        self.last_reason = SignalReason.NONE
        self.signal_timestamp = None
