"""Fetch official sources and checksum their normalised text (ADR-0036)."""

import hashlib
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
    return " ".join(" ".join(collector.parts).split())


def text_checksum(html: str) -> str:
    return hashlib.sha256(normalised_text(html).encode()).hexdigest()


@dataclass(frozen=True)
class FetchedSource:
    url: str
    retrieved: date
    body: str
    checksum: str


def fetch(url: str, timeout: float = 30) -> FetchedSource:
    request = urllib.request.Request(url, headers={"User-Agent": "PakkiFile registry"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode(response.headers.get_content_charset() or "utf-8")
    return FetchedSource(url, datetime.now(UTC).date(), body, text_checksum(body))
