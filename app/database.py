from pymongo import AsyncMongoClient
from beanie import init_beanie

from app.config import settings
from app.internal_logs.service import app_logger
from app.qso.models import QSO
from app.auth.models import User
from app.tokens.models import ApiToken
from app.internal_logs.models import ApplicationLog, ApplicationLogSettings

_client: AsyncMongoClient | None = None


async def init_db() -> None:
    global _client
    _client = AsyncMongoClient(settings.mongodb_uri)
    try:
        await init_beanie(
            database=_client[settings.mongodb_db],
            document_models=[
                QSO,
                User,
                ApiToken,
                ApplicationLog,
                ApplicationLogSettings,
            ],
        )
    except Exception:
        _client.close()
        _client = None
        raise
    await app_logger.info(
        "MongoDB connection initialized",
        source="app.database",
        event_type="mongodb_connected",
        transport="system",
        metadata={"database": settings.mongodb_db},
        force=True,
    )


async def close_db() -> None:
    global _client
    if _client is not None:
        await app_logger.info(
            "MongoDB connection closing",
            source="app.database",
            event_type="mongodb_closing",
            transport="system",
        )
        _client.close()
        _client = None


def get_client() -> AsyncMongoClient | None:
    return _client
