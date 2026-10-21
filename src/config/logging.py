import logging
import sys
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from queue import SimpleQueue
from typing import Literal

# Seting destination log file
_LOG_DIR = Path("log")
_LOG_FILE = _LOG_DIR / 'app.log'

_log_queue = SimpleQueue()
_queue_listener: QueueListener | None = None

def setup_logging(mode: Literal['production','development'] = 'development') -> None:
    global _queue_listener

    if _queue_listener is not None:
        return 

    # Ensure the directory exists
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Write log into file handle
    capture_handler = None

    if mode == 'production':
        # For production all logs will be located in log files under backend/src/log
        capture_handler = RotatingFileHandler(
            filename=_LOG_FILE,
            maxBytes= 1024 * 1024 * 10,
            backupCount=4,
            encoding="utf-8"
        )

    else:
        # For developement all logs will be logged and printed long with the terminal as usual
        capture_handler = logging.StreamHandler(sys.stdout)

    capture_handler.setFormatter(
       logging.Formatter(
            "%(asctime)s | %(levelname)s | [ %(name)s ] - %(message)s"
       )
    )

    # Create logging queue listener
    _queue_listener = QueueListener(
        _log_queue,
        capture_handler,
        respect_handler_level=True
    )

    _queue_listener.start()

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(QueueHandler(_log_queue))
    root_logger.setLevel(logging.INFO)


def shut_down_logging() -> None:
    global _queue_listener

    if _queue_listener is None:
        return

    _queue_listener.stop()
    _queue_listener = None


def get_logger(name: str | None) -> logging.Logger:
    return logging.getLogger(name)