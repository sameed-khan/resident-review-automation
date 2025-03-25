import time
import cv2
import numpy as np
from screen_types import ArrayPoint
from state import UiState

def find_first_match(screenshot_array: np.ndarray, template_path: str, threshold: float = None) -> ArrayPoint | None:
   template = cv2.imread(template_path)
   template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
   h, w = template_gray.shape
   screenshot_gray = cv2.cvtColor(screenshot_array, cv2.COLOR_BGR2GRAY)
   result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
   
   if threshold is not None and max_val < threshold:
       return None
       
   return ArrayPoint((max_loc[0], max_loc[1]))

def find_first_match_arr(screenshot_array: np.ndarray, template: np.ndarray) -> ArrayPoint | None:
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    h, w = template_gray.shape

    screenshot_gray = cv2.cvtColor(screenshot_array, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)

    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    return ArrayPoint((max_loc[0], max_loc[1]))

def find_all_matches(screenshot_array: np.ndarray, template_path: str, threshold=0.8) -> np.ndarray[ArrayPoint]:
    template = cv2.imread(template_path)
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
    screenshot_gray = cv2.cvtColor(screenshot_array, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    
    locations = np.where(result >= threshold)
    matches = np.array([ArrayPoint((x, y)) for x, y in zip(*locations[::-1])])
    return matches

def find_top_k_matches(screenshot_array: np.ndarray, template_path: str, k: int) -> np.ndarray[ArrayPoint]:
   template = cv2.imread(template_path)
   template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
   
   screenshot_gray = cv2.cvtColor(screenshot_array, cv2.COLOR_BGR2GRAY)
   result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
   
   # Get indices of top k matches
   flat_indices = np.argsort(result.flatten())[-k:]
   rows, cols = np.unravel_index(flat_indices, result.shape)
   matches = np.array([ArrayPoint((x, y)) for x, y in zip(cols, rows)])
   return matches

def compare_screens(arr1, arr2, tolerance=0.9):
   # Convert to integers
   arr1_int = arr1.astype(int)
   arr2_int = arr2.astype(int)
   
   # Get total elements
   total = arr1_int.size
   
   # Count matching elements
   matches = (arr1_int == arr2_int).sum()
   
   # Check if match ratio meets tolerance
   return (matches / total) >= tolerance

def is_ui_settled(state: UiState, capture_interval=0.2, poll_interval=1):
    """
    Checks the screen to see if UI has "settled" i.e: have things stopped loading, etc
    """
    while True:
        time.sleep(poll_interval)
        state.refresh() 
        screen1 = state.screen
        time.sleep(capture_interval)
        state.refresh()
        screen2 = state.screen
        
        if compare_screens(screen1, screen2, tolerance=1.0):
            break

def wait_for_appearance(state: UiState, template_path: str, timeout=10, poll_interval=0.5, threshold=0.8):
    template = cv2.imread(template_path)
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    while timeout > 0:
        state.refresh()
        screen = state.screen
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, conf, _, _ = cv2.minMaxLoc(result)

        if conf > threshold:
            return

        time.sleep(poll_interval)
        timeout -= poll_interval

    raise TimeoutError(f"Timeout of {timeout} exceeded waiting for {template_path} to appear")

def validate_state(state: UiState, action: callable, isChanged=True, timeout=10, interval=0.5):
    start_time = time.time()
    while time.time() - start_time < timeout:
        state.refresh()
        before_state = state.screen
        action()
        time.sleep(interval)
        state.refresh()
        after_state = state.screen
        if isChanged:
            if not compare_screens(before_state, after_state):
                return
        else:
            if compare_screens(before_state, after_state):
                return

    raise TimeoutError(f"State did not achieve isChanged {isChanged} within {timeout} seconds")