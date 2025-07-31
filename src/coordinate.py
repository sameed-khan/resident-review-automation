from dataclasses import dataclass

@dataclass(frozen=True)
class AbsoluteCoordinate:
    """
    Represents a coordinate with absolute values relative to the entire
    virtual desktop space (all monitors combined).

    Attributes:
        x (int): The absolute horizontal position.
        y (int): The absolute vertical position.
    """
    x: int
    y: int

    def __iter__(self):
        return iter((self.x, self.y))

@dataclass(frozen=True)
class RelativeCoordinate:
    """
    Represents a coordinate with relative values, typically relative to the
    top-left corner of a specific monitor.

    Attributes:
        x (int): The relative horizontal position.
        y (int): The relative vertical position.
    """
    x: int
    y: int

    def to_absolute(self, screen_origin: AbsoluteCoordinate) -> AbsoluteCoordinate:
        """
        Converts the relative coordinate to an absolute coordinate based on a
        given screen's top-left corner.

        Args:
            screen_origin (AbsoluteCoordinate): The absolute top-left coordinate
                                                of the screen this coordinate is
                                                relative to.

        Returns:
            AbsoluteCoordinate: The new coordinate with absolute values.
        """
        absolute_x = screen_origin.x + self.x
        absolute_y = screen_origin.y + self.y
        return AbsoluteCoordinate(x=absolute_x, y=absolute_y)

    def __iter__(self):
        return iter((self.x, self.y))