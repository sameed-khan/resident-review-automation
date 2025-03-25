import os
import logging
from datetime import datetime

def setup_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        log_filename = datetime.now().strftime("auto_%m-%d_%H-%M-%S.log")
        if not os.path.exists("logs"):
            os.makedirs("logs")
        file_handler = logging.FileHandler(f"logs/{log_filename}")
        file_handler.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(funcName)s | %(message)s"
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
