import pytest
import logging
import json
import sys
from datetime import datetime
from io import StringIO
from flask import Flask, g, request
from core.adapters.infrastructure.logging import (
    StructuredJsonFormatter,
    setup_structured_logging
)
from tests.conftest import app


def dump_handler_state(handler):
    """Helper to dump handler configuration"""
    print(f"\nHandler State:")
    print(f"Type: {type(handler)}")
    print(f"Level: {handler.level}")
    print(f"Formatter: {type(handler.formatter)}")
    if hasattr(handler, 'stream'):
        print(f"Stream type: {type(handler.stream)}")


def dump_logger_state(logger):
    """Helper to dump logger configuration for debugging"""
    print(f"\nLogger State for {logger.name}:")
    print(f"Level: {logger.level}")
    print(f"Propagate: {logger.propagate}")
    print(f"Handlers: {logger.handlers}")
    print(f"Parent: {logger.parent}")
    if logger.parent:
        print(f"Parent level: {logger.parent.level}")
        print(f"Parent propagate: {logger.parent.propagate}")
        print(f"Parent handlers: {logger.parent.handlers}")


@pytest.fixture
def log_stream():
    stream = StringIO()
    yield stream
    stream.close()


@pytest.fixture
def logger(log_stream):
    # Create handler with our StringIO stream
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(StructuredJsonFormatter())
    dump_handler_state(handler)

    # Get logger and replace its handlers
    logger = setup_structured_logging()
    # Store original handlers
    original_handlers = logger.handlers[:]
    logger.handlers = [handler]
    dump_logger_state(logger)
    yield logger
    # Restore original handlers
    logger.handlers = original_handlers


class TestStructuredJsonFormatter:
    @pytest.fixture
    def formatter(self):
        return StructuredJsonFormatter()

    def test_basic_log_record_formatting(self, formatter):
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test_path',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )
        formatted = formatter.format(record)
        log_dict = json.loads(formatted)
        assert log_dict['message'] == 'Test message'
        assert log_dict['level'] == 'INFO'
        assert log_dict['logger'] == 'test_logger'
        assert 'timestamp' in log_dict
        datetime.fromisoformat(log_dict['timestamp'])

    def test_format_with_request_context(self, formatter, app):
        with app.test_request_context() as ctx:
            ctx.request.method = 'POST'
            ctx.request.path = '/test'
            g.request_id = 'test-id-123'
            g.user_id = 'user-456'

            record = logging.LogRecord(
                name='test_logger',
                level=logging.INFO,
                pathname='test_path',
                lineno=42,
                msg='Test message',
                args=(),
                exc_info=None
            )

            formatted = formatter.format(record)
            log_dict = json.loads(formatted)
            assert log_dict['request_id'] == 'test-id-123'
            assert log_dict['user_id'] == 'user-456'
            assert log_dict['method'] == 'POST'
            assert log_dict['path'] == '/test'

    def test_format_with_exception_info(self, formatter):
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name='test_logger',
                level=logging.ERROR,
                pathname='test_path',
                lineno=42,
                msg='Error occurred',
                args=(),
                exc_info=exc_info
            )

            formatted = formatter.format(record)
            log_dict = json.loads(formatted)
            assert 'exc_info' in log_dict
            assert 'ValueError: Test exception' in log_dict['exc_info']
            assert 'Traceback' in log_dict['exc_info']


class TestLogging:
    def test_file_logging(self, logger, log_stream):
        test_message = "Test log message"
        logger.info(test_message)
        print(f"{log_stream.getvalue().strip()=}")
        log_entry = json.loads(log_stream.getvalue().strip())
        assert log_entry['message'] == test_message
        assert log_entry['level'] == 'INFO'
        assert 'timestamp' in log_entry

    def test_request_context_logging(self, app, logger, log_stream):
        with app.test_request_context() as ctx:
            ctx.request.method = 'POST'
            ctx.request.path = '/test'
            g.request_id = 'test-123'
            g.user_id = 'user-456'

            logger.info("Test request")

            log_entry = json.loads(log_stream.getvalue().strip())
            assert log_entry['message'] == "Test request"
            assert log_entry['request_id'] == 'test-123'
            assert log_entry['user_id'] == 'user-456'
            assert log_entry['method'] == 'POST'
            assert log_entry['path'] == '/test'

    def test_error_logging(self, logger, log_stream):
        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("Error occurred")

        log_entry = json.loads(log_stream.getvalue().strip())
        assert log_entry['message'] == "Error occurred"
        assert log_entry['level'] == 'ERROR'
        assert 'ValueError: Test error' in log_entry['exc_info']

    def test_log_level_filtering(self, logger, log_stream):
        # Set log level to ERROR
        logger.setLevel(logging.ERROR)

        logger.info("This shouldn't be logged")
        logger.error("This should be logged")

        logs = [json.loads(line) for line in log_stream.getvalue().strip().split('\n') if line]
        assert len(logs) == 1, "Should only have one log entry"
        log_entry = logs[0]
        assert log_entry['message'] == "This should be logged"
        assert log_entry['level'] == 'ERROR'

    def test_extra_fields(self, logger, log_stream):
        logger.info(
            "Test with extra",
            extra={
                'extra': {
                    'custom_field': 'custom_value',
                    'request_duration': 1.23
                }
            }
        )

        log_entry = json.loads(log_stream.getvalue().strip())
        assert log_entry.get('custom_field') == 'custom_value'
        assert log_entry.get('request_duration') == 1.23

    def test_multiple_log_entries(self, logger, log_stream):
        logger.info("First message")
        logger.warning("Second message")
        logger.error("Third message")

        logs = [json.loads(line) for line in log_stream.getvalue().strip().split('\n') if line]
        assert len(logs) == 3, "Should have three log entries"
        assert logs[0]['message'] == "First message"
        assert logs[0]['level'] == 'INFO'
        assert logs[1]['message'] == "Second message"
        assert logs[1]['level'] == 'WARNING'
        assert logs[2]['message'] == "Third message"
        assert logs[2]['level'] == 'ERROR'

    def test_structured_logger_singleton(self, log_stream):
        # Test that we get the same logger instance
        logger1 = setup_structured_logging()
        logger2 = setup_structured_logging()

        assert logger1 is logger2
        assert isinstance(logger1.handlers[0].formatter, StructuredJsonFormatter)
