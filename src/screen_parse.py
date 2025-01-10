"""
Module with functions for performing OCR and parsing scroll zone on screen to produce a table.
"""
import os
import pytesseract as pyts
import cv2
from copy import deepcopy
from math import ceil

import cv2 as cv
import numpy as np
from winocr import recognize_cv2_sync, recognize_cv2
import pandas as pd

from screen_types import ArrayCoord, ArrayPoint


def hough_to_cartesian(lines, img_shape, orientation="both", angle_threshold=1):
    """
    Convert Hough lines to Cartesian coordinates and filter by orientation.

    Parameters:
    lines: numpy.ndarray - Lines from cv2.HoughLines()
    img_shape: tuple - Shape of the image (height, width)
    orientation: str - 'vertical', 'horizontal', or 'both'
    angle_threshold: float - Maximum angle deviation from vertical/horizontal (in degrees)

    Returns:
    list - Filtered lines in format [(x1, y1, x2, y2), ...]
    """
    if lines is None:
        return []

    cartesian_lines = []
    for line in lines:
        rho, theta = line[0]

        # Convert theta to degrees for easier angle comparison
        angle_deg = np.degrees(theta)

        # Normalize angle to 0-180 degrees
        if angle_deg < 0:
            angle_deg += 180

        # For vertical lines, angle will be close to 0 or 180 degrees
        # For horizontal lines, angle will be close to 90 degrees
        is_vertical = angle_deg < angle_threshold or angle_deg > (180 - angle_threshold)
        is_horizontal = (90 - angle_threshold) <= angle_deg <= (90 + angle_threshold)

        # Filter based on orientation
        should_include = (
            (orientation == "vertical" and is_vertical)
            or (orientation == "horizontal" and is_horizontal)
            or (orientation == "both")
        )

        if should_include:
            # Convert to Cartesian coordinates
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a * rho
            y0 = b * rho

            x1 = max(ceil(x0 + img_shape[1] * np.round(-b, 3)), 0)
            y1 = ceil(y0 + img_shape[0] * np.round(a, 3))
            x2 = ceil(x0 - img_shape[1] * np.round(-b, 3))
            y2 = ceil(y0 - img_shape[0] * np.round(a, 3))

            cartesian_lines.append((x1, y1, x2, y2))

    return cartesian_lines

def find_columns(
    header_region: np.ndarray,
) -> tuple[np.ndarray, dict[str, None]]:
    preproc_header = preprocess_image(header_region)
    header_df = pyts.image_to_data(preproc_header, config=os.getenv("TESS_CONFIG"), output_type=pyts.Output.DATAFRAME)
    columns, schema = process_dataframe(header_df)

    return columns, schema

def find_rows(img, bounds):
    x, y, width, height = bounds
    area = img[y : y + height, x : x + width]
    edges = cv.Canny(area, 0, 50)
    lines = cv.HoughLines(edges, 1, np.pi / 180, 500)
    lines = np.array(hough_to_cartesian(lines, area.shape, orientation="horizontal"))

    lines = lines + [x, y, x, y]

    last_line = lines[-1]
    scroll_lower_bound = np.array([x, y + height, x + width, y + height])
    if last_line[1] < scroll_lower_bound[1] - 10:
        lines = np.concatenate([lines, [scroll_lower_bound]])

    # ensure in sorted order from top row to bottom row
    lines = lines[lines[:, 1].argsort()]

    return lines


def compute_intersections(rows, columns):
    """
    Compute intersections between two sets of lines representing columns and rows.

    Args:
        columns: numpy array of shape (n, 4) where each row is [x1, y1, x2, y2] representing vertical lines
        rows: numpy array of shape (m, 4) where each row is [x1, y1, x2, y2] representing horizontal lines

    Returns:
        intersections: numpy array of shape (m, n, 2) containing [x,y] coordinates of intersections
        where intersections[i,j,:] gives the [x,y] coordinates of the intersection of row i with column j
    """
    x_reshaped = columns[:, 0]
    y_reshaped = rows[:, 1]

    intersections = np.zeros((len(rows), len(columns), 2))
    intersections[:, :, 0] = x_reshaped[None, :]
    intersections[:, :, 1] = y_reshaped[:, None]

    return intersections


