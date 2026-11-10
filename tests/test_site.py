import subprocess
import sys
from pathlib import Path

from pakkifile.web.site import build_site, entry_path
from tests.helpers import AS_OF, ISLAMABAD, REGISTRY, entry

# web.dossier renders applicant figures, so the web modules are named one by one.
SITE_MODULES = ("pakkifile.registry", "pakkifile.sources")
SITE_WEB = {
    "pakkifile.web",
    "pakkifile.web.checklist",
    "pakkifile.web.site",
    "pakkifile.web.templates",
}


def test_each_entry_gets_a_page_by_authority_application_and_profile(tmp_path: Path) -> None:
    build_site(REGISTRY, tmp_path, AS_OF)
    study = entry(ISLAMABAD, "study")
    assert entry_path(study) == Path(
        "german-embassy-islamabad/study-visa-d/self-funded-freelancer.html"
    )
    page = (tmp_path / entry_path(study)).read_text()
    assert page.count('class="requirement"') == len(study.requirements)
    assert len({entry_path(e) for e in REGISTRY.entries}) == len(REGISTRY.entries)


def test_index_links_every_entry(tmp_path: Path) -> None:
    build_site(REGISTRY, tmp_path, AS_OF)
    index = (tmp_path / "index.html").read_text()
    for e in REGISTRY.entries:
        assert f'href="{entry_path(e).as_posix()}"' in index
    assert index.count("<h2>") == len({e.authority.name for e in REGISTRY.entries})


def test_command_writes_the_site(tmp_path: Path) -> None:
    subprocess.run([sys.executable, "-m", "pakkifile.web.site", "--out", str(tmp_path)], check=True)
    assert (tmp_path / "index.html").exists()
    assert len(list(tmp_path.glob("*/*/*.html"))) == len(REGISTRY.entries)


def test_site_build_imports_only_registry_sources_and_web() -> None:
    # R-22: the site build never loads code that handles applicant documents.
    loaded = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, pakkifile.web.site; print(*sorted(sys.modules), sep=chr(10))",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    ours = [m for m in loaded if m.startswith("pakkifile.")]
    assert "pakkifile.web.dossier" not in ours
    assert "pakkifile.web.site" in ours
    assert all(m.startswith(SITE_MODULES) or m in SITE_WEB for m in ours), ours


def test_entry_page_names_the_applicant_profile(tmp_path: Path) -> None:
    build_site(REGISTRY, tmp_path, AS_OF)
    study = entry(ISLAMABAD, "study")
    page = (tmp_path / entry_path(study)).read_text()
    assert f"{study.application.label} · {study.applicant_profile}</h1>" in page
