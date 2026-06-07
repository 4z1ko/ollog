import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.qso.custom_fields import FILL_BEHAVIORS, normalize_custom_qso_fields

MY_GRIDSQUARE_RE = re.compile(r"^[A-Ra-r]{2}[0-9]{2}([A-Xa-x]{2})?$")


class ACLogBridgeConfig(BaseModel):
    id: str
    name: str = ""
    host: str
    port: int = 1100
    enabled: bool = True

    @field_validator("name", "host")
    @classmethod
    def normalize_text(cls, v: str) -> str:
        return v.strip()

    @field_validator("host")
    @classmethod
    def require_host(cls, v: str) -> str:
        if not v:
            raise ValueError("ACLog bridge host is required")
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if v < 1 or v > 65535:
            raise ValueError("ACLog bridge port must be between 1 and 65535")
        return v


class CustomQSOFieldConfig(BaseModel):
    slot: int
    label: str
    adif_name: str
    enabled: bool = False
    fill_behavior: str = "none"
    force_uppercase: bool = False

    @field_validator("fill_behavior")
    @classmethod
    def validate_fill_behavior(cls, v: str) -> str:
        if v not in FILL_BEHAVIORS:
            raise ValueError(f"Invalid fill behavior: {v!r}")
        return v


class ProfileUpdateRequest(BaseModel):
    station_callsign: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    qth: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    my_gridsquare: Optional[str] = None
    my_rig: Optional[str] = None
    my_antenna: Optional[str] = None
    tx_pwr: Optional[float] = None
    notify_sound: bool = False
    aclog_bridges: list[ACLogBridgeConfig] = Field(default_factory=list)
    custom_qso_fields: list[CustomQSOFieldConfig] = Field(default_factory=list)

    @field_validator("my_gridsquare")
    @classmethod
    def validate_gridsquare(cls, v: str | None) -> str | None:
        if v is not None and not MY_GRIDSQUARE_RE.match(v):
            raise ValueError(f"Invalid Maidenhead grid format: {v!r}")
        return v.upper() if v else v

    @field_validator("station_callsign")
    @classmethod
    def normalize_station_callsign(cls, v: str | None) -> str | None:
        if v is not None and v.strip() == "":
            return None
        return v

    @field_validator("custom_qso_fields")
    @classmethod
    def validate_custom_qso_fields(
        cls,
        v: list[CustomQSOFieldConfig],
    ) -> list[CustomQSOFieldConfig]:
        return [
            CustomQSOFieldConfig(**field.model_dump())
            for field in normalize_custom_qso_fields(v)
        ]


class ProfileResponse(BaseModel):
    callsign: str
    station_callsign: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    qth: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    my_gridsquare: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    my_rig: Optional[str] = None
    my_antenna: Optional[str] = None
    tx_pwr: Optional[float] = None
    notify_sound: bool = False
    aclog_bridges: list[ACLogBridgeConfig] = Field(default_factory=list)
    custom_qso_fields: list[CustomQSOFieldConfig] = Field(default_factory=list)
