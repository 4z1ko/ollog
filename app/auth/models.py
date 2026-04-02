import pymongo
from pymongo import IndexModel
from beanie import Document
from pydantic import ConfigDict


class User(Document):
    """Beanie Document representing an ollog user account.

    Schema is fixed — no extra fields allowed (unlike QSO).
    Passwords are stored as Argon2 hashes via pwdlib.
    """

    model_config = ConfigDict(populate_by_name=True)

    username: str
    hashed_password: str
    callsign: str
    role: str = "operator"  # "operator" | "admin"
    enabled: bool = True

    class Settings:
        name = "users"
        indexes = [
            IndexModel(
                [("username", pymongo.ASCENDING)],
                unique=True,
                name="username_unique",
            ),
        ]
