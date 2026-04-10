import logging

from app.config import settings

logger = logging.getLogger(__name__)


async def _bootstrap_admin() -> None:
    """Create the initial admin user from environment variables if not present.

    Called once after init_beanie during lifespan startup. Idempotent —
    if the admin user already exists it is left untouched.
    """
    if not (settings.admin_username and settings.admin_password and settings.admin_callsign):
        logger.info("Admin bootstrap skipped — ADMIN_USERNAME/PASSWORD/CALLSIGN not set")
        return

    # Import here to avoid circular imports at module load time
    from app.auth.models import User
    from app.auth.service import hash_password

    existing = await User.find_one({"username": settings.admin_username})
    if existing is not None:
        logger.info("Admin user already exists: %s", settings.admin_username)
        return

    admin = User(
        username=settings.admin_username,
        hashed_password=hash_password(settings.admin_password),
        callsign=settings.admin_callsign.upper(),
        role="admin",
        enabled=True,
    )
    await admin.insert()
    logger.info("Admin user bootstrapped: %s (%s)", settings.admin_username, settings.admin_callsign)
