"""Tests for technical indicators"""

import pytest
from bot.strategy.indicators import EMA, MovingAverages, RSI, MACD


class TestEMA:
    """Test standalone EMA"""

    def test_seed_phase(self):
        """EMA returns None until period prices are fed"""
        ema = EMA(period=5)
        for i in range(4):
            assert ema.update(100.0 + i) is None
        # 5th price seeds it
        val = ema.update(104.0)
        assert val is not None
        # Seed value should be SMA of first 5 prices
        expected_sma = (100 + 101 + 102 + 103 + 104) / 5
        assert abs(val - expected_sma) < 0.001

    def test_incremental_update(self):
        """After seeding, EMA updates incrementally"""
        ema = EMA(period=3)
        for p in [10, 20, 30]:
            ema.update(p)
        assert ema.is_ready
        # Feed one more — should move toward the new price
        prev = ema.value
        ema.update(50.0)
        assert ema.value > prev  # 50 is above the previous EMA

    def test_reset(self):
        ema = EMA(period=3)
        for p in [10, 20, 30, 40]:
            ema.update(p)
        assert ema.is_ready
        ema.reset()
        assert not ema.is_ready
        assert ema.value is None


class TestMovingAverages:
    """Test dual EMA crossover"""

    def test_fast_lt_slow_required(self):
        """Constructor rejects fast_period >= slow_period"""
        with pytest.raises(ValueError):
            MovingAverages(fast_period=10, slow_period=10)
        with pytest.raises(ValueError):
            MovingAverages(fast_period=21, slow_period=9)

    def test_ready_after_slow_period(self):
        ma = MovingAverages(fast_period=3, slow_period=5)
        for i in range(4):
            ma.add_price(100.0 + i)
            assert not ma.is_ready()
        ma.add_price(104.0)
        assert ma.is_ready()

    def test_bullish_crossover(self):
        """Strong uptrend after flat period should produce bullish crossover"""
        ma = MovingAverages(fast_period=3, slow_period=5)
        # Flat prices to seed both EMAs at ~100
        for _ in range(10):
            ma.add_price(100.0)
        # Sharp move up — fast EMA reacts faster
        for p in [105, 110, 115, 120]:
            ma.add_price(p)
        # After strong uptrend, fast should be above slow
        assert ma.get_fast_ema() > ma.get_slow_ema()

    def test_reset(self):
        ma = MovingAverages(fast_period=3, slow_period=5)
        for p in [100, 101, 102, 103, 104, 105]:
            ma.add_price(p)
        ma.reset()
        assert not ma.is_ready()
        assert ma.get_fast_ema() is None


class TestRSI:
    """Test RSI with Wilder's smoothing"""

    def test_needs_period_plus_one_prices(self):
        """RSI needs period+1 prices (period changes from period+1 prices)"""
        rsi = RSI(period=14)
        # Feed 14 prices = 13 changes, not enough
        for i in range(14):
            rsi.add_price(100.0 + i)
        assert not rsi.is_ready()
        # 15th price = 14th change, now seeded
        rsi.add_price(114.0)
        assert rsi.is_ready()

    def test_pure_uptrend_high_rsi(self):
        """Continuous uptrend should produce RSI near 100"""
        rsi = RSI(period=14)
        for i in range(50):
            rsi.add_price(100.0 + i)
        assert rsi.is_ready()
        assert rsi.get_rsi() > 90

    def test_pure_downtrend_low_rsi(self):
        """Continuous downtrend should produce RSI near 0"""
        rsi = RSI(period=14)
        for i in range(50):
            rsi.add_price(200.0 - i)
        assert rsi.is_ready()
        assert rsi.get_rsi() < 10

    def test_overbought_oversold_flags(self):
        rsi = RSI(period=14, overbought=70, oversold=30)
        # Strong uptrend
        for i in range(50):
            rsi.add_price(100.0 + i)
        assert rsi.is_overbought()
        assert not rsi.is_oversold()

    def test_rsi_range(self):
        """RSI should always be 0-100"""
        rsi = RSI(period=5)
        import random
        random.seed(42)
        for _ in range(100):
            rsi.add_price(random.uniform(50, 150))
        if rsi.is_ready():
            assert 0 <= rsi.get_rsi() <= 100

    def test_reset(self):
        rsi = RSI()
        for i in range(20):
            rsi.add_price(100.0 + i)
        rsi.reset()
        assert not rsi.is_ready()
        assert rsi.get_rsi() is None


class TestMACD:
    """Test MACD with proper EMA signal line"""

    def test_needs_enough_data(self):
        """MACD needs slow_period + signal_period - 1 prices minimum"""
        macd = MACD(fast_period=12, slow_period=26, signal_period=9)
        for i in range(33):
            macd.add_price(100.0 + i)
        # 26 prices to seed slow EMA, then 9 MACD values to seed signal EMA
        # Total ~34 prices needed
        assert not macd.is_ready()
        macd.add_price(134.0)
        assert macd.is_ready()

    def test_uptrend_positive_macd(self):
        """Strong uptrend should produce positive MACD line"""
        macd = MACD(fast_period=12, slow_period=26, signal_period=9)
        for i in range(60):
            macd.add_price(100.0 + i)
        assert macd.is_ready()
        assert macd.get_macd() > 0

    def test_histogram_exists_when_ready(self):
        macd = MACD(fast_period=12, slow_period=26, signal_period=9)
        for i in range(50):
            macd.add_price(100.0 + i)
        if macd.is_ready():
            assert macd.get_histogram() is not None

    def test_reset(self):
        macd = MACD()
        for i in range(50):
            macd.add_price(100.0 + i)
        macd.reset()
        assert not macd.is_ready()
        assert macd.get_macd() is None
        assert macd.get_signal() is None
        assert macd.get_histogram() is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
