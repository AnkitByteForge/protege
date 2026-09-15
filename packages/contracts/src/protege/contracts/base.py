"""Shared base model and scalar aliases for every PROTÉGÉ contract.

Wire-compatibility rules (ARCHITECTURE.md §24):
- ``extra="ignore"`` — consumers ignore unknown fields, so payloads may gain
  fields additively within a major version without breaking older readers.
- ``frozen=True`` — contracts are values, not live objects; state lives in the
  authoritative service, never inside a contract instance.
- ``populate_by_name=True`` — the Python field name and the wire alias are both
  accepted on input, so the §38 worked example (which predates some field
  namings) validates verbatim.
"""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

JSONValue = str | int | float | bool | None | dict[str, Any] | list[Any]
"""Any JSON-encodable value. Used for open payloads (evidence, event, brief)
whose shapes are documented but intentionally open to additive extension."""

SchemaVersion = Annotated[str, StringConstraints(pattern=r"^\d+\.\d+$"), Field(examples=["1.0"])]
"""Envelope schema version (ARCHITECTURE.md §24). Additive-only within a
major; breaking changes publish ``_V2`` alongside for one release."""


class ProtegeBaseModel(BaseModel):
    """Base for all PROTÉGÉ contracts. See module docstring for the rules."""

    model_config = ConfigDict(extra="ignore", frozen=True, populate_by_name=True)
