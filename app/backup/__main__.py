"""CLI entry point for the database backup tool.

Usage:
    python -m app.backup

Runs a single backup immediately, prints the path of the created .gz file to
stdout, and exits 0.  The asyncio.run() call creates its own event loop — no
FastAPI lifespan is involved.
"""

import asyncio


async def main() -> None:
    from app.config import settings
    from app.backup.dump import run_backup

    backup_path = await run_backup(settings)
    print(str(backup_path))


if __name__ == "__main__":
    asyncio.run(main())
