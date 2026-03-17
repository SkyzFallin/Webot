"""Tests for signal generation"""

import pytest
from bot.strategy.signals import SignalGenerator, Signal, SignalReason


class TestSignalGenerator:
    """Test signal generation"""
    
    def test_signal_generator_initialization(self):
        """Test signal generator setup"""
        config = {
            'indicators': {
                'moving_averages': {'fast_period': 9, 'slow_period': 21},
                'rsi': {'period': 14, 'overbought': 70, 'oversold': 30},
            },
            'signals': {
                'rsi_divergence_enabled': True,
                'ma_crossover_enabled': True,
            }
        }
        
        generator = SignalGenerator(config)
        assert generator is not None
        assert generator.last_signal == Signal.HOLD
    
    def test_hold_signal_before_ready(self):
        """Test that HOLD signal is returned before indicators are ready"""
        config = {
            'indicators': {
                'moving_averages': {'fast_period': 9, 'slow_period': 21},
                'rsi': {'period': 14, 'overbought': 70, 'oversold': 30},
            },
            'signals': {
                'rsi_divergence_enabled': True,
                'ma_crossover_enabled': True,
            }
        }
        
        generator = SignalGenerator(config)
        
        # Add only a few prices
        generator.add_candle(100.0)
        signal, reason = generator.generate_signal()
        
        assert signal == Signal.HOLD
        assert reason == SignalReason.NONE
    
    def test_signal_reset(self):
        """Test signal generator reset"""
        config = {
            'indicators': {
                'moving_averages': {'fast_period': 9, 'slow_period': 21},
                'rsi': {'period': 14, 'overbought': 70, 'oversold': 30},
            },
            'signals': {
                'rsi_divergence_enabled': True,
                'ma_crossover_enabled': True,
            }
        }
        
        generator = SignalGenerator(config)
        generator.add_candle(100.0)
        generator.reset()
        
        assert generator.last_signal == Signal.HOLD
        assert generator.last_reason == SignalReason.NONE
    
    def test_indicator_values_retrieval(self):
        """Test getting indicator values"""
        config = {
            'indicators': {
                'moving_averages': {'fast_period': 9, 'slow_period': 21},
                'rsi': {'period': 14, 'overbought': 70, 'oversold': 30},
            },
            'signals': {
                'rsi_divergence_enabled': True,
                'ma_crossover_enabled': True,
            }
        }
        
        generator = SignalGenerator(config)
        
        # Add enough prices
        for price in range(100, 125):
            generator.add_candle(float(price))
        
        values = generator.get_indicator_values()
        
        assert 'fast_ema' in values
        assert 'slow_ema' in values
        assert 'rsi' in values
        assert 'macd' in values


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
