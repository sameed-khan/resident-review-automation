"""
auto.py
Defines functions and utilities for performing the actual automation tasks.
"""

import sys
import time
import logging

import keyboard
import re
import mouse
import numpy as np
import pyperclip
import win32clipboard as clipboard
from mss import mss

from screen_types import ScreenPoint, ArrayPoint, array_to_screen
from logging_config import setup_logger
from state import UiState
from util import (
    find_all_matches, find_first_match, 
    compare_screens, is_ui_settled, find_top_k_matches, 
    validate_state, wait_for_appearance
)
import cv2

logger = setup_logger(__name__)

# Constant coordinates
REPORT_WINDOW_RECT = (5667, 145, 1002, 827)
HIGHLIGHT_START_POINT = (6010, 220)
NEUTRAL_CLICK_ZONE = (5960, 430)

def is_scrollable(
    scroll_bounds: tuple[int, int, int, int], match_threshold=0.95
) -> bool:
    """
    Checks the bottom of the scroll area to see whether the page has scrolled after
    performing a scroll action.
    """
    scx, scy, sc_width, sc_height = scroll_bounds

    # checking zone will be the bottom 50 pixel row at the bottom of the scroll area
    with mss() as sct:
        region = {
            "left": scx,
            "top": sc_height - 50,
            "width": sc_width,
            "height": 50,
        }
        screenshot = sct.grab(region)
        before = np.array(screenshot)[:, :, :3].mean(axis=2)

    # perform scroll action
    mouse.move(scx + sc_width // 2, scy + sc_height // 2)
    time.sleep(0.1)

    mouse.click()
    time.sleep(0.1)

    keyboard.press_and_release("page down")
    time.sleep(0.5)

    with mss() as sct:
        region = {
            "left": scx,
            "top": sc_height - 50,
            "width": sc_width,
            "height": 50,
        }
        screenshot = sct.grab(region)
        after = np.array(screenshot)[:, :, :3].mean(axis=2)

    # check if the two images are similar
    same_probability = (before == after).sum() / (before.shape[0] * before.shape[1])
    return same_probability < match_threshold


def multiple_keypress(keys: list[str]):
    for key in keys:
        keyboard.press(key)

    time.sleep(0.1)

    for key in reversed(keys):
        keyboard.release(key)


def copy_to_clipboard():
    mouse.click("left")
    time.sleep(0.1)
    mouse.click("left")
    time.sleep(0.1)
    mouse.click("left")
    time.sleep(0.1)

    # Copy the selected text to the clipboard
    pyperclip.copy("")  # Clear the clipboard
    mouse.click("right")  # Right-click to open context menu
    time.sleep(0.1)
    multiple_keypress(["ctrl", "c"])


def get_clipboard_rtf():
    clipboard.OpenClipboard()
    try:
        if clipboard.IsClipboardFormatAvailable(clipboard.CF_RTF):
            rtf_data = clipboard.GetClipboardData(clipboard.CF_RTF)
        else:
            rtf_data = None
    finally:
        clipboard.CloseClipboard()
    return rtf_data


def save_rtf_to_file(rtf_data, filename):
    with open(filename, "w") as file:
        file.write(rtf_data)

def locate_score_button(state: UiState) -> np.ndarray[ScreenPoint]:
    logger.info("Locating report buttons")
    score_buttons = [
        "score_button.png",
        "score_button_1.png",
        "score_button_2.png",
        "score_button_3.png",
        "score_button_4.png",
    ]
    temp = []
    for but in score_buttons:
        template_path = f"template/{but}"
        matches = find_all_matches(state.screen, template_path, threshold=0.9)
        temp.extend(matches)
    
    final_matches = sorted([array_to_screen(state.current_monitor, array_coord) for array_coord in temp], key= lambda x: x[1])
    logger.debug(f"Located {len(final_matches)} report buttons at points: {final_matches}")
    return np.array(final_matches)

def open_report(location: ScreenPoint, state: UiState, template_path="template/report_textarea.png") -> None:
    logger.info("Opening report")
    logger.debug(f"Opening report: clicking at ({location[0]+10}, {location[1]+10})")
    mouse.move(location[0]+10, location[1]+10)
    time.sleep(0.5)
    mouse.click()
    wait_for_appearance(state, "template/highlight_start_point.png")
    state.refresh()

def locate_report_top_left(state: UiState, template_path="template/report_interface.png") -> tuple[ScreenPoint, int, int]:
    h, w, _ = cv2.imread(template_path).shape
    temp = find_first_match(state.screen, template_path)
    report_top_left: ScreenPoint = array_to_screen(state.current_monitor, temp)
    logger.debug(f"Located report window top left at {report_top_left} with width {w} and height {h}")
    return report_top_left, w, h

def locate_highlight_start_point(state: UiState, template_path="template/highlight_start_point.png") -> ScreenPoint:
    temp = find_first_match(state.screen, template_path)
    highlight_top_left: ScreenPoint = array_to_screen(state.current_monitor, temp)
    logger.debug(f"Located highlight start point at {highlight_top_left}")
    return highlight_top_left

def locate_checkrows(state: UiState, template_path="template/version_checkrow.png") -> np.ndarray[ScreenPoint]:
    temp: np.ndarray[ArrayPoint] = find_top_k_matches(state.screen, template_path, 2)
    checkrow_locations: np.ndarray[ScreenPoint] = np.array(
        sorted([array_to_screen(state.current_monitor, array_point) for array_point in temp], key=lambda x: x[1])
    )
    logger.debug(f"Located two checkbox for attending and resident report respectively at {checkrow_locations}")
    return checkrow_locations

def highlight_report(state: UiState, start_point: ScreenPoint, report_top_left: ScreenPoint, window_width, window_height) -> None:
    bottom_drag_end = ScreenPoint((report_top_left[0] + window_width // 2, report_top_left[1] + window_height + 20))
    logger.info("Start highlighting report")
    mouse.move(start_point[0] + 3, start_point[1])
    mouse.press()
    mouse.move(bottom_drag_end[0], bottom_drag_end[1], duration=1)
    logger.info("Reached bottom of highlighting report, waiting for scrolling to finish")
    is_ui_settled(state)
    mouse.move(0, -80, absolute=False, duration=0.5)  # Drag back up into interface
    mouse.release()
    time.sleep(0.5)
    logger.info("Report highlighting complete")

def copy_and_save(key: str, state: UiState):
    logger.info("Starting to copy and save report text")
    keyboard.send('ctrl+c')
    report = pyperclip.paste()
    dic = {}
    dic[key] = report
    state.data.append(dic)
    logger.info("Report text copied to UI state")
    logger.debug(f"Copied report to UI state, text: { \
        re.sub(r'\s+', ' ', report.replace('\n', ' ').replace('\r', '')).strip() \
    }")

def copy_one_report(state: UiState) -> None:
    # rtl, w, h = locate_report_top_left(state)
    # highlight_start_point = locate_highlight_start_point(state)
    t, l, w, h = REPORT_WINDOW_RECT
    rtl = (t, l)
    highlight_start_point = HIGHLIGHT_START_POINT
    checkrow_locations = locate_checkrows(state)
    attending_row = checkrow_locations[0]
    resident_row = checkrow_locations[1]

    # Click off the attending row to get resident report
    mouse.move(attending_row[0]+5, attending_row[1]+10)
    mouse.click()
    time.sleep(3)

    # Highlight the report
    highlight_report(state, highlight_start_point, rtl, w, h)
    copy_and_save("resident", state)

    # Get attending report
    mouse.move(resident_row[0]+5, resident_row[1]+10)
    mouse.click()

    mouse.move(attending_row[0]+5, attending_row[1]+10)
    mouse.click()
    time.sleep(3)

    # Highlight new report
    highlight_report(state, highlight_start_point, rtl, w, h)
    copy_and_save("attending", state)

    # Close report
    logger.info("Closing report")
    mouse.click()  # bring back focus to the report interface
    keyboard.send('alt+f4')
    state.refresh()

def scroll_check(state: UiState) -> bool:
    """
    Returns True if scroll was executed
    """
    logger.info("Checking if scrollable (are we at bottom of window?)")
    state.refresh()
    before_scroll = state.screen  # Save for comparison
    keyboard.send("page down")
    time.sleep(2)
    state.refresh()
    after_scroll = state.screen
    result = not compare_screens(before_scroll, after_scroll)
    logger.info(f"Interface scrollable: {result}")
    return result

def run(scroll_bounds: ScreenPoint, header_bounds: ScreenPoint):
    """
    Main function to run the automation tasks.
    """
    debug_iter = False

    ui_state = UiState(scroll_bounds, header_bounds)
    next_button = "template/next_button.png"
    no_further_scrolling = False
    second_iteration_on_page = False
    next_button_flag = True

    while True:
        logger.info("Start of iteration, finding report buttons on screen")
        button_locs = locate_score_button(ui_state)

        if second_iteration_on_page:
            logger.info("Starting iteration after page down, getting only last 5 rows")
            button_locs = button_locs[-6:]
            second_iteration_on_page = False

        if debug_iter:
            button_locs = button_locs[-1:]
            debug_iter = False

        for loc in button_locs:
            open_report(loc, ui_state)
            copy_one_report(ui_state)

        logger.info("Writing data to JSON output")
        ui_state.save()
        time.sleep(2)

        ## Checks
        # If we cannot scroll down then we are at the bottom
        if not scroll_check(ui_state):
            no_further_scrolling = True
        else:
            second_iteration_on_page = True

        if no_further_scrolling:
            logger.info("Hit bottom of screen and iteration concluded. Finding 'Next' button")
            nxb_arrtl = find_first_match(ui_state.screen, next_button, threshold=0.9)
            if nxb_arrtl is None:
                logger.info("Next button was not found. This is the final screen. Exiting application.")
                break
            logger.info("Next button found, clicking and waiting for UI update")
            nxb_sctl = array_to_screen(ui_state.current_monitor, nxb_arrtl)
            mouse.move(nxb_sctl[0]+3, nxb_sctl[1]+3)
            time.sleep(1)  # wait for highlight off row to fade
            ui_state.refresh()
            old_screen = ui_state.screen
            mouse.click()

            # Continue to wait until new page loads
            logger.info("Waiting for UI update")
            while True:
                time.sleep(1)
                ui_state.refresh()
                new_screen = ui_state.screen
                if not compare_screens(old_screen, new_screen, tolerance=0.99):
                    logger.info("UI successfully updated, scrolling to top of page")
                    break

            mouse.move(*NEUTRAL_CLICK_ZONE)
            time.sleep(0.5)
            mouse.click()
            # Keep hitting page up until we hit top of screen and nothing changes
            validate_state(ui_state, lambda: keyboard.send("page up"), isChanged=False)
            no_further_scrolling = False
