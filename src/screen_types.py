from typing import NewType

ScreenCoord = NewType("ScreenCoord", int)
ArrayCoord = NewType("ArrayCoord", int)

ScreenPoint = tuple[ScreenCoord, ScreenCoord]
ArrayPoint = tuple[ArrayCoord, ScreenCoord]


def screen_to_array(
    monitor_dims: dict[str, int], screen_coord: ScreenPoint
) -> ArrayPoint:
    top, left = monitor_dims["top"], monitor_dims["left"]
    return ArrayPoint((screen_coord[0] - left, screen_coord[1] - top))


def array_to_screen(
    monitor_dims: dict[str, int], array_coord: ArrayPoint
) -> ScreenPoint:
    top, left = monitor_dims["top"], monitor_dims["left"]
    return ScreenPoint((array_coord[0] + left, array_coord[1] + top))
