import pymongo
from pymongo import IndexModel
from beanie import Document
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional


class ACLogBridge(BaseModel):
    """Per-user ACLog TCP API bridge configuration."""

    id: str
    name: str = ""
    host: str = "127.0.0.1"
    port: int = 1100
    enabled: bool = True


class CustomQSOField(BaseModel):
    """Per-user ACLog-style custom QSO field configuration."""

    slot: int
    label: str
    adif_name: str
    enabled: bool = False
    fill_behavior: str = "none"
    force_uppercase: bool = False


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
    my_antenna: Optional[str] = None     # ADIF 3.1.6: MY_ANTENNA
    tx_pwr: Optional[float] = None       # watts
    notify_sound: bool = False  # SND-03: off by default; missing field reads as False (no migration)
    aclog_bridges: list[ACLogBridge] = Field(default_factory=list)
    custom_qso_fields: list[CustomQSOField] = Field(default_factory=list)

    class Settings:
        name = "users"
        indexes = [
            IndexModel(
                [("username", pymongo.ASCENDING)],
                unique=True,
                name="username_unique",
            ),
        ]
