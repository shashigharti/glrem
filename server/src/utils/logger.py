import os
import sys
import logging
from functools import wraps

from src.config import LOG_FILENAME


class CustomLogger:
    def __init__(self, name):
        log_dir = os.path.dirname(LOG_FILENAME)

        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        self.logger = logging.getLogger(name)

        if not self.logger.hasHandlers():
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                handlers=[
                    logging.FileHandler(LOG_FILENAME),
                    logging.StreamHandler(sys.stdout),
                ],
            )

        if not os.path.exists(LOG_FILENAME):
            with open(LOG_FILENAME, "w"):
                pass

    def print_log(self, level, message, exc_info=False):
        """Log message with specified log level."""
        if level.lower() == "debug":
            self.logger.debug(message)
        elif level.lower() == "info":
            self.logger.info(message)
        elif level.lower() == "warning":
            self.logger.warning(message, exc_info=True)
        elif level.lower() == "error":
            self.logger.error(message, exc_info=True)
        elif level.lower() == "critical":
            self.logger.critical(message, exc_info=True)
        else:
            self.logger.info(message)


logger = CustomLogger(__name__)


def log_data(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.print_log(
            "info",
            f"Calling function: {func.__name__} with args: {args}, kwargs: {kwargs}",
        )

        result = func(*args, **kwargs)

        logger.print_log("info", f"Function: {func.__name__} returned: {result}")

        return result

    return wrapper