# Table schema:
# {
#     "index": 0,
#     "state": {
#         "identifier": "Accession",
#         "clicked": False
#     },
#     "column_name": {
#         "data": "value",
#         "coordinate": [x, y],
#         "textstart": [x, y]
#     }
#     ...
#     "Score": { <-- this is the column that contains the button that pulls up the readout
#         ...
#     }
# }
def generate_table(
    table_img: np.ndarray,
    scroll_bounds: tuple[ArrayCoord, ArrayCoord, int, int],
    header_bounds: tuple[ArrayCoord, ArrayCoord, int, int],
) -> dict[str, dict[str, str | ArrayPoint | bool]]:
    # Get relevant regions
    scx, scy, sc_height, sc_width = scroll_bounds
    hx, hy, h_width, h_height = header_bounds
    header_area = table_img[hy : hy + h_height, hx : hx + h_width]

    # Get columns and rows
    columns, schema = find_columns(header_area)
    rows = find_rows(table_img, scroll_bounds)
    intersections = compute_intersections(rows, columns)

    # Get content
    content_bounds = (
        header_bounds[0],
        header_bounds[1] + header_bounds[3],
        scroll_bounds[2],
        scroll_bounds[3] - header_bounds[3],
    )
    cx, cy, cwidth, cheight = content_bounds
    table_content = table_img[cy : cy + cheight, cx : cx + cwidth]
    table_content_text = recognize_cv2_sync(table_content)
    content_words = []
    content_rects = []
    for line in table_content_text["lines"]:
        for word in line["words"]:
            content_words.append(word["text"])
            content_rects.append(
                [
                    word["bounding_rect"]["x"],
                    word["bounding_rect"]["y"],
                    word["bounding_rect"]["width"],
                    word["bounding_rect"]["height"],
                ]
            )

    content_rects = np.array(content_rects) + np.array(content_bounds)

    content_rects = content_rects[:, :2]
    ct = intersections[None, :, :, :] - content_rects[:, None, None, :]
    ctl = (ct * np.array([-1, -1])[None, None, None, :]).prod(axis=-1)
    cfidx = (
        np.where(ctl > 0, ctl, np.inf).reshape(len(content_words), -1).argmin(axis=1)
    )
    ccoords = np.array(np.unravel_index(cfidx, ctl.shape[1:])).T

    # Map content text to screen position
    data = []
    for i in range(len(rows) - 1):
        curr_row = deepcopy(schema)
        values = [[] for _ in range(len(schema.keys()))]
        intersection_point = [
            None for _ in range(len(schema.keys()))
        ]  # index and state keys
        textstart_point = [None for _ in range(len(schema.keys()))]
        row = np.where(ccoords[:, 0] == i)[0]
        for coord_idx in row:
            values_idx = ccoords[coord_idx, 1]
            values[values_idx].append(content_words[coord_idx])

            old_intersection_point = intersection_point[values_idx]
            update_ipoint = intersections[*ccoords[coord_idx]]
            intersection_point[values_idx] = (
                update_ipoint
                if old_intersection_point is None
                else old_intersection_point
            )

            old_textstart_point = textstart_point[values_idx]
            update_tpoint = content_rects[coord_idx, :2]
            textstart_point[values_idx] = (
                update_tpoint if old_textstart_point is None else old_textstart_point
            )

        values = [" ".join(v) for v in values]
        for key in list(schema.keys()):  # index and state keys
            curr_row[key]["data"] = values.pop(0)
            curr_row[key]["coordinate"] = intersection_point.pop(0)
            curr_row[key]["textstart"] = textstart_point.pop(0)

        curr_row["index"] = i
        curr_row["state"] = {"identifier": None, "clicked": False}
        data.append(curr_row)

    return data


def is_contained(container, rect):
    """
    Check if rect is fully contained within container.

    Args:
        container (dict): Dict with keys 'left', 'top', 'width', 'height'
        rect (tuple): Tuple of (left, top, width, height)

    Returns:
        bool: True if rect is contained within container
    """
    rect_left, rect_top, rect_width, rect_height = rect
    return (
        rect_left >= container["left"]
        and rect_top >= container["top"]
        and rect_left + rect_width <= container["left"] + container["width"]
        and rect_top + rect_height <= container["top"] + container["height"]
    )

def preprocess_image(image_arr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image_arr, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    # Optional: Denoising, blurring, or sharpening
    # blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # sharpened = cv2.filter2D(gray, -1, kernel)

    return thresh

def process_dataframe(df: pd.DataFrame):
    # Clean the dataframe
    df = df.dropna(subset=['text'])
    df['text'] = df['text'].str.replace(r'[^a-zA-Z\s]', '', regex=True).str.lower()
    
    # Initialize outputs
    tuples = []
    text_dict = {}
    
    i = 0
    while i < len(df):
        current_left = df.iloc[i]['left']
        current_text = df.iloc[i]['text']
        
        # Check if next row exists and is within 50 units
        if i + 1 < len(df) and abs(df.iloc[i + 1]['left'] - current_left) <= 50:
            combined_text = f"{current_text}_{df.iloc[i + 1]['text']}"
            tuples.append([current_left, 0, current_left, 1080])
            text_dict[combined_text] = None
            i += 2
        else:
            tuples.append([current_left, 0, current_left, 1080])
            text_dict[current_text] = None
            i += 1
    
    return np.array(tuples), text_dict