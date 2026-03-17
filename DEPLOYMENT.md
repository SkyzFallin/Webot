# Deployment Guide

Instructions for deploying the Webull trading bot to production environments.

## Local Development

### Setup
```bash
cd webull-trading-bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config/example_config.yaml config/trading_config.yaml
```

### Run
```bash
# Paper trading (safe, no credentials needed)
python main.py --mode paper

# With custom config
python main.py --mode paper --config config/my_config.yaml

# Debug mode
python main.py --mode paper --log-level DEBUG

# Dry run (log only)
python main.py --mode paper --dry-run
```

### Monitor
```bash
# Watch logs
tail -f logs/trading.log

# View trades
cat logs/trades.csv

# Check specific errors
grep ERROR logs/trading.log
```

---

## VPS Deployment (Linux)

### 1. Prepare VPS

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip git

# Create app user (optional but recommended)
sudo useradd -m -s /bin/bash webull
sudo su - webull
```

### 2. Clone Repository

```bash
# Clone the bot
git clone https://github.com/youruser/webull-trading-bot.git
cd webull-trading-bot

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure

```bash
# Setup credentials
cp config/.env.example .env
nano .env  # Edit with your credentials

# Load environment variables
source .env

# Copy config
cp config/example_config.yaml config/trading_config.yaml
nano config/trading_config.yaml  # Customize if needed
```

### 4. Run as Service

Create systemd service file:

```bash
sudo nano /etc/systemd/system/webull-bot.service
```

Content:
```ini
[Unit]
Description=Webull Trading Bot
After=network.target

[Service]
Type=simple
User=webull
WorkingDirectory=/home/webull/webull-trading-bot
Environment="PATH=/home/webull/webull-trading-bot/venv/bin"
EnvironmentFile=/home/webull/webull-trading-bot/.env
ExecStart=/home/webull/webull-trading-bot/venv/bin/python main.py --mode live --log-level INFO
Restart=always
RestartSec=10
StandardOutput=append:/home/webull/webull-trading-bot/logs/systemd.log
StandardError=append:/home/webull/webull-trading-bot/logs/systemd.log

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable webull-bot
sudo systemctl start webull-bot
sudo systemctl status webull-bot
```

### 5. Monitor Service

```bash
# View status
sudo systemctl status webull-bot

# View logs
sudo journalctl -u webull-bot -f

# Restart if needed
sudo systemctl restart webull-bot

# Stop
sudo systemctl stop webull-bot
```

---

## Docker Deployment

### Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Run bot
ENV PYTHONUNBUFFERED=1
CMD ["python", "main.py", "--mode", "live"]
```

### Create docker-compose.yml

```yaml
version: '3.8'

services:
  webull-bot:
    build: .
    container_name: webull-trading-bot
    environment:
      - WEBULL_USERNAME=${WEBULL_USERNAME}
      - WEBULL_PASSWORD=${WEBULL_PASSWORD}
      - WEBULL_DID=${WEBULL_DID}
      - WEBULL_TRADING_PIN=${WEBULL_TRADING_PIN}
      - TRADING_MODE=live
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"
```

### Run Docker

```bash
# Copy .env
cp config/.env.example .env
nano .env  # Fill in credentials

# Build and run
docker-compose up -d

# View logs
docker-compose logs -f webull-bot

# Stop
docker-compose down
```

---

## Screen/Tmux (Simple Persistent)

### Using Screen

```bash
# Start session
screen -S webull-bot

# Inside screen, run bot
source venv/bin/activate
source .env
python main.py --mode live

# Detach (Ctrl+A, D)

# Reattach
screen -r webull-bot

# Kill session
screen -S webull-bot -X quit
```

### Using Tmux

```bash
# Start session
tmux new-session -d -s webull-bot

# Run bot
tmux send-keys -t webull-bot "cd ~/webull-trading-bot && source venv/bin/activate && source .env && python main.py --mode live" Enter

# View logs
tmux send-keys -t webull-bot "tail -f logs/trading.log" Enter

# Attach to session
tmux attach -t webull-bot

# Detach (Ctrl+B, D)

# Kill session
tmux kill-session -t webull-bot
```

---

## Cloud Platforms

### AWS EC2

```bash
# Launch EC2 instance (Ubuntu 22.04, t3.micro or larger)

# SSH into instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Follow VPS deployment steps above

# Use systemd service for auto-start on reboot
```

### Heroku (not recommended for long-running bots)

Would require worker dyno and 24/7 uptime plan. Docker deployment recommended instead.

### DigitalOcean Droplet

Similar to AWS - follow VPS deployment:

```bash
# Create droplet (5USD/month, Ubuntu 22.04)
# SSH in and run VPS deployment steps
```

---

## Monitoring & Alerts

### Email Alerts (Optional)

Extend `bot/main.py` to send alerts:

```python
import smtplib

