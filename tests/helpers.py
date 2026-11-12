import json
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from pakkifile.llm.ollama import LocalModel
from pakkifile.registry.files import load_registry
from pakkifile.registry.model import Registry, RegistryEntry

REGISTRY: Registry = load_registry(Path("registry-data"))
ISLAMABAD = "German Embassy Islamabad"
KARACHI = "Consulate General of Germany, Karachi"
# The date the registry data was retrieved and verified; keeps confidence stable in tests.
AS_OF = date(2026, 10, 30)


def entry(authority: str, purpose: str) -> RegistryEntry:
    return next(
        e
        for e in REGISTRY.entries
        if e.authority.name == authority and e.application.purpose == purpose
    )


def islamabad_study() -> RegistryEntry:
    """The tracer's entry."""
    return entry(ISLAMABAD, "study")


class FakeOllama:
    """A local stand-in for Ollama's chat endpoint that records each request."""

    def __init__(self, content: str = "") -> None:
        self.content = content
        self.status = 200
        self.reply: Any = None
        self.prompt_tokens = 100
        self.done_reason = "stop"
        self.requests: list[dict[str, Any]] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers["Content-Length"])
                fake.requests.append(json.loads(self.rfile.read(length)))
                reply = fake.reply or {
                    "message": {"content": fake.content},
                    "done_reason": fake.done_reason,
                    "prompt_eval_count": fake.prompt_tokens,
                }
                self.send_response(fake.status)
                self.end_headers()
                self.wfile.write(json.dumps(reply).encode())

            def log_message(self, *args: object) -> None:
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def model(self) -> LocalModel:
        return LocalModel("test-model", f"http://127.0.0.1:{self.server.server_port}")
