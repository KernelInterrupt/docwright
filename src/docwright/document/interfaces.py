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
    """Resolved nearby reading-order node IDs around a focus node."""

    focus_node_id: str
    before_node_ids: tuple[str, ...] = field(default_factory=tuple)
    after_node_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class NodeStructureSlice:
    """Resolved hierarchy/navigation metadata around a focus node."""

    focus_node_id: str
    root_id: str | None = None
    parent_node_id: str | None = None
    child_node_ids: tuple[str, ...] = field(default_factory=tuple)
    sibling_node_ids: tuple[str, ...] = field(default_factory=tuple)
    ancestry_node_ids: tuple[str, ...] = field(default_factory=tuple)
    section_path_node_ids: tuple[str, ...] = field(default_factory=tuple)
    section_path_titles: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class TextSearchHit:
    """Structured keyword-search result over runtime-visible document nodes."""

    node_id: str
    node_kind: str
    page_number: int
    text_preview: str
    match_count: int = 1
    section_path_node_ids: tuple[str, ...] = field(default_factory=tuple)
    section_path_titles: tuple[str, ...] = field(default_factory=tuple)
    scope: str = "document"
    score: float | None = None


@dataclass(slots=True, frozen=True)
class InternalLinkHit:
    """Structured outgoing internal-link result for runtime navigation."""

    relation_id: str
    source_node_id: str
    target_node_id: str
    target_kind: str
    target_page_number: int
    target_text_preview: str
    score: float | None = None


@runtime_checkable
class DocumentHandle(Protocol):
    """Core-facing document handle protocol."""

    @property
    def document_id(self) -> str:
        """Stable document identifier."""

    @property
    def root_id(self) -> str | None:
        """Stable root node identifier when available."""

    @property
    def reading_order(self) -> Sequence[str]:
        """Stable runtime traversal order of node IDs."""

    def get_page(self, page_number: int) -> PageHandle:
        """Return a page handle for the given page number."""

    def get_node(self, node_id: str) -> NodeHandle:
        """Resolve a node handle by stable node ID."""

    def get_context(self, node_id: str, *, before: int = 1, after: int = 1) -> NodeContextSlice:
        """Return nearby reading-order node IDs for a focus node."""

    def get_parent_id(self, node_id: str) -> str | None:
        """Return the parent node ID when known."""

    def get_child_ids(self, node_id: str) -> Sequence[str]:
        """Return child node IDs in stable structural order when known."""

    def get_sibling_ids(self, node_id: str) -> Sequence[str]:
        """Return sibling node IDs near the focus node when known."""

    def get_ancestry(self, node_id: str, *, include_self: bool = False) -> Sequence[str]:
        """Return ancestor IDs from root toward the focus node."""

    def get_subtree_node_ids(self, node_id: str, *, include_self: bool = True) -> Sequence[str]:
        """Return node IDs contained in the focus node subtree."""


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

    @property
    def parent_node_id(self) -> str | None:
        """Parent node ID when available."""

    def text_content(self) -> str | None:
        """Return node text when available."""

    def relations(self) -> Sequence[NodeRelationRef]:
        """Return related node references when available."""
