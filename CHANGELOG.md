# Webot Audit Fixes — Changelog

All fixes below are cross-referenced to the original audit finding numbers.

## CRITICAL fixes

### #1 — Per-symbol SignalGenerator (bot/main.py)
**Bug:** Single `SignalGenerator` was shared across all symbols. AAPL prices
mixed into TSLA's EMA/RSI/MACD state, making all signals meaningless.
**Fix:** `self.signal_generators: Dict[str, SignalGenerator]` — each symbol
gets its own independent indicator set, initialized on startup and lazily
for any new symbols added at runtime.

### #2 — Exit conditions now place actual sell orders (bot/main.py)
**Bug:** `_check_exit_conditions()` called `portfolio.close_position()` on
stop-loss/take-profit hits but never placed a sell order through the executor.
In live mode, the position tracker would show flat while Webull still held shares.
**Fix:** `_check_exit_conditions()` now calls `paper_executor.place_market_order()`
or `executor.place_market_order()` before updating the portfolio tracker. Failed
exit orders are logged as errors and the position stays open.

### #3 — Eastern Time for market hours (bot/main.py)
**Bug:** `datetime.now().time()` used local system time. Running on a UTC
server (Kali26) would offset market hours by 4-5 hours.
**Fix:** Uses `datetime.now(ZoneInfo("America/New_York")).time()` for correct
ET market hour checks.

### #4 — Paper trading prices now move (bot/main.py)
**Bug:** `_get_simulated_price()` returned static hardcoded prices. Indicators
could never produce crossovers or RSI signals — paper mode was dead code.
**Fix:** Random walk simulation (±0.5% per tick) so prices drift and indicators
can actually generate real signals during paper testing.

## HIGH fixes

### #5 — EMA now incremental, not O(n) recalculation (bot/strategy/indicators.py)
**Bug:** `_calculate_ema()` iterated over entire price history every tick and
the `deque(maxlen=slow_period)` truncation threw away early data, corrupting
the seed SMA after enough ticks.
**Fix:** New standalone `EMA` class with proper SMA seed + incremental update:
`EMA_new = price * k + EMA_prev * (1 - k)`. O(1) per tick, no data loss.

### #6 — MACD uses standalone EMAs correctly (bot/strategy/indicators.py)
**Bug:** MACD created `MovingAverages(fast_period, fast_period)` setting both
periods identical, then read `.get_fast_ema()` from one and `.get_slow_ema()`
from another with different deque sizes.
**Fix:** MACD now uses three independent `EMA` objects (fast, slow, signal)
with correct periods.

### #7 — MACD signal line is now EMA, not SMA (bot/strategy/indicators.py)
**Bug:** Signal line was `sum(macd_values) / len(macd_values)` — a simple average.
Standard MACD uses EMA of the MACD line.
**Fix:** `self.signal_ema = EMA(signal_period)` fed with MACD line values.

### #8 — MACD confirmation relaxed (bot/strategy/signals.py)
**Bug:** Required `macd > 0 AND histogram > 0` for buy, filtering out early
crossovers where MACD is negative but momentum is turning.
**Fix:** Only requires `histogram > 0` (bullish momentum) for buy confirmation,
allowing entries at the actual inflection point.

### #9 — RSI uses Wilder's smoothing (bot/strategy/indicators.py)
**Bug:** RSI recalculated average gain/loss from a deque each tick (SMA-style).
Standard RSI uses Wilder's exponential smoothing.
**Fix:** After seed period, uses:
`avg_gain = (prev_avg_gain * (period-1) + current_gain) / period`

### #10 — Removed duplicate setup_logging() call (bot/main.py)
**Bug:** `TradingBot.__init__()` called `setup_logging()`, which cleared all
handlers — then `main.py` called it again. First call was wasted.
**Fix:** `TradingBot.__init__()` no longer calls `setup_logging()`. The entry
point (`main.py`) is the single owner of logging configuration.

## MEDIUM fixes

### #11 — SIGTERM/SIGINT graceful shutdown (bot/main.py)
**Fix:** `signal.signal(SIGTERM, ...)` and `signal.signal(SIGINT, ...)` handlers
set `self.is_running = False` for clean loop exit. Works with systemd, Docker, etc.

### #13 — Safe iteration during exit checks (bot/main.py)
**Fix:** `_check_exit_conditions()` now snapshots the position list with
`list(self.portfolio.get_all_positions())` before iterating.

### #14 — Logs directory auto-creation for trades CSV (bot/portfolio/manager.py)
**Fix:** `_init_trades_log()` now calls `log_path.parent.mkdir(parents=True, exist_ok=True)`.

### #15 — Division-by-zero guard in position sizing (bot/strategy/risk.py)
**Fix:** `calculate_position_size()` now returns `(0, details)` if `entry_price`,
`account_balance`, or `stop_loss_percent` is <= 0.

## LOW fixes

### #17 — Removed unused `threading` import (bot/main.py)
### #18 — Removed unused `random` and `Enum` imports (bot/execution/paper_trading.py)
### #19 — Removed unused `math` import (bot/strategy/indicators.py)

### exc_info=True sweep (all files)
All `logger.error()` calls that catch an exception variable now include
`exc_info=True` for full stack traces in JSON logs.

### datetime.utcnow() deprecation (bot/logger.py)
Replaced with timezone-aware `datetime.now(tz=ZoneInfo('UTC'))`.

### test_position_sizing_fixed assertion fix (tests/test_risk.py)
Old test expected 100 shares but the max-position-size clamp (5% of $100k = $5k
at $100/share = 50 shares) correctly reduces it. Test updated to match actual
behavior. Added `test_position_sizing_fixed_no_clamp` to cover the unclamped case.

## Test results

```
32 passed in 0.19s
```
