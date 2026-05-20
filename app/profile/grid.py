"""Maidenhead grid square to lat/lon conversion utility."""

import maidenhead


def grid_to_latlon(grid: str) -> tuple[float, float]:
    """Convert Maidenhead grid locator to (latitude, longitude).

    Returns the center of the grid square, not the SW corner.
    Supports 2-, 4-, and 6-character Maidenhead locators.

    Args:
        grid: Maidenhead locator string (e.g., "FN31", "FN31pr").

    Returns:
        Tuple of (latitude, longitude) as floats, representing
        the center of the grid square.

    Raises:
        ValueError: If grid is empty, wrong length, or invalid format.
    """
    if not isinstance(grid, str) or not grid:
        raise ValueError(f"Grid must be a non-empty string: {grid!r}")
    if len(grid) % 2 != 0 or len(grid) not in (2, 4, 6):
        raise ValueError(
            f"Grid must be 2, 4, or 6 characters, got {len(grid)}: {grid!r}"
        )
    grid = grid.strip().upper()
    # Validate Maidenhead character classes:
    # Positions 0-1: letters A-R, Positions 2-3: digits 0-9,
    # Positions 4-5: letters A-X (if present)
    if len(grid) >= 2 and not grid[0:2].isalpha():
        raise ValueError(f"Grid positions 0-1 must be letters: {grid!r}")
    if len(grid) >= 4 and not grid[2:4].isdigit():
        raise ValueError(f"Grid positions 2-3 must be digits: {grid!r}")
    if len(grid) == 6 and not grid[4:6].isalpha():
        raise ValueError(f"Grid positions 4-5 must be letters: {grid!r}")
    return maidenhead.to_location(grid, center=True)
