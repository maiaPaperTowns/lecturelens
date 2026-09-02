"""Text extraction from PDF / TXT / Markdown / image source files.

Images (and scanned PDFs) go through Tesseract OCR via ``pytesseract`` , this
keeps the pipeline fully offline (no OCR API).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.core.exceptions import InvalidFileError
from app.core.logging import get_logger

logger = get_logger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", *IMAGE_EXTENSIONS}
EXTENSION_TO_TYPE = {
    ".pdf": "pdf",
    ".txt": "txt",
    ".md": "md",
    ".markdown": "md",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
}

# minimum characters an OCR pass must yield before we treat the result as usable
_MIN_OCR_CHARS = 24


@dataclass
class PageContent:
    """One logical page of a document (a real page for PDFs, the whole file otherwise)."""

    page_number: int
    text: str
    kind: str = "page"  # page | slide | document | image


@dataclass
class ExtractedDocument:
    file_name: str
    file_type: str
    pages: list[PageContent] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)

    @property
    def page_count(self) -> int:
        return len(self.pages)


def detect_file_type(file_name: str) -> str:
    ext = Path(file_name).suffix.lower()
    if ext not in EXTENSION_TO_TYPE:
        raise InvalidFileError(
            f"Unsupported file type '{ext or 'unknown'}'. "
            f"Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    return EXTENSION_TO_TYPE[ext]


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------
def _ocr(image) -> str:
    """Run Tesseract on a PIL image, returning cleaned text."""
    try:
        import pytesseract
    except ImportError as exc:  # pragma: no cover - dependency guaranteed in prod
        raise InvalidFileError("Image support is unavailable (pytesseract not installed).") from exc

    try:
        text = pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError as exc:
        raise InvalidFileError(
            "Image OCR is unavailable: the Tesseract binary is not installed on the server."
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise InvalidFileError(f"OCR failed: {exc}") from exc
    return text.strip()


def _extract_image(path: Path) -> list[PageContent]:
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:  # pragma: no cover
        raise InvalidFileError("Image support is unavailable (Pillow not installed).") from exc

    try:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img).convert("L")
            text = _ocr(img)
    except InvalidFileError:
        raise
    except Exception as exc:
        raise InvalidFileError(f"Could not read image: {exc}") from exc

    if len(text) < _MIN_OCR_CHARS:
        raise InvalidFileError(
            "No readable text was detected in this image. Use a sharper, higher-contrast scan."
        )
    return [PageContent(page_number=1, text=text, kind="image")]


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
def _extract_pdf(path: Path) -> list[PageContent]:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover - dependency guaranteed in prod
        raise InvalidFileError("PDF support is unavailable (PyMuPDF not installed).") from exc

    pages: list[PageContent] = []
    try:
        with fitz.open(path) as doc:
            slide_like = _looks_like_slides(doc)
            for i, page in enumerate(doc, start=1):
                text = page.get_text("text") or ""
                pages.append(
                    PageContent(page_number=i, text=text, kind="slide" if slide_like else "page")
                )
            if not any(p.text.strip() for p in pages):
                pages = _ocr_pdf(doc)
    except InvalidFileError:
        raise
    except Exception as exc:
        raise InvalidFileError(f"Could not read PDF: {exc}") from exc

    if not any(p.text.strip() for p in pages):
        raise InvalidFileError("No extractable text found in this PDF, even after OCR.")
    return pages


def _ocr_pdf(doc) -> list[PageContent]:
    """Rasterise each page and OCR it (used for scanned / image-only PDFs)."""
    try:
        import fitz
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise InvalidFileError("Scanned-PDF OCR needs Pillow, which is not installed.") from exc

    logger.info("PDF has no text layer, falling back to OCR (%d pages)", len(doc))
    pages: list[PageContent] = []
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
        pages.append(PageContent(page_number=i, text=_ocr(img), kind="page"))
    return pages


def _looks_like_slides(doc) -> bool:
    """Heuristic: slide decks tend to have wide pages and little text per page."""
    try:
        first = doc[0]
        wide = first.rect.width >= first.rect.height
        avg_chars = sum(len(p.get_text("text") or "") for p in doc) / max(len(doc), 1)
        return wide and avg_chars < 900
    except Exception:
        return False


def _extract_plaintext(path: Path, file_type: str) -> list[PageContent]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if not raw.strip():
        raise InvalidFileError("The uploaded file is empty.")
    return [PageContent(page_number=1, text=raw, kind="document")]


def extract_document(path: str | Path, file_name: str | None = None) -> ExtractedDocument:
    """Extract text from a file on disk, returning page-aware content."""
    path = Path(path)
    if not path.exists():
        raise InvalidFileError(f"File not found: {path}")
    name = file_name or path.name
    file_type = detect_file_type(name)

    if file_type == "pdf":
        pages = _extract_pdf(path)
    elif file_type == "image":
        pages = _extract_image(path)
    else:
        pages = _extract_plaintext(path, file_type)

    logger.info("Extracted %s (%s) -> %d page(s)", name, file_type, len(pages))
    return ExtractedDocument(file_name=name, file_type=file_type, pages=pages)
