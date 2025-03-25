import os
import sys
import pytesseract as pyts
import logging
import signal
import time
import traceback
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, List, Optional
from dotenv import load_dotenv

from auto import run
from logging_config import setup_logger

def main():
    load_dotenv()
    pyts.pytesseract.tesseract_cmd=os.getenv("TESSERACT_LOCATION")

    # Dirty coordinates
    # scroll_bounds = (13, 186, 1872, 843)
    # header_bounds = (14, 188, 1867, 23)

    # Clean coordinates
    # header_bounds = (15, 185, 1870, 25)
    # scroll_bounds = (15, 185, 1870, 850)
    # run(scroll_bounds, header_bounds)

    # Dev multiscreen coordinates
    # scroll_bounds = (-1906, 210, 1900, 819)
    # header_bounds = (-1906, 189, 1900, 22)
    # run(scroll_bounds, header_bounds)

    # Prod coordinates
    scroll_bounds = (5216, 209, 1870, 827)
    header_bounds = (5215, 188, 1887, 20)
    run(scroll_bounds, header_bounds)


if __name__ == "__main__":
    logger = setup_logger(__name__)

    logger.info("Automation commencing")
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logger.info("Changed working directory to ../../src/main.py")
    sys.exit(main())
