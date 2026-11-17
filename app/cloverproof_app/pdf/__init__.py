"""Proof PDF v0 (see `model.py` for the wording rules, `render.py` for WeasyPrint)."""

from cloverproof_app.pdf.model import (
    AI_ACTOR,
    FORBIDDEN_PHRASES,
    HASH_STATEMENT,
    HUMAN_ACTOR,
    NOT_YET_VALIDATED,
    PLACEHOLDER_PACK_BANNER,
    TEMPLATE_VERSION,
    Approval,
    ProofInput,
    approval_line,
)
from cloverproof_app.pdf.render import PdfUnavailable, render_html, render_pdf

__all__ = [
    "AI_ACTOR",
    "FORBIDDEN_PHRASES",
    "HASH_STATEMENT",
    "HUMAN_ACTOR",
    "NOT_YET_VALIDATED",
    "PLACEHOLDER_PACK_BANNER",
    "TEMPLATE_VERSION",
    "Approval",
    "PdfUnavailable",
    "ProofInput",
    "approval_line",
    "render_html",
    "render_pdf",
]
