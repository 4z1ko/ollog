import pymongo
from pymongo import IndexModel
from beanie import Document, PydanticObjectId
from pydantic import ConfigDict, Field
from typing import Optional
from datetime import datetime, timezone


class ApiToken(Document):
    """Beanie Document representing an ollog API token.

    Tokens are HMAC-SHA256 hashed — the raw token is never stored.
    token_prefix stores the first 8 chars for fast lookup before verifying
    the full HMAC hash.
    """

    model_config = ConfigDict(populate_by_name=True)

    user_id: PydanticObjectId
    name: str
    token_prefix: str
    hashed_token: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    last_used_at: Optional[datetime] = None
    enabled: bool = True

    class Settings:
        name = "api_tokens"
        indexes = [
            IndexModel(
                [
                    ("token_prefix", pymongo.ASCENDING),
                    ("user_id", pymongo.ASCENDING),
                ],
                name="prefix_user_idx",
            ),
        ]
