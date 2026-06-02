import pymongo
from pymongo import IndexModel
from beanie.odm.actions import ActionDirections
from beanie.odm.bulk import BulkWriter
from beanie.odm.fields import WriteRules
from beanie import Document
from pydantic import ConfigDict, Field
from typing import Any, Mapping, Optional
from datetime import datetime, timezone

from pymongo.asynchronous.client_session import AsyncClientSession

from app.hashing import canonical_document_hash


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
    created_at: datetime = Field(
        alias="_created_at",
        serialization_alias="_created_at",
        default_factory=lambda: datetime.now(timezone.utc),
    )
    row_hash: str = Field(default="", alias="rowHash", serialization_alias="rowHash")

    def refresh_row_hash(self) -> str:
        """Recompute rowHash from business-relevant document values."""
        self.row_hash = canonical_document_hash(self.model_dump(by_alias=True))
        return self.row_hash

    def _row_hash_after_set(self, updates: Mapping[Any, Any]) -> tuple[str, dict[Any, Any]]:
        set_doc = dict(updates)
        if "is_deleted" in set_doc:
            set_doc["_deleted"] = set_doc.pop("is_deleted")
        if "row_hash" in set_doc:
            set_doc["rowHash"] = set_doc.pop("row_hash")

        merged = self.model_dump(by_alias=True)
        merged.update(set_doc)
        set_doc["rowHash"] = canonical_document_hash(merged)
        return set_doc["rowHash"], set_doc

    async def insert(
        self,
        *,
        link_rule: WriteRules = WriteRules.DO_NOTHING,
        session: AsyncClientSession | None = None,
        skip_actions: list[ActionDirections | str] | None = None,
    ) -> "QSO":
        self.refresh_row_hash()
        return await super().insert(
            link_rule=link_rule,
            session=session,
            skip_actions=skip_actions,
        )

    async def update(
        self,
        *args: dict[Any, Any] | Mapping[Any, Any],
        ignore_revision: bool = False,
        session: AsyncClientSession | None = None,
        bulk_writer: BulkWriter | None = None,
        skip_actions: list[ActionDirections | str] | None = None,
        skip_sync: bool | None = None,
        **pymongo_kwargs: Any,
    ) -> "QSO":
        update_args = list(args)
        if len(update_args) == 1 and isinstance(update_args[0], Mapping):
            update_doc = dict(update_args[0])
            if "$set" in update_doc and isinstance(update_doc["$set"], Mapping):
                row_hash, set_doc = self._row_hash_after_set(update_doc["$set"])
                update_doc["$set"] = set_doc
                self.row_hash = row_hash
                if "_deleted" in set_doc:
                    self.is_deleted = set_doc["_deleted"]
                update_args[0] = update_doc

        return await super().update(
            *update_args,
            ignore_revision=ignore_revision,
            session=session,
            bulk_writer=bulk_writer,
            skip_actions=skip_actions,
            skip_sync=skip_sync,
            **pymongo_kwargs,
        )

    async def set(
        self,
        expression: dict[Any, Any],
        session: AsyncClientSession | None = None,
        bulk_writer: BulkWriter | None = None,
        skip_sync: bool | None = None,
        **kwargs: Any,
    ) -> "QSO":
        _, set_doc = self._row_hash_after_set(expression)
        return await super().set(
            set_doc,
            session=session,
            bulk_writer=bulk_writer,
            skip_sync=skip_sync,
            **kwargs,
        )

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
                name="operator_qso_compound",
            ),
            IndexModel(
                [("_operator", pymongo.ASCENDING)],
                name="operator_idx",
            ),
            IndexModel(
                [("_operator", pymongo.ASCENDING), ("_deleted", pymongo.ASCENDING)],
                name="operator_active_idx",
            ),
            IndexModel(
                [
                    ("_operator", pymongo.ASCENDING),
                    ("_created_at", pymongo.DESCENDING),
                ],
                name="operator_created_at_idx",
            ),
            IndexModel(
                [("rowHash", pymongo.ASCENDING)],
                name="row_hash_unique_idx",
                unique=True,
                sparse=True,
            ),
        ]
