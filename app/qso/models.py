import pymongo
from pymongo import IndexModel
from beanie import Document
from pydantic import ConfigDict, Field
from typing import Optional
from datetime import datetime


class QSO(Document):
    """Beanie Document representing a single QSO (contact) in the logbook.

    ADIF field names are stored verbatim as uppercase MongoDB document keys
    via extra='allow'. Core fields are declared for indexing and type safety.

    MongoDB field mapping via serialization_alias:
      - operator_callsign -> _operator  (leading underscore, locked decision)
      - is_deleted        -> _deleted   (soft-delete flag)
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    # Core declared fields — ADIF verbatim names (uppercase) plus prefixed internal fields
    # alias (not serialization_alias) is required so Beanie stores the MongoDB field name
    # correctly. populate_by_name=True allows construction using the Python attribute name.
    operator_callsign: str = Field(alias="_operator", serialization_alias="_operator")
    CALL: str
    BAND: Optional[str] = None
    MODE: Optional[str] = None
    qso_date_utc: Optional[datetime] = None
    is_deleted: bool = Field(default=False, alias="_deleted", serialization_alias="_deleted")

    @classmethod
    async def find_active(cls, operator: str) -> list["QSO"]:
        """Find all non-deleted QSOs for an operator.

        Use this instead of raw find() to exclude soft-deleted records by default.
        The operator argument should be the callsign stored in _operator field.
        """
        return await cls.find({"_operator": operator, "_deleted": False}).to_list()

    class Settings:
        name = "qsos"
        indexes = [
            IndexModel(
                [
                    ("_operator", pymongo.ASCENDING),
                    ("CALL", pymongo.ASCENDING),
                    ("qso_date_utc", pymongo.ASCENDING),
                    ("BAND", pymongo.ASCENDING),
                    ("MODE", pymongo.ASCENDING),
                ],
                unique=True,
                name="operator_qso_unique",
            ),
            IndexModel(
                [("_operator", pymongo.ASCENDING)],
                name="operator_idx",
            ),
            IndexModel(
                [("_operator", pymongo.ASCENDING), ("_deleted", pymongo.ASCENDING)],
                name="operator_active_idx",
            ),
        ]
