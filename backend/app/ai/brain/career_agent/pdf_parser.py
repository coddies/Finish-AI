"""
pdf_parser.py — PDF text extraction with < 50 char scanned-image validation.
"""
from __future__ import annotations

import pathlib

from pypdf import PdfReader

from career_agent.config import PDF_MIN_CHARS

# Message returned when PDF is scanned / image-based
SCANNED_PDF_MSG: str = (
    "The PDF appears to be scanned or image-based. "
    "Please upload a searchable text PDF or paste your text directly."
)


def extract_pdf_text(pdf_path: str | pathlib.Path) -> str:
    """
    Extract plain text from a PDF file page by page.

    Args:
        pdf_path: Absolute or relative path to the target PDF file.

    Returns:
        Full extracted text if >= PDF_MIN_CHARS characters, otherwise
        SCANNED_PDF_MSG indicating the file is image-based.

    Raises:
        FileNotFoundError: If the file does not exist at the given path.
        ValueError: If the file is not a .pdf or pypdf fails to parse it.
    """
    path = pathlib.Path(pdf_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Expected a .pdf file, received: '{path.suffix}'. "
            "Please provide a valid PDF file."
        )

    try:
        reader = PdfReader(str(path))
        pages_text: list[str] = []

        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            pages_text.append(page_text)

        full_text = "\n".join(pages_text).strip()

    except Exception as exc:
        raise ValueError(f"Failed to parse PDF '{path.name}': {exc}") from exc

    # Scanned / image-based PDF check
    if len(full_text) < PDF_MIN_CHARS:
        return SCANNED_PDF_MSG

    return full_text


def get_pdf_metadata(pdf_path: str | pathlib.Path) -> dict[str, str | int]:
    """
    Extract basic metadata from a PDF (author, title, page count).

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Dictionary with keys: title, author, page_count.
    """
    path = pathlib.Path(pdf_path).resolve()
    try:
        reader = PdfReader(str(path))
        meta = reader.metadata or {}
        return {
            "title": str(meta.get("/Title", "Unknown")),
            "author": str(meta.get("/Author", "Unknown")),
            "page_count": len(reader.pages),
        }
    except Exception:
        return {"title": "Unknown", "author": "Unknown", "page_count": 0}
