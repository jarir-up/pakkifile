"""Turn one official source into one registry entry."""

import re
from dataclasses import dataclass
from datetime import date

from pakkifile.registry.model import (
    Application,
    Authority,
    Citation,
    RegistryEntry,
    Requirement,
    Source,
    SourceAuthority,
)
from pakkifile.sources.extract import extract_section
from pakkifile.sources.fetch import text_checksum


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    authority: Authority
    application: Application
    applicant_profile: str
    document: str
    section: str
    url: str
    published: date | None
    retrieved: date
    source_authority: SourceAuthority


TRACER_SOURCE = SourceSpec(
    source_id="de-missions-pk-study-visa-page",
    authority=Authority(
        name="German Embassy Islamabad", kind="embassy", authority_class="Schengen missions"
    ),
    application=Application(name="Study visa", purpose="study", visa_category="D"),
    applicant_profile="Self-funded freelancer",
    document="Study visa, German Missions in Pakistan",
    section="Mandatory documents",
    url="https://pakistan.diplo.de/pk-en/service/2-study-visa-seite-1676104",
    published=date(2025, 11, 27),
    retrieved=date(2026, 10, 30),
    source_authority="consulate_page",
)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def build_entry(html: str, spec: SourceSpec, verified: date) -> tuple[RegistryEntry, Source]:
    """Return the entry and the source it cites, to be stored under `spec.source_id`."""
    source = Source(
        document=spec.document,
        url=spec.url,
        published=spec.published,
        retrieved=spec.retrieved,
        last_verified=verified,
        checksum=text_checksum(html),
        source_authority=spec.source_authority,
    )
    requirements = tuple(
        Requirement(
            id=_slug(item.text),
            text=item.text,
            type=item.type,
            condition=item.condition,
            citations=(Citation(source=spec.source_id, section=spec.section),),
        )
        for item in extract_section(html, spec.section)
    )
    entry = RegistryEntry(
        authority=spec.authority,
        application=spec.application,
        applicant_profile=spec.applicant_profile,
        requirements=requirements,
    )
    return entry, source
