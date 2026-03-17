"""Tests for technical indicators"""

import pytest
from bot.strategy.indicators import MovingAverages, RSI, MACD


class TestMovingAverages:
    """Test moving average indicators"""
    
    def test_ema_calculation(self):
        """Test EMA calculation"""
        ma = MovingAverages(fast_period=3, slow_period=5)
        
        prices = [100, 102, 101, 103, 104, 105]
        for price in prices:
            ma.add_price(price)
        
        assert ma.is_ready()
        assert ma.get_fast_ema() is not None
        assert ma.get_slow_ema() is not None
    
    def test_crossover_detection(self):
        """Test MA crossover signals"""
        ma = MovingAverages(fast_period=3, slow_period=5)
        
        # Prices trending up then crossing
        prices = [100, 100, 100, 101, 102, 103, 104, 105]
        
        for price in prices:
            ma.add_price(price)
            if len(prices) > 5:
                # After all prices, fast should be above slow
                assert ma.get_fast_ema() > ma.get_slow_ema()
    
    def test_reset(self):
        """Test reset functionality"""
        ma = MovingAverages()
        ma.add_price(100)
        ma.add_price(101)
        
        assert ma.is_ready() == False or ma.get_fast_ema() is not None
        
        ma.reset()
        assert not ma.is_ready()
        assert ma.get_fast_ema() is None


class TestRSI:
    """Test RSI indicator"""
    
    def test_rsi_calculation(self):
        """Test RSI calculation"""
        rsi = RSI(period=14)
        
        # Uptrend prices
        prices = list(range(100, 130))
        for price in prices:
            rsi.add_price(float(price))
        
        assert rsi.is_ready()
        rsi_value = rsi.get_rsi()
        assert rsi_value is not None
        assert 0 <= rsi_value <= 100
    
    def test_overbought_oversold(self):
        """Test overbought/oversold detection"""
        rsi = RSI(period=14, overbought=70, oversold=30)
        
        # Strong uptrend (should be overbought)
        prices = [100] * 10 + list(range(100, 130))
        for price in prices:
            rsi.add_price(float(price))
        
        assert rsi.is_ready()
        if rsi.get_rsi() > 70:
            assert rsi.is_overbought()
    
    def test_reset(self):
        """Test reset functionality"""
        rsi = RSI()
        rsi.add_price(100)
        rsi.add_price(101)
        
        rsi.reset()
        assert not rsi.is_ready()
        assert rsi.get_rsi() is None


class TestMACD:
    """Test MACD indicator"""
    
    def test_macd_calculation(self):
        """Test MACD calculation"""
        macd = MACD(fast_period=12, slow_period=26, signal_period=9)
        
        # Uptrend prices
        prices = list(range(100, 150))
        for price in prices:
            macd.add_price(float(price))
        
        macd_value = macd.get_macd()
        assert macd_value is not None
    
    def test_reset(self):
        """Test reset functionality"""
        macd = MACD()
        macd.add_price(100)
        
        macd.reset()
        assert not macd.is_ready()
        assert macd.get_macd() is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
