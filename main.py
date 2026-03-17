"""
Main entry point for the Webull trading bot
"""

import argparse
import logging
from pathlib import Path

from bot.config import Config
from bot.logger import setup_logging
from bot.main import TradingBot


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Webull Autonomous Trading Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Paper trading (default)
  python main.py --mode paper
  
  # Live trading with custom config
  python main.py --mode live --config config/my_config.yaml
  
  # Dry run (log only, no orders)
  python main.py --mode paper --dry-run
  
  # Custom symbols
  python main.py --mode paper --symbols AAPL,MSFT,TSLA
        '''
    )
    
    parser.add_argument(
        '--mode',
        choices=['paper', 'live'],
        default='paper',
        help='Trading mode: paper (default) or live'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/trading_config.yaml',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--symbols',
        type=str,
        help='Comma-separated list of symbols to trade'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (log only, no actual orders)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--no-trading-hours',
        action='store_true',
        help='Ignore market hours restrictions'
    )
    
    args = parser.parse_args()
    
    # Validate mode and credentials
    if args.mode == 'live':
        import os
        creds = {
            'username': os.getenv('WEBULL_USERNAME'),
            'password': os.getenv('WEBULL_PASSWORD'),
            'did': os.getenv('WEBULL_DID'),
            'trading_pin': os.getenv('WEBULL_TRADING_PIN'),
        }
        
        if not all(creds.values()):
            print("ERROR: Live trading requires Webull credentials in environment variables:")
            print("  WEBULL_USERNAME")
            print("  WEBULL_PASSWORD")
            print("  WEBULL_DID")
            print("  WEBULL_TRADING_PIN")
            print("\nSet these in .env file and run: source .env")
            return 1
        
        # Confirmation for live trading
        print("\n" + "="*60)
        print("WARNING: LIVE TRADING MODE")
        print("="*60)
        print("This bot will execute REAL trades with REAL money.")
        print("Past performance does not guarantee future results.")
        print("\nBefore continuing, ensure:")
        print("  - You've tested in paper trading mode")
        print("  - You understand the risks")
        print("  - Your configuration is correct")
        print("  - You're monitoring the bot")
        print("="*60 + "\n")
        
        response = input("Type 'YES' to continue with LIVE trading: ").strip()
        if response != 'YES':
            print("Live trading cancelled.")
            return 0
    
    # Load configuration
    try:
        config = Config(args.config)
    except Exception as e:
        print(f"ERROR: Failed to load configuration: {e}")
        return 1
    
    # Override settings
    if args.symbols:
        config.config['watchlist'] = [s.strip().upper() for s in args.symbols.split(',')]
    
    if args.no_trading_hours:
        if 'market' not in config.config:
            config.config['market'] = {}
        config.config['market']['trading_hours_enabled'] = False
    
    # Setup logging
    logging_config = config.get_logging_config()
    logging_config['level'] = args.log_level
    setup_logging(logging_config)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting Webull Trading Bot - Mode: {args.mode}")
    logger.info(f"Config: {args.config}")
    logger.info(f"Symbols: {', '.join(config.get_watchlist())}")
    
    # Create and start bot
    try:
        bot = TradingBot(config, mode=args.mode, dry_run=args.dry_run)
        bot.start()
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
