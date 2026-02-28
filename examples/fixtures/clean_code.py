"""Module for working with geometric shapes.

Provides area and perimeter calculations for common shapes.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Circle:
    """A circle defined by its radius."""

    radius: float

    def __post_init__(self) -> None:
        if self.radius < 0:
            raise ValueError(f"Radius must be non-negative, got {self.radius}")

    @property
    def area(self) -> float:
        """Calculate the area of the circle."""
        return math.pi * self.radius**2

    @property
    def circumference(self) -> float:
        """Calculate the circumference of the circle."""
        return 2 * math.pi * self.radius


@dataclass(frozen=True)
class Rectangle:
    """A rectangle defined by width and height."""

    width: float
    height: float

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError(
                f"Dimensions must be non-negative, "
                f"got width={self.width}, height={self.height}"
            )

    @property
    def area(self) -> float:
        """Calculate the area of the rectangle."""
        return self.width * self.height

    @property
    def perimeter(self) -> float:
        """Calculate the perimeter of the rectangle."""
        return 2 * (self.width + self.height)

    @property
    def is_square(self) -> bool:
        """Check if the rectangle is a square."""
        return math.isclose(self.width, self.height)


def total_area(shapes: list[Circle | Rectangle]) -> float:
    """Calculate the total area of a list of shapes.

    Args:
        shapes: List of Circle or Rectangle instances.

    Returns:
        Sum of all shape areas.
    """
    return sum(shape.area for shape in shapes)
