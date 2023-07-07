import logging
import os


def set_logger(logger_name):
    log_format = "%(asctime)s - %(levelname)s - %(message)s"

    log = logging.getLogger(logger_name)
    level = os.environ.get("LOG_LEVEL", "INFO")
    log.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(log_format))

    log.addHandler(handler)
    return log


logger = set_logger("main")
