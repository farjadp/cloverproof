"""HTML (Jinja2, `templates/pdf/`) -> PDF (WeasyPrint).

WeasyPrint is imported lazily: it needs system libraries (pango, gobject). Without them
the app still starts; only proof rendering fails, with `PdfUnavailable`.
Resources: only the self-hosted fonts and the logo in `static/` can be loaded; any
other URL (network, other files) stops the render.
"""

from __future__ import annotations

import mimetypes
import os
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any
from urllib.parse import unquote, urlparse

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from cloverproof_app import planning
from cloverproof_app.pdf.model import (
    HASH_STATEMENT,
    NO_SOIL_TEST,
    NOT_YET_VALIDATED,
    PLACEHOLDER_BANNER,
    TEMPLATE_VERSION,
    ProofInput,
    approval_line,
)

APP_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
ALLOWED_ASSETS = frozenset(
    {
        STATIC_DIR / "logo.svg",
        STATIC_DIR / "fonts" / "source-serif-4-latin-wght-normal.woff2",
        STATIC_DIR / "fonts" / "source-sans-3-latin-wght-normal.woff2",
        STATIC_DIR / "fonts" / "source-sans-3-latin-wght-italic.woff2",
    }
)
FORM_LABELS = {"N": "N", "NO3-N": "NO3-N", "P": "P", "P2O5": "P2O5", "K": "K", "K2O": "K2O"}
# One source for extraction-method labels (the app and the PDF must never drift: S1-exit D2).
METHOD_LABELS = planning.METHOD_LABELS


# fontTools (WeasyPrint's variable-font instancing and woff2 decoding) stamps the embedded
# font's `head.modified` with the current time unless SOURCE_DATE_EPOCH is set, which made
# identical inputs give different PDF bytes (and SHA-256) from one second to the next.
# A fixed value keeps the bytes reproducible. It is process-wide, which is fine: nothing
# else in the app reads it, and every render wants the same value.
FONT_TIMESTAMP_EPOCH = "1767225600"  # 2026-01-01T00:00:00Z, arbitrary but fixed


class PdfUnavailable(RuntimeError):
    """WeasyPrint or its system libraries cannot be loaded."""


class PdfRenderError(RuntimeError):
    """Rendering failed (e.g. the template asked for a resource outside the allow-list)."""


def _num(value: Any, digits: int = 1) -> str:
    return f"{float(value):,.{digits}f}"


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _plain(value: Any) -> str:
    """Inputs as entered: 6.0 -> "6", 12.5 -> "12.5"."""
    return f"{float(value):g}"


_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html"], default_for_string=True, default=True),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
_env.filters["num"] = _num
_env.filters["plain"] = _plain
_env.filters["utc"] = _utc


def render_html(proof: ProofInput) -> str:
    doc = proof.doc
    return _env.get_template("pdf/proof.html").render(
        p=proof,
        doc=doc,
        n=doc["nitrogen"],
        snap=doc["input_snapshot"],
        approval_line=approval_line(proof.approval) if proof.approval else None,
        banner=PLACEHOLDER_BANNER,
        no_soil_test=NO_SOIL_TEST,
        not_validated=NOT_YET_VALIDATED,
        hash_statement=HASH_STATEMENT,
        template_version=TEMPLATE_VERSION,
        form_labels=FORM_LABELS,
        method_labels=METHOD_LABELS,
    )


def load_weasyprint() -> ModuleType:
    os.environ["SOURCE_DATE_EPOCH"] = FONT_TIMESTAMP_EPOCH
    try:
        import weasyprint
    except (ImportError, OSError) as error:
        raise PdfUnavailable(
            "WeasyPrint cannot load its system libraries (pango). On macOS run with"
            " DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib."
        ) from error
    return weasyprint


def _fetcher(weasyprint: ModuleType) -> Any:
    from weasyprint.urls import URLFetcher, URLFetcherResponse

    class LocalAssets(URLFetcher):  # type: ignore[misc]
        """Serves the allow-listed static files; refuses everything else."""

        def __init__(self) -> None:
            super().__init__(allowed_protocols={"file"}, fail_on_errors=True)

        def fetch(self, url: str, headers: Any = None) -> Any:
            parsed = urlparse(url)
            path = Path(unquote(parsed.path)).resolve() if parsed.scheme == "file" else None
            if path is None or path not in ALLOWED_ASSETS:
                raise ValueError(f"proof PDF may not load {url!r}")
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            return URLFetcherResponse(url, path.read_bytes(), {"Content-Type": mime})

    return LocalAssets()


def render_pdf(proof: ProofInput) -> bytes:
    """The PDF bytes. Deterministic: no creation/modification date is written."""
    weasyprint = load_weasyprint()
    document = weasyprint.HTML(
        string=render_html(proof),
        base_url=STATIC_DIR.as_uri() + "/",
        url_fetcher=_fetcher(weasyprint),
    )
    from weasyprint.urls import FatalURLFetchingError

    try:
        data: bytes = document.write_pdf()
    except FatalURLFetchingError as error:  # a BaseException in WeasyPrint; keep it contained
        raise PdfRenderError("proof template referenced a resource that is not allowed") from error
    return data
