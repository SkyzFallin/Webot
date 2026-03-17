"""
Technical indicators for trading signals
Includes: Moving Averages (SMA, EMA), RSI, MACD

All indicators use standard incremental calculations:
- EMA: incremental with SMA seed
- RSI: Wilder's smoothing method
- MACD: dual incremental EMA with EMA signal line
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EMA:
    """Single Exponential Moving Average — incremental calculation"""

    def __init__(self, period: int):
        self.period = period
        self.multiplier = 2.0 / (period + 1)
        self._seed_prices: list[float] = []
        self.value: Optional[float] = None
        self.prev_value: Optional[float] = None

    def update(self, price: float) -> Optional[float]:
        """Feed one price, return current EMA or None if not yet seeded."""
        # Seeding phase: collect `period` prices, then SMA becomes first EMA
        if self.value is None:
            self._seed_prices.append(price)
            if len(self._seed_prices) >= self.period:
                self.value = sum(self._seed_prices) / self.period
                self._seed_prices = []
            return self.value

        # Incremental EMA
        self.prev_value = self.value
        self.value = price * self.multiplier + self.value * (1 - self.multiplier)
        return self.value

    @property
    def is_ready(self) -> bool:
        return self.value is not None

    def reset(self) -> None:
        self._seed_prices = []
        self.value = None
        self.prev_value = None


class MovingAverages:
    """Dual EMA crossover detector (fast + slow)"""

    def __init__(self, fast_period: int = 9, slow_period: int = 21):
        if fast_period >= slow_period:
            raise ValueError(f"fast_period ({fast_period}) must be < slow_period ({slow_period})")
        self.fast_ema = EMA(fast_period)
        self.slow_ema = EMA(slow_period)

    def add_price(self, price: float) -> None:
        self.fast_ema.update(price)
        self.slow_ema.update(price)

    def get_fast_ema(self) -> Optional[float]:
        return self.fast_ema.value

    def get_slow_ema(self) -> Optional[float]:
        return self.slow_ema.value

    def is_ready(self) -> bool:
        return self.fast_ema.is_ready and self.slow_ema.is_ready

    def crossover_bullish(self) -> bool:
        """Fast EMA crosses above slow EMA this tick."""
        if not self.is_ready():
            return False
        prev_fast = self.fast_ema.prev_value
        prev_slow = self.slow_ema.prev_value
        if prev_fast is None or prev_slow is None:
            return False
        return prev_fast <= prev_slow and self.fast_ema.value > self.slow_ema.value

    def crossover_bearish(self) -> bool:
        """Fast EMA crosses below slow EMA this tick."""
        if not self.is_ready():
            return False
        prev_fast = self.fast_ema.prev_value
        prev_slow = self.slow_ema.prev_value
        if prev_fast is None or prev_slow is None:
            return False
        return prev_fast >= prev_slow and self.fast_ema.value < self.slow_ema.value

    def reset(self) -> None:
        self.fast_ema.reset()
        self.slow_ema.reset()


class RSI:
    """
    Relative Strength Index — Wilder's smoothing method

    First avg_gain/avg_loss = SMA of first `period` changes.
    Subsequent values use exponential smoothing:
        avg_gain = (prev_avg_gain * (period - 1) + current_gain) / period
    """

    def __init__(self, period: int = 14, overbought: float = 70.0, oversold: float = 30.0):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

        self._prev_price: Optional[float] = None
        self._seed_gains: list[float] = []
        self._seed_losses: list[float] = []
        self.avg_gain: Optional[float] = None
        self.avg_loss: Optional[float] = None
        self.rsi: Optional[float] = None
        self._seeded = False

    def add_price(self, price: float) -> None:
        if self._prev_price is None:
            self._prev_price = price
            return

        change = price - self._prev_price
        self._prev_price = price
        gain = max(change, 0.0)
        loss = max(-change, 0.0)

        if not self._seeded:
            self._seed_gains.append(gain)
            self._seed_losses.append(loss)
            if len(self._seed_gains) >= self.period:
                self.avg_gain = sum(self._seed_gains) / self.period
                self.avg_loss = sum(self._seed_losses) / self.period
                self._seeded = True
                self._seed_gains = []
                self._seed_losses = []
                self._compute_rsi()
        else:
            # Wilder's smoothing
            self.avg_gain = (self.avg_gain * (self.period - 1) + gain) / self.period
            self.avg_loss = (self.avg_loss * (self.period - 1) + loss) / self.period
            self._compute_rsi()

    def _compute_rsi(self) -> None:
        if self.avg_loss == 0:
            self.rsi = 100.0 if self.avg_gain > 0 else 50.0
        else:
            rs = self.avg_gain / self.avg_loss
            self.rsi = 100.0 - (100.0 / (1.0 + rs))

    def get_rsi(self) -> Optional[float]:
        return self.rsi

    def is_ready(self) -> bool:
        return self._seeded

    def is_overbought(self) -> bool:
        return self.rsi is not None and self.rsi > self.overbought

    def is_oversold(self) -> bool:
        return self.rsi is not None and self.rsi < self.oversold

    def reset(self) -> None:
        self._prev_price = None
        self._seed_gains = []
        self._seed_losses = []
        self.avg_gain = None
        self.avg_loss = None
        self.rsi = None
        self._seeded = False


class MACD:
    """
    MACD — proper implementation using standalone EMA objects

    - MACD line = EMA(fast) - EMA(slow)
    - Signal line = EMA(signal_period) of MACD line
    - Histogram = MACD line - Signal line
    """

    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        self.fast_ema = EMA(fast_period)
        self.slow_ema = EMA(slow_period)
        self.signal_ema = EMA(signal_period)

        self.macd_line: Optional[float] = None
        self.signal_line: Optional[float] = None
        self.histogram: Optional[float] = None

    def add_price(self, price: float) -> None:
        fast_val = self.fast_ema.update(price)
        slow_val = self.slow_ema.update(price)

        if fast_val is not None and slow_val is not None:
            self.macd_line = fast_val - slow_val
            sig = self.signal_ema.update(self.macd_line)
            if sig is not None:
                self.signal_line = sig
                self.histogram = self.macd_line - self.signal_line

    def get_macd(self) -> Optional[float]:
        return self.macd_line

    def get_signal(self) -> Optional[float]:
        return self.signal_line

    def get_histogram(self) -> Optional[float]:
        return self.histogram

    def is_ready(self) -> bool:
        return self.signal_line is not None

    def reset(self) -> None:
        self.fast_ema.reset()
        self.slow_ema.reset()
        self.signal_ema.reset()
        self.macd_line = None
        self.signal_line = None
        self.histogram = None
