import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from pakkifile.sources.fetch import fetch, text_checksum

PAGE = b"<html><body><h2>Mandatory documents</h2><ul><li>Degree transcripts</li></ul></body></html>"


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def server_url() -> Iterator[str]:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/page"
    server.shutdown()


def test_fetch_returns_body_and_checksum(server_url: str) -> None:
    fetched = fetch(server_url)
    assert fetched.body == PAGE.decode()
    assert fetched.checksum == text_checksum(PAGE.decode())


def test_checksum_ignores_markup_and_whitespace() -> None:
    a = "<ul><li>Degree transcripts</li></ul>"
    b = "<ul>\n  <li>Degree   transcripts</li>\n</ul>"
    assert text_checksum(a) == text_checksum(b)


def test_checksum_changes_when_text_changes() -> None:
    assert text_checksum("<li>Degree transcripts</li>") != text_checksum(
        "<li>Degree certificates</li>"
    )
