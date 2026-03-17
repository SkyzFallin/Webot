"""Tests for risk management"""

import pytest
from bot.strategy.risk import RiskManager


class TestRiskManager:
    """Test risk management"""
    
    def test_position_sizing_risk_based(self):
        """Test risk-based position sizing"""
        config = {
            'risk': {
                'stop_loss_percent': 2,
                'take_profit_percent': 4,
                'max_concurrent_positions': 3,
            },
            'account': {
                'max_position_size_percent': 5,
                'max_daily_loss_percent': 2,
            },
            'position_sizing': {
                'method': 'risk_based',
                'risk_per_trade_percent': 1,
            }
        }
        
        manager = RiskManager(config)
        
        entry_price = 100.0
        account_balance = 100000.0
        
        quantity, details = manager.calculate_position_size(entry_price, account_balance)
        
        assert quantity > 0
        assert details['quantity'] == quantity
        assert 'position_value' in details
        assert 'risk_amount' in details
    
    def test_position_sizing_fixed(self):
        """Test fixed position sizing"""
        config = {
            'risk': {
                'stop_loss_percent': 2,
                'take_profit_percent': 4,
                'max_concurrent_positions': 3,
            },
            'account': {
                'max_position_size_percent': 5,
                'max_daily_loss_percent': 2,
            },
            'position_sizing': {
                'method': 'fixed',
                'fixed_shares': 100,
            }
        }
        
        manager = RiskManager(config)
        
        entry_price = 100.0
        account_balance = 100000.0
        
        quantity, details = manager.calculate_position_size(entry_price, account_balance)
        
        assert quantity == 100
    
    def test_stop_loss_calculation(self):
        """Test stop loss calculation"""
        config = {
            'risk': {
                'stop_loss_percent': 2,
                'take_profit_percent': 4,
                'max_concurrent_positions': 3,
            },
            'account': {
                'max_position_size_percent': 5,
                'max_daily_loss_percent': 2,
            },
            'position_sizing': {
                'method': 'fixed',
                'fixed_shares': 10,
            }
        }
        
        manager = RiskManager(config)
        
        entry_price = 100.0
        stop_loss = manager.calculate_stop_loss(entry_price)
        
        assert stop_loss == 98.0  # 100 * (1 - 2%)
    
    def test_take_profit_calculation(self):
        """Test take profit calculation"""
        config = {
            'risk': {
                'stop_loss_percent': 2,
                'take_profit_percent': 4,
                'max_concurrent_positions': 3,
            },
            'account': {
                'max_position_size_percent': 5,
                'max_daily_loss_percent': 2,
            },
            'position_sizing': {
                'method': 'fixed',
                'fixed_shares': 10,
            }
        }
        
        manager = RiskManager(config)
        
        entry_price = 100.0
        take_profit = manager.calculate_take_profit(entry_price)
        
        assert take_profit == 104.0  # 100 * (1 + 4%)
    
    def test_can_open_new_position(self):
        """Test position limit check"""
        config = {
            'risk': {
                'stop_loss_percent': 2,
                'take_profit_percent': 4,
                'max_concurrent_positions': 3,
            },
            'account': {
                'max_position_size_percent': 5,
                'max_daily_loss_percent': 2,
            },
            'position_sizing': {
                'method': 'fixed',
                'fixed_shares': 10,
            }
        }
        
        manager = RiskManager(config)
        
        # Should allow opening when under limit
        assert manager.can_open_new_position(0) == True
        assert manager.can_open_new_position(2) == True
        
        # Should deny when at limit
        assert manager.can_open_new_position(3) == False
    
    def test_daily_loss_limit(self):
        """Test daily loss limit check"""
        config = {
            'risk': {
                'stop_loss_percent': 2,
                'take_profit_percent': 4,
                'max_concurrent_positions': 3,
            },
            'account': {
                'max_position_size_percent': 5,
                'max_daily_loss_percent': 2,
            },
            'position_sizing': {
                'method': 'fixed',
                'fixed_shares': 10,
            }
        }
        
        manager = RiskManager(config)
        account_balance = 100000.0
        
        # Within limit
        daily_pnl = -1500  # -1.5%
        assert manager.check_daily_loss_limit(daily_pnl, account_balance) == True
        
        # Exceeds limit
        daily_pnl = -3000  # -3%
        assert manager.check_daily_loss_limit(daily_pnl, account_balance) == False
    
    def test_pnl_calculation(self):
        """Test P&L calculation"""
        config = {
            'risk': {
                'stop_loss_percent': 2,
                'take_profit_percent': 4,
                'max_concurrent_positions': 3,
            },
            'account': {
                'max_position_size_percent': 5,
                'max_daily_loss_percent': 2,
            },
            'position_sizing': {
                'method': 'fixed',
                'fixed_shares': 10,
            }
        }
        
        manager = RiskManager(config)
        
        # Winning trade
        pnl, pnl_percent = manager.calculate_pnl(100.0, 105.0, 10, side='BUY')
        assert pnl == 50.0  # (105 - 100) * 10
        assert pnl_percent == 5.0
        
        # Losing trade
        pnl, pnl_percent = manager.calculate_pnl(100.0, 95.0, 10, side='BUY')
        assert pnl == -50.0  # (95 - 100) * 10
        assert pnl_percent == -5.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
