# core/adapters/infrastructure/logging.py
import logging
from typing import Any, Dict
from flask import request, g, has_request_context
from config import Config
from core.adapters.parsers import JsonSerializer, datetime_now


class StructuredJsonFormatter(logging.Formatter):
    """Custom JSON formatter that uses our JsonSerializer for structured logging"""

    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        self.json_serializer = JsonSerializer()

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string"""
        log_record: Dict[str, Any] = {'message': record.getMessage(), 'level': record.levelname,
                                      'timestamp': datetime_now().isoformat(), 'logger': record.name,
                                      'environment': Config.ENV}
        # Add standard message and level
        # Add request context if available
        if has_request_context():
            log_record.update({
                'request_id': getattr(g, 'request_id', None),
                'user_id': getattr(g, 'user_id', None),
                'ip': request.remote_addr,
                'method': request.method,
                'path': request.path,
                'user_agent': request.user_agent.string if request.user_agent else None
            })
        # Add any extra fields from record
        if hasattr(record, 'duration'):
            log_record['duration'] = record.duration
        if hasattr(record, 'status_code'):
            log_record['status_code'] = record.status_code
        # Add exception info if present
        if record.exc_info:
            log_record['exc_info'] = self.formatException(record.exc_info)
        # Add any extra attributes from the record
        if record.__dict__.get('extra'):
            log_record.update(record.__dict__['extra'])
        return self.json_serializer.dumps(log_record)


def setup_structured_logging() -> logging.Logger:
    """Configure structured logging for the application"""
    # Create logger
    logger = logging.getLogger(f'structured')
    logger.setLevel(logging.getLevelName(Config.LOG_LEVEL))
    # Remove existing handlers
    logger.handlers.clear()
    # Create JSON formatter
    formatter = StructuredJsonFormatter()
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    # Don't propagate to root logger
    logger.propagate = False
    return logger


# Create global logger instances
structured_logger = setup_structured_logging()
