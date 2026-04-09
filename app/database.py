from pymongo import AsyncMongoClient
from beanie import init_beanie

from app.config import settings
from app.qso.models import QSO
from app.auth.models import User
from app.tokens.models import ApiToken

_client: AsyncMongoClient | None = None


async def init_db() -> None:
    global _client
    _client = AsyncMongoClient(settings.mongodb_uri)
    await init_beanie(
        database=_client[settings.mongodb_db],
        document_models=[
            QSO,
            User,
            ApiToken,
        ],
    )


async def close_db() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_client() -> AsyncMongoClient | None:
    return _client
