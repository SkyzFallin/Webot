"""
Logging configuration and setup
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.now(tz=__import__('zoneinfo').ZoneInfo('UTC')).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                              'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message',
                              'pathname', 'process', 'processName', 'relativeCreated', 'thread',
                              'threadName', 'exc_info', 'exc_text', 'stack_info', 'getMessage']:
                    log_data[key] = str(value)
        
        return json.dumps(log_data)


def setup_logging(config: Dict[str, Any]) -> None:
    """
    Setup logging based on configuration
    
    Args:
        config: Logging configuration dictionary
    """
    log_level = config.get('level', 'INFO').upper()
    log_file = config.get('log_file', 'logs/trading.log')
    
    # Create logs directory
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (rotating)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(getattr(logging, log_level))
    file_formatter = JSONFormatter()
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    logging.getLogger(__name__).info(f"Logging initialized - Level: {log_level}, File: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)
