from datetime import datetime, timezone


def from_mongo_dt(dt: datetime | None) -> datetime | None:
    """Re-attach UTC tzinfo to a datetime read from MongoDB.
    PyMongo may return naive datetimes — always call this after reads."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
