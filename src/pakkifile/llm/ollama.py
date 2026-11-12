"""A local model served by Ollama (ADR-0012): the one way this project calls a model."""

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Self

DEFAULT_URL = "http://127.0.0.1:11434"
TIMEOUT_SECONDS = 3600


class ModelError(Exception):
    """The model was unavailable, or its reply can't be used."""


@dataclass(frozen=True)
class LocalModel:
    name: str
    url: str = DEFAULT_URL
    think: bool | None = None

    @classmethod
    def from_env(cls, model_var: str, think_var: str, think: bool | None = None) -> Self:
        """The model named in `model_var`; `think_var` ("on" or "off") overrides `think`."""
        name = os.environ.get(model_var)
        if not name:
            raise ModelError(f"{model_var} is not set")
        think = {"on": True, "off": False}.get(os.environ.get(think_var, ""), think)
        return cls(name, os.environ.get("PAKKIFILE_OLLAMA_URL", DEFAULT_URL), think)


@dataclass(frozen=True)
class Reply:
    content: str
    finished: str
    prompt_tokens: int


def chat(model: LocalModel, body: dict[str, Any]) -> Reply:
    """Send one chat request; `body` gets the model's name and thinking setting.

    Applicant text must pass through `llm.redact` before it is put in `body` (R-27).
    """
    body = {**body, "model": model.name, "stream": False}
    if model.think is not None:
        body["think"] = model.think
    request = urllib.request.Request(
        f"{model.url}/api/chat",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            reply = json.load(response)
        return Reply(
            str(reply["message"]["content"]),
            reply["done_reason"],
            reply.get("prompt_eval_count", 0),
        )
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise ModelError(f"{model.name}: no usable reply: {error!r}") from error
