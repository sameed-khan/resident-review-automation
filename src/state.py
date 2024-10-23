"""
state.py
Exposes UiState class which manages the table and scroll area state.
"""

import mss.tools
import numpy as np
from mss import mss

from screen_parse import generate_table


class UiState:
    def __init__(
        self,
        scroll_bounds: tuple[int, int, int, int],
        header_bounds: tuple[int, int, int, int],
    ):
        self.scroll_bounds = scroll_bounds
        self.header_bounds = header_bounds

        with mss() as sct:
            # TODO: need to account for different monitors
            screenshot = sct.grab(sct.monitors[2])  # grabs monitor 1 by default
            frame = np.array(screenshot)[:, :, :3]  # BGRA -> RGB

        self.table = generate_table(frame, scroll_bounds, header_bounds)
        for row in self.table:
            row["state"]["identifier"] = "Accession"
            row["state"]["clicked"] = False

    def refresh(self):
        """Updates the internal table state based on new elements on screen"""
        with mss() as sct:
            # TODO: need to account for different monitors
            screenshot = sct.grab(sct.monitors[2])
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
