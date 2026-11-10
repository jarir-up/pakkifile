"""A minimal text-only PDF writer for synthetic evidence, so no PDF library is needed.

Courier keeps columns aligned, so `pdftotext -layout` reads them back as a real export does.
Encryption is qpdf's job (ADR-0053).
"""

import subprocess
from collections.abc import Sequence
from pathlib import Path

PAGE_W, PAGE_H = 595, 842  # A4 in points
FONT_SIZE = 8
LEADING = 11
MARGIN = 36
LINES_PER_PAGE = (PAGE_H - 2 * MARGIN) // LEADING


def _escape(line: str) -> str:
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _content(lines: Sequence[str]) -> bytes:
    body = "\n".join(f"({_escape(line)}) Tj T*" for line in lines)
    start = f"BT /F1 {FONT_SIZE} Tf {LEADING} TL {MARGIN} {PAGE_H - MARGIN} Td"
    return f"{start}\n{body}\nET".encode("latin-1")


def write_pdf(pages: Sequence[Sequence[str]], path: Path) -> Path:
    """Write one page per list of text lines."""
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # the page tree, filled in once the page objects are numbered
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>",
    ]
    kids = []
    for lines in pages:
        stream = _content(lines)
        objects.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
        page_no = len(objects) + 1
        kids.append(f"{page_no} 0 R")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {page_no - 1} 0 R >>".encode()
        )
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>".encode()

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    path.write_bytes(bytes(out))
    return path


def encrypt(path: Path, password: str) -> Path:
    """Password-protect a PDF in place with AES-256, as banks send statements."""
    subprocess.run(
        ["qpdf", "--encrypt", password, password, "256", "--", "--replace-input", str(path)],
        check=True,
    )
    return path


def paginate(header: Sequence[str], rows: Sequence[str], first: Sequence[str]) -> list[list[str]]:
    """`first` opens page one; `header` repeats at the top of every page."""
    pages: list[list[str]] = []
    page = [*first, *header]
    for row in rows:
        if len(page) >= LINES_PER_PAGE:
            pages.append(page)
            page = list(header)
        page.append(row)
    pages.append(page)
    return pages
