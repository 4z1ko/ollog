import pymongo
from pymongo import IndexModel
from beanie import Document
from pydantic import ConfigDict, EmailStr
from typing import Optional


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

    # Profile fields (all optional — no migration needed)
    station_callsign: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    qth: Optional[str] = None          # city
    state: Optional[str] = None        # state/province
    country: Optional[str] = None
    my_gridsquare: Optional[str] = None  # Maidenhead locator, up to 6 chars
    latitude: Optional[float] = None     # derived from my_gridsquare center
    longitude: Optional[float] = None    # derived from my_gridsquare center
    my_rig: Optional[str] = None
    my_ant: Optional[str] = None         # ADIF field name TBD at Phase 8
    tx_pwr: Optional[float] = None       # watts

    class Settings:
        name = "users"
        indexes = [
            IndexModel(
                [("username", pymongo.ASCENDING)],
                unique=True,
                name="username_unique",
            ),
        ]
