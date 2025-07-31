"""
state.py
Exposes UiState class which manages the table and scroll area state.
"""

import pyautogui
import mss.tools
import numpy as np
from mss import mss
import json

from screen_parse import is_contained

from screen_types import (
    ArrayPoint,
    ScreenCoord,
    ScreenPoint,
    array_to_screen,
    screen_to_array,
)

from coordinate import AbsoluteCoordinate

from constants import (
    EXPECTED_WIDTH,
    EXPECTED_HEIGHT,
    SCROLL_BOUNDS_TOP_LEFT, 
    SCROLL_BOUNDS_WIDTH, 
    SCROLL_BOUNDS_HEIGHT, 
    HEADER_BOUNDS_TOP_LEFT, 
    HEADER_BOUNDS_WIDTH, 
    HEADER_BOUNDS_HEIGHT
)

from logging_config import setup_logger

logger = setup_logger(__name__)

# def get_current_monitor():
#     """
#     Identifies which monitor the mouse cursor is currently on and returns
#     its top-left coordinates and dimensions.
#     """
#     print("Please position your mouse cursor in the center of the Fluency Report interface")
#     input("Press Enter to continue once the mouse is positioned correctly; do NOT click this interface or move your mouse")
#     mouse_x, mouse_y = pyautogui.position()

#     with mss() as sct:
#         for i, monitor in enumerate(sct.monitors):
#             # sct.monitors[0] is the bounding box of all monitors
#             # We are interested in individual monitors starting from index 1
#             if i == 0:
#                 continue

#             # Check if mouse coordinates fall within this monitor's bounds
#             if (monitor["left"] <= mouse_x < monitor["left"] + monitor["width"] and
#                 monitor["top"] <= mouse_y < monitor["top"] + monitor["height"]):
                
#                 logger.info(f"\nMouse cursor detected on monitor (MSS index): {i}")
#                 logger.info(f"  Monitor dimensions: {monitor['width']}x{monitor['height']}")
#                 logger.info(f"  Monitor top-left: ({monitor['left']}, {monitor['top']})")
#                 verify_monitor_dimensions(monitor)
#                 return AbsoluteCoordinate(x=monitor["left"], y=monitor["top"])

#     raise ValueError("Error: Mouse cursor not found on any defined monitor.")

def verify_monitor_dimensions(monitor_info):
    """
    Verifies if the given monitor's dimensions match the expected 1920x1080.
    Throws a script error and exits if they don't.
    """
    if monitor_info["width"] != EXPECTED_WIDTH or monitor_info["height"] != EXPECTED_HEIGHT:
        logger.error(f"\nSCRIPT ERROR: The fluency reporting interface screen is not 1920x1080.")
        logger.error(f"  Detected dimensions: {monitor_info['width']}x{monitor_info['height']}")
        logger.error(f"  Expected dimensions: {EXPECTED_WIDTH}x{EXPECTED_HEIGHT}")
        logger.error("Please ensure the fluency reporting interface is maximized on a 1920x1080 screen.")
        raise ValueError("Monitor dimensions do not match required 1920 x 1080")

    logger.info(f"Monitor dimensions verified: {monitor_info['width']}x{monitor_info['height']} (OK)")

class UiState:
    def __init__(
        self
    ):
        self.current_monitor = None
        mouse_x, mouse_y = pyautogui.position()

        # Find current monitor based on which screen contains the scroll bounds
        with mss() as sct:
            for i, monitor in enumerate(sct.monitors):
                # sct.monitors[0] is the bounding box of all monitors
                # We are interested in individual monitors starting from index 1
                if i == 0:
                    continue

                # Check if mouse coordinates fall within this monitor's bounds
                if (monitor["left"] <= mouse_x < monitor["left"] + monitor["width"] and
                    monitor["top"] <= mouse_y < monitor["top"] + monitor["height"]):
                    
                    logger.info(f"\nMouse cursor detected on monitor (MSS index): {i}")
                    logger.info(f"  Monitor dimensions: {monitor['width']}x{monitor['height']}")
                    logger.info(f"  Monitor top-left: ({monitor['left']}, {monitor['top']})")
                    verify_monitor_dimensions(monitor)
                    self.current_monitor = monitor
                    break
            else:
                raise ValueError("Error: Mouse cursor not found on any defined monitor.")


            screenshot = sct.grab(
                self.current_monitor
            )  # exclude 0th "monitor" which is the entire screen
            frame = np.array(screenshot)[:, :, :3]  # BGRA -> RGB

        self.screen = frame
        self.top_left = AbsoluteCoordinate(x=self.current_monitor["left"], y=self.current_monitor["top"])

        scroll_top_left = SCROLL_BOUNDS_TOP_LEFT.to_absolute(self.top_left)
        header_top_left = HEADER_BOUNDS_TOP_LEFT.to_absolute(self.top_left)
        self.scroll_bounds = (*scroll_top_left, SCROLL_BOUNDS_WIDTH, SCROLL_BOUNDS_HEIGHT)
        self.header_bounds = (*header_top_left, HEADER_BOUNDS_WIDTH, HEADER_BOUNDS_HEIGHT)
        self.data = []

    def refresh(self):
        """Updates the internal table state based on new elements on screen"""
        with mss() as sct:
            screenshot = sct.grab(
                self.current_monitor
            )  # Invariant: application always stays on the same screen
            frame = np.array(screenshot)[:, :, :3]
        self.screen = frame

    def save(self):
        with open("output.json", "w") as f:
            json.dump(self.data, f, indent=2)

    def convert_bounds(
        self, bounds: tuple[ScreenCoord, ScreenCoord, int, int]
    ) -> tuple[ScreenCoord, ScreenCoord, int, int]:
        """
        Converts screen bounds to array bounds
        """
        array_corner = screen_to_array(
            self.current_monitor, ScreenPoint((bounds[0], bounds[1]))
        )
        return (*array_corner, bounds[2], bounds[3])
