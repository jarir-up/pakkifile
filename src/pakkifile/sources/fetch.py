"""Fetch official sources and checksum their normalised text (ADR-0036, ADR-0044)."""

import hashlib
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import UTC, date, datetime
from html.parser import HTMLParser


class _TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def normalised_text(html: str) -> str:
    collector = _TextCollector()
    collector.feed(html)
    collector.close()
    return " ".join(" ".join(collector.parts).split())


def _checksum(normalised: str) -> str:
    return hashlib.sha256(normalised.encode()).hexdigest()


def text_checksum(html: str) -> str:
    return _checksum(normalised_text(html))


@dataclass(frozen=True)
class FetchedSource:
    url: str
    retrieved: date
    body: str
    checksum: str
    has_text: bool


def _pdf_text(pdf: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(pdf)
        f.flush()
        return subprocess.run(
            ["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True, check=True
        ).stdout


def fetch(url: str, timeout: float = 30) -> FetchedSource:
    request = urllib.request.Request(url, headers={"User-Agent": "PakkiFile registry"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
    if raw.startswith(b"%PDF"):
        body = _pdf_text(raw)
        # PDF text is not markup: an HTML parser would drop whatever follows a stray "<".
        normalised = " ".join(body.split())
    else:
        body = raw.decode(charset)
        normalised = normalised_text(body)
    return FetchedSource(
        url, datetime.now(UTC).date(), body, _checksum(normalised), bool(normalised)
    )
