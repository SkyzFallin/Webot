# Webull Autonomous Trading Bot

A fully autonomous trading bot for Webull that executes trades on stocks and options using momentum-based indicators with risk management.

## Features

- ✅ **Webull API Integration** - Real-time market data and order execution
- ✅ **Dual Asset Classes** - Trade stocks and options
- ✅ **Momentum Indicators** - Moving averages (EMA/SMA) and RSI-based signals
- ✅ **Risk Management** - Stop-loss, take-profit, and position sizing
- ✅ **Paper Trading Mode** - Test strategies without real money
- ✅ **Comprehensive Logging** - All trades, signals, and errors tracked
- ✅ **Configuration-Driven** - Load settings from environment or config file
- ✅ **P&L Monitoring** - Real-time position tracking and performance metrics

## Project Structure

```
webull-trading-bot/
├── bot/
│   ├── __init__.py
│   ├── api/                    # Webull API wrapper
│   │   ├── __init__.py
│   │   └── client.py          # API client abstraction
│   ├── strategy/               # Trading strategy modules
│   │   ├── __init__.py
│   │   ├── indicators.py      # Technical indicators (EMA, SMA, RSI)
│   │   ├── signals.py         # Signal generation logic
│   │   └── risk.py            # Risk management (position sizing, stops)
│   ├── execution/              # Order execution
│   │   ├── __init__.py
│   │   ├── executor.py        # Order placement and cancellation
│   │   └── paper_trading.py   # Paper trading simulator
│   ├── portfolio/              # Portfolio and position tracking
│   │   ├── __init__.py
│   │   └── manager.py         # Position management and P&L
│   ├── config.py              # Configuration loader
│   ├── logger.py              # Logging setup
│   └── main.py                # Main bot orchestrator
├── tests/
│   ├── __init__.py
│   ├── test_indicators.py
│   ├── test_signals.py
│   └── test_risk.py
├── config/
│   ├── example_config.yaml    # Example configuration
│   └── .env.example           # Environment variables template
├── logs/                       # Trade logs and monitoring
├── requirements.txt            # Python dependencies
├── setup.py                    # Package setup
├── main.py                     # Entry point
└── README.md                   # This file
```

## Installation

### 1. Clone and Setup

```bash
git clone <repo>
cd webull-trading-bot
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Webull Credentials

Create a `.env` file in the project root:

```bash
cp config/.env.example .env
```

Edit `.env` with your Webull credentials:

```
WEBULL_USERNAME=your_email@example.com
WEBULL_PASSWORD=your_password
WEBULL_DID=your_device_id
WEBULL_TRADING_PIN=your_trading_pin
```

> ⚠️ **Security Note**: Never commit `.env` to version control. Keep credentials private.

### 3. Configure Trading Strategy

Copy the example config:

```bash
cp config/example_config.yaml config/trading_config.yaml
```

Edit `config/trading_config.yaml` with your trading parameters (see Configuration section below).

### 4. Run the Bot

```bash
# Paper trading mode (test without real money)
python main.py --mode paper

# Live trading mode (requires confirmation)
python main.py --mode live
```

## Configuration

### Trading Config (`config/trading_config.yaml`)

```yaml
# Paper trading simulation settings
paper_trading:
  enabled: true
  initial_balance: 100000
  
# Account and position settings
account:
  max_position_size_percent: 5      # Max % of portfolio per position
  max_daily_loss_percent: 2         # Max daily loss before stopping
  
# Symbols to watch and trade
watchlist:
  - AAPL
  - MSFT
  - TSLA
  - SPY
  - QQQ

# Technical indicator settings
indicators:
  rsi:
    period: 14
    overbought: 70
    oversold: 30
  
  moving_averages:
    fast_period: 9      # EMA period for fast MA
    slow_period: 21     # EMA period for slow MA
  
  candle_interval: 5    # Candle interval in minutes

# Signal generation rules
signals:
  rsi_divergence_enabled: true
  ma_crossover_enabled: true
  require_volume_confirmation: true

# Risk management
risk:
  stop_loss_percent: 2          # Stop loss % below entry
  take_profit_percent: 4        # Take profit % above entry
  trailing_stop_percent: 1.5    # Trailing stop %
  max_concurrent_positions: 3   # Max open positions simultaneously

# Position sizing
position_sizing:
  method: "risk_based"          # "fixed" or "risk_based"
  fixed_shares: 10              # For fixed method
  risk_per_trade_percent: 1     # For risk-based method

# Time settings
market:
  trading_hours_enabled: true
  start_hour: 9                 # Market open (ET)
  end_hour: 16                  # Market close (ET)

# Logging
logging:
  level: "INFO"
  log_file: "logs/trading.log"
  trades_file: "logs/trades.csv"
```

### Environment Variables

```bash
# Webull credentials
WEBULL_USERNAME=your_email@example.com
WEBULL_PASSWORD=your_password
WEBULL_DID=your_device_id
WEBULL_TRADING_PIN=your_trading_pin

# Trading mode
TRADING_MODE=paper          # "paper" or "live"
CONFIG_FILE=config/trading_config.yaml

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/trading.log

# Optional: API rate limiting
WEBULL_RATE_LIMIT=1000      # Requests per hour
```

## Usage

### Basic Start

```bash
python main.py --mode paper --config config/trading_config.yaml
```

### Command-Line Options

```bash
python main.py [OPTIONS]

Options:
  --mode {paper,live}              Trading mode (default: paper)
  --config FILE                    Config file path
  --symbols SYMBOL1,SYMBOL2        Override watchlist symbols
  --dry-run                        Print actions without executing
  --log-level {DEBUG,INFO,WARNING} Logging level
  --help                           Show help message
