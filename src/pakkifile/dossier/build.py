"""Order a dossier the way the authority's checklist is ordered."""

from dataclasses import dataclass

from pakkifile.figures.continuity import UnattributedCredit
from pakkifile.registry.model import RegistryEntry, Requirement


@dataclass(frozen=True)
class EvidenceLink:
    requirement_id: str
    file_name: str
    figure: UnattributedCredit | None


@dataclass(frozen=True)
class DossierItem:
    requirement: Requirement
    evidence: EvidenceLink | None


@dataclass(frozen=True)
class Dossier:
    authority: str
    application: str
    applicant: str
    items: tuple[DossierItem, ...]


def build_dossier(entry: RegistryEntry, applicant: str, links: list[EvidenceLink]) -> Dossier:
    by_requirement = {link.requirement_id: link for link in links}
    return Dossier(
        authority=entry.authority,
        application=entry.application,
        applicant=applicant,
        items=tuple(DossierItem(r, by_requirement.get(r.id)) for r in entry.requirements),
    )
