"""
auto.py
Defines functions and utilities for performing the actual automation tasks.
"""

import time

import keyboard
import mouse
import numpy as np
import pyperclip
import win32clipboard as clipboard
from mss import mss

from screen_types import ScreenPoint
from state import UiState


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


def run(scroll_bounds: ScreenPoint, header_bounds: ScreenPoint):
    """
    Main function to run the automation tasks.
    """
    # TODO: validate that AppState scroll and header bounds are correct

    counter = 0
    ui_state = UiState(scroll_bounds, header_bounds)
    while True:
        button_locs = [
            x["Score"]["textstart"]
            for x in ui_state.table
            if x is not None and not x["state"]["clicked"]
        ]
        button_locs = [x for x in button_locs if x is not None]

        for idx, loc in enumerate(button_locs):
            print("Clicking!")
            mouse.move(loc[0], loc[1])
            mouse.click()
            time.sleep(0.5)

            # Report review window should pop up now
            print("Testing reviewing report, matchTemplating...")
            # report_template = cv.imread("../template/report_textarea.png", cv.IMREAD_GRAYSCALE)
            # with mss() as sct:
            #     screenshot = sct.grab(sct.monitors[1])
            #     frame = np.array(screenshot)[:, :, :3]

            # t = cv.matchTemplate(frame, report_template, cv.TM_CCOEFF_NORMED)
            # mouse_loc = cv.minMaxLoc(t)[3]
            # mouse.move(mouse_loc[0] + 20, mouse_loc[1] + 20)
            # copy_to_clipboard()
            # rtf_data = get_clipboard_rtf()
            # save_rtf_to_file(rtf_data, f"report_{counter}.rtf")
            counter += 1

            # Close the report review window
            print("Testing closing report window...")
            # multiple_keypress(["alt", "f4"])

            # Click in center of screen to bring focus back to main window
            scx, scy, sc_width, sc_height = scroll_bounds
            midpoint = (scx + sc_width // 2, scy + sc_height // 2)
            mouse.move(*midpoint)
            mouse.click("left")
            time.sleep(0.5)

            # Mark the row as clicked
            ui_state.table[idx]["state"]["clicked"] = True

        if not is_scrollable(scroll_bounds):  # this pages down!
            break
        else:
            ui_state.refresh()  # update the table state after a page down

        if counter >= 100:
            raise Exception("Infinite loop, stopping...")