```

### Monitor Live Performance

The bot logs all activity to:
- **Trades**: `logs/trades.csv` - Detailed trade execution log
- **Signals**: `logs/signals.log` - All generated signals
- **System**: `logs/trading.log` - System events and errors

```bash
# Watch logs in real-time
tail -f logs/trading.log
```

### Python API

```python
from bot.main import TradingBot
from bot.config import Config

# Load configuration
config = Config('config/trading_config.yaml')

# Create bot instance
bot = TradingBot(config, mode='paper')

# Start bot
bot.start()

# Stop bot
bot.stop()

# Get performance metrics
metrics = bot.get_metrics()
print(f"Total P&L: ${metrics['total_pnl']}")
print(f"Win Rate: {metrics['win_rate']}%")
```

## Trading Logic

### Signal Generation

1. **RSI Signal** (Momentum)
   - Buy when RSI < 30 (oversold)
   - Sell when RSI > 70 (overbought)

2. **Moving Average Crossover**
   - Buy when fast EMA crosses above slow EMA
   - Sell when fast EMA crosses below slow EMA

3. **Volume Confirmation** (optional)
   - Require above-average volume for signal confirmation

### Position Management

1. **Entry**
   - Position size calculated based on risk % and stop-loss distance
   - All orders are market orders for immediate execution

2. **Stop Loss**
   - Set at configured % below entry price
   - Automatically cancelled and recreated if price rebounds

3. **Take Profit**
   - Set at configured % above entry price
   - Partially closes position if enabled

4. **Trailing Stop** (optional)
   - Moves stop loss up as price increases
   - Locks in profits on winning trades

### Risk Management

- **Position Sizing**: Based on account balance and risk tolerance
- **Max Concurrent Positions**: Limits portfolio concentration
- **Max Daily Loss**: Stops trading if daily loss exceeds threshold
- **Drawdown Monitoring**: Tracks peak-to-trough decline

## API Integration

### Webull API Wrapper

The bot uses the `webull-api` library (or custom wrapper) to:

```python
from bot.api.client import WebullClient

client = WebullClient(username, password, did, trading_pin)

# Get account info
balance = client.get_account_balance()
positions = client.get_positions()

# Get market data
price = client.get_stock_price('AAPL')
option_price = client.get_option_price('AAPL', strike=150, exp='2026-03-20')

# Place orders
order_id = client.place_stock_order('AAPL', quantity=10, order_type='BUY')
order_id = client.place_option_order('AAPL', contracts=1, strike=150, order_type='CALL')

# Cancel order
client.cancel_order(order_id)

# Get order status
status = client.get_order_status(order_id)
```

## Paper Trading

Paper trading allows you to test strategies with simulated trades:

```bash
python main.py --mode paper
```

Features:
- Starts with configured initial balance
- Simulates order execution at current market prices
- Tracks fictional P&L and positions
- No real money or orders placed
- Perfect for backtesting and strategy validation

## Error Handling

The bot handles:
- ✅ API connection failures (auto-retry with backoff)
- ✅ Invalid orders (validation before submission)
- ✅ Order execution failures (logging and notification)
- ✅ Missing market data (skips signals if data unavailable)
- ✅ Credentials errors (fails safely with clear message)

## Logging and Monitoring

### Trade Log Example

```csv
timestamp,symbol,side,quantity,entry_price,exit_price,pnl,pnl_percent,reason
2026-03-17 10:30:00,AAPL,BUY,10,150.50,152.00,15.00,0.99,MA_CROSSOVER
2026-03-17 11:45:00,AAPL,SELL,10,152.00,151.80,-2.00,-0.13,STOP_LOSS
```

### Signal Log Example

```
[2026-03-17 10:30:00] AAPL - RSI Signal: OVERSOLD (28) - BUY
[2026-03-17 10:31:00] AAPL - MA Crossover: Fast EMA (150.30) > Slow EMA (149.50) - BUY
[2026-03-17 11:45:00] AAPL - Stop Loss Hit at $151.80 - SELL
```

## Limitations & Disclaimers

⚠️ **Important**: 
- This bot is provided for educational purposes
- Past performance ≠ future results
- Always test in paper trading mode first
- Start with small position sizes
- Monitor the bot regularly
- Keep your Webull credentials secure
- Some strategies may not work in all market conditions

## Dependencies

See `requirements.txt` for full list:
- `webull-api` - Webull API client
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `pyyaml` - Config file parsing
- `python-dotenv` - Environment variable loading
- `requests` - HTTP requests
- `pytz` - Timezone handling

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_indicators.py

# With coverage
pytest --cov=bot tests/
```

## Contributing

This is a personal project, but improvements welcome:
1. Fork the repo
2. Create a feature branch
3. Make changes with tests
4. Submit a PR

## Future Enhancements

- [ ] Options-specific strategies (spreads, IV crush, etc.)
- [ ] Machine learning signal generation
- [ ] Multi-timeframe analysis
- [ ] Discord/Slack notifications
- [ ] Web dashboard for monitoring
- [ ] Backtesting framework with historical data
- [ ] Support for other brokers (TD Ameritrade, Interactive Brokers)
- [ ] Advanced risk metrics (Sharpe, Sortino, max drawdown)

## Support

For issues:
1. Check logs in `logs/` directory
2. Verify credentials in `.env`
3. Ensure market hours (9:30 AM - 4:00 PM ET weekdays)
4. Check Webull API status

## License

Personal use only. Not for redistribution without modification.

---

**Built with ❤️ for autonomous trading**
