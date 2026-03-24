"""Document-layer interfaces consumed by DocWright Core.

The document layer is intentionally externalizable. Core should rely on these
interfaces instead of parser-specific implementations.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(slots=True, frozen=True)
class NodeRelationRef:
    """Transportable reference to a related node."""

    relation_id: str
    kind: str
    target_id: str
    score: float | None = None


@dataclass(slots=True, frozen=True)
class NodeContextSlice:
    """Resolved nearby node IDs around a focus node."""

    focus_node_id: str
    before_node_ids: tuple[str, ...] = field(default_factory=tuple)
    after_node_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class TextSearchHit:
    """Structured keyword-search result over runtime-visible document nodes."""

    node_id: str
    page_number: int
    text_preview: str
    match_count: int = 1


@runtime_checkable
class DocumentHandle(Protocol):
    """Core-facing document handle protocol."""

    @property
    def document_id(self) -> str:
        """Stable document identifier."""

    @property
    def reading_order(self) -> Sequence[str]:
        """Stable runtime traversal order of node IDs."""

    def get_page(self, page_number: int) -> PageHandle:
        """Return a page handle for the given page number."""

    def get_node(self, node_id: str) -> NodeHandle:
        """Resolve a node handle by stable node ID."""

    def get_context(self, node_id: str, *, before: int = 1, after: int = 1) -> NodeContextSlice:
        """Return nearby node IDs for a focus node."""


@runtime_checkable
class PageHandle(Protocol):
    """Core-facing page handle protocol."""

    @property
    def page_number(self) -> int:
        """One-based page number."""

    @property
    def node_ids(self) -> Sequence[str]:
        """Stable node IDs present on the page."""

    def get_node(self, node_id: str) -> NodeHandle:
        """Resolve a node on the page by stable node ID."""


@runtime_checkable
class NodeHandle(Protocol):
    """Core-facing node handle protocol."""

    @property
    def node_id(self) -> str:
        """Stable node identifier."""

    @property
    def kind(self) -> str:
        """Runtime-visible node kind."""

    @property
    def page_number(self) -> int:
        """One-based page number containing the node when available."""

    def text_content(self) -> str | None:
        """Return node text when available."""

    def relations(self) -> Sequence[NodeRelationRef]:
        """Return related node references when available."""
