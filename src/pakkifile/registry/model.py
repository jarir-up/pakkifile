"""Registry schema: requirements typed and cited (FR-2, R-21, ADR-0038, ADR-0043)."""

from collections.abc import Mapping
from datetime import date
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

RequirementType = Literal["mandatory", "conditional", "optional"]
VisaCategory = Literal["C", "D"]
SourceAuthority = Literal[
    "official_checklist", "consulate_page", "service_provider_page", "agent", "community_story"
]
# GLOSSARY "Source authority", highest first.
AUTHORITY_ORDER: tuple[SourceAuthority, ...] = (
    "official_checklist",
    "consulate_page",
    "service_provider_page",
    "agent",
    "community_story",
)
Stance = Literal["supports", "conflicts"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Source(_Frozen):
    document: str
    url: str
    published: date | None = None
    retrieved: date
    last_verified: date
    source_authority: SourceAuthority
    checksum: str | None = None


class Citation(_Frozen):
    source: str
    section: str
    stance: Stance = "supports"


class Requirement(_Frozen):
    id: str
    text: str
    type: RequirementType
    condition: str | None = None
    citations: Annotated[tuple[Citation, ...], Field(min_length=1)]

    def cited(self, sources: Mapping[str, Source], stance: Stance) -> list[Source]:
        return [sources[c.source] for c in self.citations if c.stance == stance]

    @model_validator(mode="after")
    def _has_support(self) -> Self:
        if not any(c.stance == "supports" for c in self.citations):
            raise ValueError(f"{self.id}: needs at least one supporting citation")
        return self


class Authority(_Frozen):
    name: str
    kind: Literal["embassy", "consulate"]
    authority_class: str


class Application(_Frozen):
    name: str
    purpose: str
    visa_category: VisaCategory | None

    @property
    def label(self) -> str:
        return f"{self.name} ({self.visa_category})" if self.visa_category else self.name


class RegistryEntry(_Frozen):
    authority: Authority
    application: Application
    applicant_profile: str
    requirements: tuple[Requirement, ...]


class Registry(_Frozen):
    sources: Mapping[str, Source]
    entries: tuple[RegistryEntry, ...]

    @model_validator(mode="after")
    def _citations_resolve(self) -> Self:
        for entry in self.entries:
            for req in entry.requirements:
                missing = [c.source for c in req.citations if c.source not in self.sources]
                if missing:
                    raise ValueError(f"{req.id}: unknown sources {missing}")
        return self
