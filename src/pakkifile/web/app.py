"""The local app (ADR-0052): served on this machine only, never beyond it."""

import argparse
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from typing import get_args
from urllib.parse import parse_qs

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import Connection

from pakkifile.figures.money import Money
from pakkifile.vault.classify import RowClass
from pakkifile.vault.db import vault_engine
from pakkifile.vault.review import ReviewError, awaiting_review, decide
from pakkifile.vault.schema import metadata
from pakkifile.web.templates import env

HOST = "127.0.0.1"
PORT = 8000
CLASSES: tuple[RowClass, ...] = get_args(RowClass)

Connect = Callable[[], AbstractContextManager[Connection]]


def create_app(
    connect: Connect, person_id: int, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
) -> FastAPI:
    """`connect` opens one transaction per request; `person_id` is whose vault this is."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/", response_class=HTMLResponse)
    def review_page() -> str:
        with connect() as conn:
            rows = awaiting_review(conn, person_id)
        return env.get_template("review.html").render(
            rows=[(row, Money(row.amount_minor, row.currency).display()) for row in rows],
            classes=CLASSES,
        )

    @app.post("/")
    async def save(request: Request) -> RedirectResponse:
        form = parse_qs((await request.body()).decode())
        chosen = {
            int(field.removeprefix("row-")): values[0]
            for field, values in form.items()
            if field.removeprefix("row-").isdigit() and values[0] in CLASSES
        }
        with connect() as conn:
            for row_id, row_class in chosen.items():
                try:
                    decide(conn, person_id, row_id, row_class, clock())
                except ReviewError:
                    continue  # decided already, from another tab or a resubmit: keep the rest
        return RedirectResponse("/", status_code=303)

    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--person", type=int, required=True)
    args = parser.parse_args()
    engine = vault_engine()
    metadata.create_all(engine)  # missing tables only; migrations wait for a release (ADR-0055)
    uvicorn.run(create_app(engine.begin, args.person), host=HOST, port=PORT)


if __name__ == "__main__":
    main()
