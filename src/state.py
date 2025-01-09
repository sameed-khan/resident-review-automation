"""
state.py
Exposes UiState class which manages the table and scroll area state.
"""

import mss.tools
import numpy as np
from mss import mss

from screen_parse import generate_table, is_contained
from screen_types import ScreenCoord, ScreenPoint, screen_to_array


class UiState:
    def __init__(
        self,
        scroll_bounds: tuple[ScreenCoord, ScreenCoord, int, int],
        header_bounds: tuple[ScreenCoord, ScreenCoord, int, int],
    ):
        self.scroll_bounds = scroll_bounds
        self.header_bounds = header_bounds

        # Find current monitor based on which screen contains the scroll bounds
        with mss() as sct:
            contains_screenbounds = [
                is_contained(screen, scroll_bounds) for screen in sct.monitors[1:]
            ]
            current_monitor = contains_screenbounds.index(True)
            current_monitor = sct.monitors[1:][current_monitor]
            self.current_monitor = current_monitor
            screenshot = sct.grab(
                current_monitor
            )  # exclude 0th "monitor" which is the entire screen
            frame = np.array(screenshot)[:, :, :3]  # BGRA -> RGB

        array_scroll_bounds = self.convert_bounds(scroll_bounds)
        array_header_bounds = self.convert_bounds(header_bounds)

        self.table = generate_table(frame, array_scroll_bounds, array_header_bounds)
        for row in self.table:
            row["state"]["identifier"] = "Accession"
            row["state"]["clicked"] = False

    def refresh(self):
        """Updates the internal table state based on new elements on screen"""
        with mss() as sct:
            screenshot = sct.grab(
                self.current_monitor
            )  # Invariant: application always stays on the same screen
            frame = np.array(screenshot)[:, :, :3]

        array_scroll_bounds = self.convert_bounds(self.scroll_bounds)
        array_header_bounds = self.convert_bounds(self.header_bounds)
        new_table = generate_table(frame, array_scroll_bounds, array_header_bounds)

        identifier = self.table[0]["state"]["identifier"]
        old_ids = [x[identifier] for x in self.table]

        commit_table = []
        for idx, row in enumerate(new_table):
            if row[identifier] in old_ids:
                commit_table.append(self.table[idx])
                continue

            commit_table.append(row)

        self.table = commit_table

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
