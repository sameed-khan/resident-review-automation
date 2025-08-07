import os
import sys
import logging
import signal
import time
import traceback
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, List, Optional
from dotenv import load_dotenv
from coordinate import AbsoluteCoordinate, RelativeCoordinate

from auto import run
from logging_config import setup_logger

def main():
    load_dotenv()
    print("Please position (do not click!) your mouse cursor in the center of the Fluency Report interface")
    input("Press Enter to continue once the mouse is positioned correctly; do NOT click this interface or move your mouse")

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
    # scroll_bounds = (5216, 209, 1870, 827)
    # header_bounds = (5215, 188, 1887, 20)

    run()


if __name__ == "__main__":
    logger = setup_logger(__name__)

    logger.info("Automation commencing")
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logger.info(f"Changed working directory to {os.getcwd()} (two dirs up from src/main.py)")

    try:
        main()
    except Exception as e:
        logger.error(f"Error in main function: {e}")