def send_email_alert(subject, message):
    """Send email alert"""
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASS'))
        
        msg = f"Subject: {subject}\n\n{message}"
        server.sendmail(os.getenv('EMAIL_USER'), os.getenv('EMAIL_TO'), msg)
        server.quit()
    except Exception as e:
        logger.error(f"Email alert failed: {e}")
```

### Discord Webhook (Optional)

```python
import requests

def send_discord_alert(message):
    """Send Discord message"""
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    if webhook_url:
        try:
            requests.post(webhook_url, json={'content': message})
        except Exception as e:
            logger.error(f"Discord alert failed: {e}")
```

Add to `.env`:
```
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
EMAIL_TO=alert@example.com
DISCORD_WEBHOOK=https://discordapp.com/api/webhooks/...
```

---

## Backup & Recovery

### Backup Logs

```bash
# Backup logs directory
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/

# Upload to cloud storage
aws s3 cp logs_backup_*.tar.gz s3://your-bucket/backups/
```

### Backup Configuration

```bash
# Backup config (but never commit .env!)
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/*.yaml

# Keep .env secure - use secrets manager instead
```

---

## Troubleshooting

### Bot Crashes Frequently

1. Check disk space: `df -h`
2. Check memory: `free -h`
3. Check logs: `tail -100 logs/trading.log`
4. Increase verbosity: `--log-level DEBUG`

### Connection Errors

1. Check internet: `ping google.com`
2. Check Webull API status
3. Verify credentials in .env
4. Check firewall rules

### Logs Growing Too Large

1. Logs rotate at 10MB (default, 5 backups kept)
2. Manual cleanup: `rm logs/trading.log.*`
3. Compress old logs: `gzip logs/trading.log.1`

### High CPU/Memory Usage

1. Increase candle_interval (slower updates)
2. Reduce watchlist size
3. Lower log verbosity
4. Check for infinite loops in logs

---

## Performance Tuning

### Optimize for Low Resources

```yaml
# In config/trading_config.yaml

# Increase update interval (slower trading)
indicators:
  candle_interval: 15  # 15 minutes instead of 5

# Reduce symbols (fewer API calls)
watchlist:
  - AAPL
  - SPY

# Reduce logging verbosity
logging:
  level: "WARNING"  # Not INFO
```

### Scale for High Throughput

```yaml
# More frequent updates
indicators:
  candle_interval: 1  # 1 minute

# More symbols
watchlist:
  - AAPL
  - MSFT
  - TSLA
  - SPY
  - QQQ
  - NVDA
  - AMD
  - GOOGL

# Debug logging for analysis
logging:
  level: "DEBUG"
```

---

## Security Checklist

- ✅ Never commit `.env` file to git
- ✅ Use environment variables for credentials
- ✅ Use unique, strong trading PIN
- ✅ Enable 2FA on Webull account
- ✅ Restrict API permissions to trading only
- ✅ Use minimal balance for live trading initially
- ✅ Monitor account activity regularly
- ✅ Keep VPS and packages updated
- ✅ Use firewall rules on VPS
- ✅ Log all trades for audit trail
- ✅ Backup configuration regularly
- ✅ Test extensively in paper mode first

---

## Rollback Plan

If something goes wrong:

```bash
# Stop the bot
sudo systemctl stop webull-bot
# or
docker-compose down
# or
Ctrl+C in screen/tmux

# Close any open positions manually (if needed)

# Review trades.csv to understand what happened
cat logs/trades.csv

# Check logs for errors
grep ERROR logs/trading.log

# Fix the issue
# - Update config, or
# - Fix code bug, or
# - Adjust parameters

# Test in paper mode
python main.py --mode paper --dry-run

# Restart
sudo systemctl start webull-bot
# or
docker-compose up -d
```

---

## Maintenance Schedule

### Daily
- Monitor logs: `tail -f logs/trading.log`
- Check trades: `cat logs/trades.csv`
- Verify balance and positions in Webull app

### Weekly
- Review performance metrics
- Check disk space: `df -h`
- Backup logs: `tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/`

### Monthly
- Update dependencies: `pip install --upgrade -r requirements.txt`
- Review configuration effectiveness
- Adjust strategy if needed
- Archive old logs

### Quarterly
- Security audit (check API keys, 2FA)
- Performance review (P&L, win rate)
- Update VPS and OS packages
- Test disaster recovery procedures

---

## Support

For issues:
1. Check `logs/trading.log`
2. Enable `--log-level DEBUG` for more details
3. Test in paper trading mode
4. Review configuration in `config/trading_config.yaml`
5. Check Webull API status

---

**Deployment complete!** Your bot is now running autonomously. 🚀

Monitor it regularly and adjust as needed.
