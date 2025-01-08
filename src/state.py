"""
state.py
Exposes UiState class which manages the table and scroll area state.
"""

import mss.tools
import numpy as np
from mss import mss

from screen_parse import generate_table, is_contained, monitor_normalize
from PIL import Image


class UiState:
    def __init__(
        self,
        scroll_bounds: tuple[int, int, int, int],
        header_bounds: tuple[int, int, int, int],
    ):

        # Find current monitor based on which screen contains the scroll bounds
        with mss() as sct:
            contains_screenbounds = [is_contained(screen, scroll_bounds) for screen in sct.monitors[1:]]
            current_monitor = contains_screenbounds.index(True)
            current_monitor = sct.monitors[1:][current_monitor]
            self.current_monitor = current_monitor
            screenshot = sct.grab(current_monitor)  # exclude 0th "monitor" which is the entire screen
            frame = np.array(screenshot)[:, :, :3]  # BGRA -> RGB

            self.scroll_bounds = monitor_normalize(current_monitor, scroll_bounds)  # normalize raw coords by dims of the new monitor
            self.header_bounds = monitor_normalize(current_monitor, header_bounds)

        self.table = generate_table(frame, self.scroll_bounds, self.header_bounds)
        for row in self.table:
            row["state"]["identifier"] = "Accession"
            row["state"]["clicked"] = False

    def refresh(self):
        """Updates the internal table state based on new elements on screen"""
        with mss() as sct:
            screenshot = sct.grab(self.current_monitor)  # Invariant: application always stays on the same screen
            frame = np.array(screenshot)[:, :, :3]

        new_table = generate_table(frame, self.scroll_bounds, self.header_bounds)
        identifier = self.table[0]["state"]["identifier"]
        old_ids = [x[identifier] for x in self.table]

        commit_table = []
        for idx, row in enumerate(new_table):
            if row[identifier] in old_ids:
                commit_table.append(self.table[idx])
                continue

            commit_table.append(row)

        self.table = commit_table
