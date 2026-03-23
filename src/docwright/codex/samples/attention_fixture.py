"""Optional packaged sample using the prepared Attention document IR fixture.

This sample is intentionally separate from the main bridge so the primary
DocWright package entry stays generic. It is only a convenience helper for
demos and tests.
"""

from __future__ import annotations

from pathlib import Path

from docwright.codex.entry import DocWrightCodexEntry
from docwright.document.ir_loader import load_in_memory_document_from_ir_path

FIXTURE_PATH = (
    Path(__file__).resolve().parents[4]
    / "tests"
    / "fixtures"
    / "document_ir"
    / "attention_is_all_you_need.document_ir.json"
)


def build_attention_fixture_entry(**entry_kwargs: object) -> DocWrightCodexEntry:
    """Create a DocWright Codex entry from the prepared Attention IR fixture.

    ``entry_kwargs`` are forwarded to ``DocWrightCodexEntry.from_document`` so
    callers can choose capability, IDs, permissions, or compilers without
    binding the main bridge to this specific fixture.
    """

    document = load_in_memory_document_from_ir_path(FIXTURE_PATH)
    return DocWrightCodexEntry.from_document(document, **entry_kwargs)
