import threading
from collections.abc import Iterator
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from pakkifile.registry.files import load_sources, save_sources
from pakkifile.registry.model import Source
from pakkifile.sources.check import check_sources, run
from pakkifile.sources.fetch import text_checksum

AS_OF = date(2026, 11, 9)
EARLIER = date(2026, 10, 30)
PAGE = "<html><body><ul><li>Degree transcripts</li></ul></body></html>"


class _Site:
    def __init__(self) -> None:
        self.pages: dict[str, tuple[int, bytes]] = {}
        self.headers: dict[str, str] = {}
        site = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                status, body = site.pages.get(self.path, (404, b""))
                self.send_response(status)
                if self.path in site.headers:
                    self.send_header("Content-Type", site.headers[self.path])
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args: object) -> None:
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


@pytest.fixture
def site() -> Iterator[_Site]:
    s = _Site()
    yield s
    s.server.shutdown()


def _source(url: str, checksum: str | None) -> Source:
    return Source(
        document="d",
        url=url,
        retrieved=EARLIER,
        last_verified=EARLIER,
        source_authority="consulate_page",
        checksum=checksum,
    )


def _pdf(text: str) -> bytes:
    """A one-page PDF, written by hand."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
        b"/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>>>",
        b"<</Length %d>>stream\n%s\nendstream" % (len(stream), stream),
    ]
    pdf = b"%PDF-1.4\n"
    for i, body in enumerate(objects, 1):
        pdf += b"%d 0 obj\n%s\nendobj\n" % (i, body)
    return pdf + b"trailer<</Root 1 0 R>>\n"


def test_unchanged_source_only_moves_last_verified(site: _Site) -> None:
    site.pages["/a"] = (200, PAGE.encode())
    before = _source(f"{site.url}/a", text_checksum(PAGE))
    check = check_sources({"a": before}, AS_OF)["a"]
    assert check.status == "unchanged"
    assert check.source == before.model_copy(update={"last_verified": AS_OF})


def test_whitespace_change_counts_as_unchanged(site: _Site) -> None:
    site.pages["/a"] = (200, b"<ul>\n  <li>Degree    transcripts</li>\n</ul>")
    before = _source(f"{site.url}/a", text_checksum(PAGE))
    assert check_sources({"a": before}, AS_OF)["a"].status == "unchanged"


def test_changed_source_is_reported_and_left_as_it_was(site: _Site) -> None:
    site.pages["/a"] = (200, b"<li>Degree certificates</li>")
    before = _source(f"{site.url}/a", text_checksum(PAGE))
    check = check_sources({"a": before}, AS_OF)["a"]
    assert check.status == "changed"
    assert check.source == before
    assert check.text is not None and "Degree certificates" in check.text


def test_new_source_records_its_first_checksum_and_retrieval(site: _Site) -> None:
    site.pages["/a"] = (200, PAGE.encode())
    check = check_sources({"a": _source(f"{site.url}/a", None)}, AS_OF)["a"]
    assert check.status == "new"
    assert check.source.checksum == text_checksum(PAGE)
    assert check.source.retrieved == AS_OF
    assert check.source.last_verified == AS_OF


def test_refused_fetch_is_reported_and_left_as_it_was(site: _Site) -> None:
    site.pages["/a"] = (403, b"")
    before = _source(f"{site.url}/a", "abc")
    check = check_sources({"a": before}, AS_OF)["a"]
    assert check.status == "failed"
    assert check.source == before
    assert check.error is not None and "403" in check.error


def test_undecodable_page_fails_only_that_source(site: _Site) -> None:
    site.pages["/bad"] = (200, b"\xff\xfe not utf-8")
    site.pages["/ok"] = (200, PAGE.encode())
    sources = {
        "bad": _source(f"{site.url}/bad", "abc"),
        "ok": _source(f"{site.url}/ok", text_checksum(PAGE)),
    }
    checks = check_sources(sources, AS_OF)
    assert (checks["bad"].status, checks["ok"].status) == ("failed", "unchanged")


def test_unknown_charset_fails_only_that_source(site: _Site) -> None:
    site.pages["/a"] = (200, PAGE.encode())
    site.headers["/a"] = "text/html; charset=not-a-charset"
    assert check_sources({"a": _source(f"{site.url}/a", "abc")}, AS_OF)["a"].status == "failed"


def test_page_without_text_never_counts_as_verified(site: _Site) -> None:
    site.pages["/a"] = (200, b"<html><body></body></html>")
    before = _source(f"{site.url}/a", None)
    check = check_sources({"a": before}, AS_OF)["a"]
    assert check.status == "failed"
    assert check.source == before


def test_pdf_text_comes_from_pdftotext(site: _Site) -> None:
    site.pages["/a.pdf"] = (200, _pdf("Degree transcripts"))
    check = check_sources({"a": _source(f"{site.url}/a.pdf", None)}, AS_OF)["a"]
    assert check.status == "new"
    assert check.source.checksum == text_checksum("Degree transcripts")


def test_pdf_change_after_an_angle_bracket_is_detected(site: _Site) -> None:
    site.pages["/a.pdf"] = (200, _pdf("if a <b then 10,236 euro"))
    baseline = check_sources({"a": _source(f"{site.url}/a.pdf", None)}, AS_OF)["a"].source
    site.pages["/a.pdf"] = (200, _pdf("if a <b then 11,904 euro"))
    assert check_sources({"a": baseline}, AS_OF)["a"].status == "changed"


def test_changed_page_text_is_readable_without_navigation_or_markup(site: _Site) -> None:
    site.pages["/a"] = (
        200,
        b"<nav>Home</nav><h2>Required</h2><ul><li>Passport</li><li>Photo</li></ul>"
        b"<script>x()</script><footer>Imprint</footer>",
    )
    check = check_sources({"a": _source(f"{site.url}/a", "old")}, AS_OF)["a"]
    assert check.text == "Required\nPassport\nPhoto"


def test_run_saves_what_the_check_learned(site: _Site, tmp_path: Path) -> None:
    site.pages["/a"] = (200, PAGE.encode())
    save_sources({"a": _source(f"{site.url}/a", text_checksum(PAGE))}, tmp_path / "sources.yaml")
    assert run(tmp_path, AS_OF)["a"].status == "unchanged"
    assert load_sources(tmp_path / "sources.yaml")["a"].last_verified == AS_OF
