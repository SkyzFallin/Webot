# Quick Start Guide

Get the Webull trading bot up and running in 5 minutes!

## 1. Installation

```bash
# Clone or download the bot
cd webull-trading-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 2. Configuration

### Option A: Paper Trading (Recommended for Testing)

Paper trading requires NO Webull credentials:

```bash
# Copy example config
cp config/example_config.yaml config/trading_config.yaml

# Start paper trading
python main.py --mode paper
```

### Option B: Live Trading

Live trading requires Webull credentials:

```bash
# Create .env file with credentials
cp config/.env.example .env

# Edit .env with your Webull info:
# WEBULL_USERNAME=your_email@example.com
# WEBULL_PASSWORD=your_password
# WEBULL_DID=your_device_id
# WEBULL_TRADING_PIN=your_trading_pin
```

Load environment variables:
```bash
source .env  # Linux/Mac
set -a && source .env && set +a  # Bash
```

Run live trading:
```bash
python main.py --mode live
```

## 3. Run the Bot

### Paper Trading (Safest)
```bash
# Test with default config (AAPL, MSFT, TSLA)
python main.py --mode paper

# Test with specific symbols
python main.py --mode paper --symbols AAPL,SPY,QQQ

# Dry run (log only, no orders)
python main.py --mode paper --dry-run

# Debug mode
python main.py --mode paper --log-level DEBUG
```

### Live Trading
```bash
# Start live trading
python main.py --mode live

# With custom config
python main.py --mode live --config config/my_strategy.yaml

# Custom symbols
python main.py --mode live --symbols AAPL,MSFT,NVDA
```

## 4. Monitor the Bot

### Watch Logs in Real-Time
```bash
# Main log
tail -f logs/trading.log

# Trade history
cat logs/trades.csv

# View last 50 lines
tail -50 logs/trading.log
```

### Log Output Example
```
2026-03-17 10:30:00 - bot.strategy.signals - INFO - Signal generated: BUY (MA_BULLISH_CROSSOVER)
2026-03-17 10:30:01 - bot.main - INFO - BUY Signal: 10 AAPL @ $150.50 (SL: $147.49, TP: $156.50)
2026-03-17 10:30:02 - bot.execution.executor - INFO - Stock order placed: BUY 10 AAPL - Order ID: 12345
2026-03-17 10:30:03 - bot.portfolio.manager - INFO - Position added: 10 AAPL @ $150.50 (SL: $147.49, TP: $156.50)
```

## 5. Common Commands

```bash
# Paper trading with custom config
python main.py --mode paper --config config/conservative.yaml

# Aggressive strategy
python main.py --mode paper --config config/aggressive.yaml

# Single symbol
python main.py --mode paper --symbols TSLA

# Multiple symbols
python main.py --mode paper --symbols AAPL,MSFT,NVDA,AMD,GOOGL

# Ignore market hours (trade 24/7)
python main.py --mode paper --no-trading-hours

# Exit bot (Ctrl+C)
# Graceful shutdown - closes all positions and logs summary
```

## 6. File Structure

```
logs/
├── trading.log          # Main bot log (updates in real-time)
└── trades.csv           # Closed trades (CSV format for Excel)

config/
├── trading_config.yaml  # Your active strategy config
├── example_config.yaml  # Template with all options
└── .env                 # Your Webull credentials (NEVER commit!)

bot/
├── main.py             # Main bot orchestrator
├── api/
│   └── client.py       # Webull API wrapper
├── strategy/
│   ├── signals.py      # Signal generation
│   ├── indicators.py   # Technical indicators
│   └── risk.py         # Risk management
├── execution/
│   ├── executor.py     # Real order execution
│   └── paper_trading.py # Simulated trading
└── portfolio/
    └── manager.py      # Position tracking

tests/
├── test_indicators.py  # Test indicators
├── test_signals.py     # Test signals
└── test_risk.py        # Test risk management
```

## 7. Trading Strategy

The default strategy uses **momentum indicators**:

### BUY Signal When:
- ✅ RSI < 30 (oversold)
- ✅ Fast EMA > Slow EMA (bullish momentum)
- ✅ MACD histogram positive

### SELL Signal When:
- ❌ RSI > 70 (overbought)
- ❌ Fast EMA < Slow EMA (bearish momentum)
- ❌ MACD histogram negative

### Risk Management:
- 🛑 Stop loss: 2% below entry
- 📈 Take profit: 4% above entry
- 📊 Max 3 concurrent positions
- ⚠️ Max 2% daily loss before stopping

## 8. Customization

Edit `config/trading_config.yaml` to adjust:

### More Aggressive
```yaml
indicators:
  moving_averages:
    fast_period: 5        # Faster signals
    slow_period: 15
  rsi:
    oversold: 25          # Earlier buys
    overbought: 75

risk:
  take_profit_percent: 6  # Higher targets
  max_concurrent_positions: 5
```

### More Conservative
```yaml
indicators:
  moving_averages:
    fast_period: 20       # Slower signals
    slow_period: 50
  rsi:
    oversold: 35          # Stronger oversold
    overbought: 65

risk:
  stop_loss_percent: 3    # Wider stops
  take_profit_percent: 2  # Lock in earlier
  max_concurrent_positions: 1
```

## 9. Troubleshooting

### Bot won't start
```bash
# Check dependencies
pip install -r requirements.txt

# Check logs
cat logs/trading.log

# Verify config syntax
python -c "import yaml; yaml.safe_load(open('config/trading_config.yaml'))"
```

### No signals generated
- Bot still loading indicators (needs ~25 candles)
- Market might be closed (check trading_hours_enabled)
- Check logs for indicator values: `tail -100 logs/trading.log | grep -i signal`

### Connection errors (live trading)
- Verify Webull credentials in .env
- Check internet connection
- Webull API might be down
- Check logs: `tail -50 logs/trading.log | grep -i error`

### Logs filling up disk
- Logs rotate at 10MB (keeps 5 backups)
- Clear old logs: `rm logs/trading.log.* && > logs/trading.log`

## 10. Testing Before Live Trading

Always follow this sequence:

1. **Test paper trading first**
   ```bash
   python main.py --mode paper --dry-run
   ```

2. **Backtest with historical data** (review CSV logs)
   ```bash
   tail -100 logs/trades.csv
   ```

3. **Paper trade for 1-2 weeks**
   ```bash
   python main.py --mode paper
   ```

4. **Only then go live**
   ```bash
   python main.py --mode live
   ```

## 11. Safety Checklist Before Live Trading

- [ ] Tested in paper trading mode
- [ ] Understand the strategy (RSI + MA)
- [ ] Reviewed config settings
- [ ] Webull credentials secure (.env not committed)
- [ ] Starting with small account balance
- [ ] Monitoring bot actively
- [ ] Know how to stop bot (Ctrl+C)
- [ ] Understand P&L tracking

## 12. Getting Help

### Check Logs
```bash
# Full log
cat logs/trading.log

# Last 50 errors
grep ERROR logs/trading.log | tail -50

# Specific symbol
grep "AAPL" logs/trading.log

# Signals only
grep "Signal" logs/trading.log
```

### Run Tests
```bash
pytest tests/ -v
pytest tests/ -v --cov=bot
```

### Debug Mode
```bash
python main.py --mode paper --log-level DEBUG
```

---

**Ready to trade?** Start with paper mode and have fun! 🚀

For more details, see [README.md](README.md)
