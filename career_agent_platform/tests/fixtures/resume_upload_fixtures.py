"""In-memory resume file fixtures for upload extraction tests."""

from __future__ import annotations

from io import BytesIO


def _escape_pdf_literal(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf_bytes(text: str) -> bytes:
    """Build a minimal PDF with extractable text (deterministic, no external tools)."""
    safe = _escape_pdf_literal(text.strip()[:500])
    safe = safe.encode("ascii", errors="replace").decode("ascii")
    stream = f"BT /F1 12 Tf 72 720 Td ({safe}) Tj ET"
    stream_bytes = stream.encode("latin-1")
    objects: list[bytes] = []

    def add_obj(body: str) -> int:
        objects.append(body.encode("latin-1"))
        return len(objects)

    add_obj("<< /Type /Catalog /Pages 2 0 R >>")
    add_obj("<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    add_obj(
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    )
    add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(
        f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin-1")
        + stream_bytes
        + b"\nendstream",
    )

    header = b"%PDF-1.4\n"
    body = bytearray(header)
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(body))
        body.extend(f"{idx} 0 obj\n".encode("latin-1"))
        body.extend(obj)
        body.extend(b"\nendobj\n")

    xref_start = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    body.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        body.extend(f"{off:010d} 00000 n \n".encode("latin-1"))
    body.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n".encode("latin-1"),
    )
    return bytes(body)


def make_docx_bytes(text: str) -> bytes:
    from docx import Document

    buf = BytesIO()
    doc = Document()
    for line in text.strip().splitlines():
        if line.strip():
            doc.add_paragraph(line.strip())
    doc.save(buf)
    return buf.getvalue()
