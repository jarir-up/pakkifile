"""Turn one official source into one registry entry."""

import re
from dataclasses import dataclass
from datetime import date

from pakkifile.registry.model import RegistryEntry, Requirement, Source
from pakkifile.sources.extract import extract_section
from pakkifile.sources.fetch import text_checksum


@dataclass(frozen=True)
class SourceSpec:
    authority: str
    application: str
    applicant_profile: str
    document: str
    section: str
    url: str
    retrieved: date


TRACER_SOURCE = SourceSpec(
    authority="German Embassy Islamabad",
    application="Study visa (D)",
    applicant_profile="Self-funded freelancer",
    document="Study visa, German Missions in Pakistan (27.11.2025)",
    section="Mandatory documents",
    url="https://pakistan.diplo.de/pk-en/service/2-study-visa-seite-1676104",
    retrieved=date(2026, 10, 30),
)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def build_entry(html: str, spec: SourceSpec, verified: date) -> RegistryEntry:
    source = Source(
        document=spec.document,
        section=spec.section,
        url=spec.url,
        retrieved=spec.retrieved,
        last_verified=verified,
        checksum=text_checksum(html),
    )
    requirements = tuple(
        Requirement(
            id=_slug(item.text),
            text=item.text,
            type=item.type,
            condition=item.condition,
            source=source,
        )
        for item in extract_section(html, spec.section)
    )
    return RegistryEntry(
        authority=spec.authority,
        application=spec.application,
        applicant_profile=spec.applicant_profile,
        requirements=requirements,
    )
