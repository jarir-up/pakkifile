"""Registry schema: requirements typed and cited (FR-2, R-21)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

RequirementType = Literal["mandatory", "conditional", "optional"]


class Source(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    document: str
    section: str
    url: str
    retrieved: date
    last_verified: date
    checksum: str


class Requirement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    text: str
    type: RequirementType
    condition: str | None
    source: Source


class RegistryEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    authority: str
    application: str
    applicant_profile: str
    requirements: tuple[Requirement, ...]
