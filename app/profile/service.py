"""Profile service — business logic for profile reads and updates."""

from app.auth.models import User
from app.profile.grid import grid_to_latlon


async def update_profile(user: User, updates: dict) -> User:
    """Apply partial updates to a user's profile fields.

    If my_gridsquare is in updates, auto-compute latitude/longitude
    from the grid center. If my_gridsquare is set to None, clear
    latitude and longitude.

    Args:
        user: The authenticated User Beanie document.
        updates: Dict of field names to new values (from model_dump(exclude_unset=True)).

    Returns:
        The refreshed User document after update.
    """
    if "my_gridsquare" in updates:
        grid = updates["my_gridsquare"]
        if grid is not None:
            lat, lon = grid_to_latlon(grid)
            updates["latitude"] = lat
            updates["longitude"] = lon
        else:
            updates["latitude"] = None
            updates["longitude"] = None

    if updates:
        await user.update({"$set": updates})

    # Re-fetch to get the updated document (Beanie update does not mutate in-memory object)
    return await User.get(user.id)
