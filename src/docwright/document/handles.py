"""In-memory document handles for tests and lightweight integrations."""

from __future__ import annotations

from dataclasses import dataclass, field

from docwright.document.interfaces import (
    NodeContextSlice,
    NodeRelationRef,
    TextSearchHit,
)

_STRUCTURAL_KINDS = {"document", "section", "heading", "chapter", "subsection", "subsubsection"}


@dataclass(slots=True, frozen=True)
class InMemoryNode:
    """Minimal node handle backed by in-memory data."""

    node_id: str
    kind: str
    page_number: int = 1
    text: str | None = None
    parent_node_id: str | None = None
    relation_refs: tuple[NodeRelationRef, ...] = field(default_factory=tuple)

    def text_content(self) -> str | None:
        return self.text

    def relations(self) -> tuple[NodeRelationRef, ...]:
        return self.relation_refs


@dataclass(slots=True)
class InMemoryPage:
    """Minimal page handle backed by an in-memory document."""

    page_number: int
    _nodes: dict[str, InMemoryNode]
    node_ids: tuple[str, ...]

    def get_node(self, node_id: str) -> InMemoryNode:
        if node_id not in self.node_ids:
            raise KeyError(f"node '{node_id}' is not on page {self.page_number}")
        return self._nodes[node_id]


@dataclass(slots=True)
class InMemoryDocument:
    """Minimal document handle suitable for Core tests."""

    document_id: str
    nodes: dict[str, InMemoryNode]
    reading_order: tuple[str, ...]
    root_id: str | None
    _page_index: dict[int, tuple[str, ...]]
    _parent_index: dict[str, str | None]
    _child_index: dict[str | None, tuple[str, ...]]

    @classmethod
    def from_nodes(
        cls,
        *,
        document_id: str,
        nodes: list[InMemoryNode],
        reading_order: tuple[str, ...] | None = None,
        root_id: str | None = None,
    ) -> InMemoryDocument:
        node_map = {node.node_id: node for node in nodes}
        resolved_reading_order = reading_order or tuple(node.node_id for node in nodes)
        page_index: dict[int, list[str]] = {}
        for node_id in resolved_reading_order:
            node = node_map[node_id]
            page_index.setdefault(node.page_number, []).append(node.node_id)
        for node in nodes:
            page_index.setdefault(node.page_number, [])
            if node.node_id not in page_index[node.page_number]:
                page_index[node.page_number].append(node.node_id)

        parent_index = {node.node_id: node.parent_node_id for node in nodes}
        child_index_lists: dict[str | None, list[str]] = {None: []}
        for node in nodes:
            child_index_lists.setdefault(node.parent_node_id, []).append(node.node_id)

        ordering = {node_id: index for index, node_id in enumerate(resolved_reading_order)}
        for parent_id, child_ids in child_index_lists.items():
            child_ids.sort(key=lambda node_id: ordering.get(node_id, len(ordering)))

        inferred_root = root_id if root_id is not None else _infer_root_id(nodes)
        return cls(
            document_id=document_id,
            nodes=node_map,
            reading_order=resolved_reading_order,
            root_id=inferred_root,
            _page_index={page: tuple(node_ids) for page, node_ids in page_index.items()},
            _parent_index=parent_index,
            _child_index={parent: tuple(node_ids) for parent, node_ids in child_index_lists.items()},
        )

    def get_page(self, page_number: int) -> InMemoryPage:
        node_ids = self._page_index[page_number]
        return InMemoryPage(page_number=page_number, _nodes=self.nodes, node_ids=node_ids)

    def get_node(self, node_id: str) -> InMemoryNode:
        return self.nodes[node_id]

    def get_context(self, node_id: str, *, before: int = 1, after: int = 1) -> NodeContextSlice:
        index = self.reading_order.index(node_id)
        before_node_ids = self.reading_order[max(0, index - before) : index]
        after_node_ids = self.reading_order[index + 1 : index + 1 + after]
        return NodeContextSlice(
            focus_node_id=node_id,
            before_node_ids=tuple(before_node_ids),
            after_node_ids=tuple(after_node_ids),
        )

    def get_parent_id(self, node_id: str) -> str | None:
        return self._parent_index.get(node_id)

    def get_child_ids(self, node_id: str) -> tuple[str, ...]:
        return self._child_index.get(node_id, ())

    def get_sibling_ids(self, node_id: str) -> tuple[str, ...]:
        parent_id = self.get_parent_id(node_id)
        return tuple(sibling_id for sibling_id in self._child_index.get(parent_id, ()) if sibling_id != node_id)

    def get_ancestry(self, node_id: str, *, include_self: bool = False) -> tuple[str, ...]:
        ancestry: list[str] = []
        current = node_id if include_self else self.get_parent_id(node_id)
        while current is not None:
            ancestry.append(current)
            current = self.get_parent_id(current)
        ancestry.reverse()
        return tuple(ancestry)

    def get_subtree_node_ids(self, node_id: str, *, include_self: bool = True) -> tuple[str, ...]:
        ordered: list[str] = []

        def visit(current_id: str) -> None:
            if current_id in self.nodes:
                ordered.append(current_id)
            for child_id in self.get_child_ids(current_id):
                visit(child_id)

        if include_self:
            visit(node_id)
        else:
            for child_id in self.get_child_ids(node_id):
                visit(child_id)

        ordering = {candidate: index for index, candidate in enumerate(self.reading_order)}
        ordered.sort(key=lambda candidate: ordering.get(candidate, len(ordering)))
        return tuple(dict.fromkeys(ordered))

    def search_text(
        self,
        query: str,
        *,
        limit: int = 10,
        scope: str = "document",
        node_ids: tuple[str, ...] | None = None,
        node_kinds: tuple[str, ...] | None = None,
    ) -> tuple[TextSearchHit, ...]:
        """Helper search implementation over this in-memory IR-backed document.

        Runtime owns the public search contract; this method merely provides a
        concrete implementation that ``RuntimeSession.search_text(...)`` may use.
        """

        needle = query.strip().casefold()
        if not needle or limit < 1:
            return ()

        allowed = set(node_ids) if node_ids is not None else None
        allowed_kinds = set(node_kinds) if node_kinds else None

        ordered_candidates = list(self.reading_order)
        for node_id in self.nodes:
            if node_id not in ordered_candidates:
                ordered_candidates.append(node_id)

        hits: list[TextSearchHit] = []
        for node_id in ordered_candidates:
            if allowed is not None and node_id not in allowed:
                continue
            node = self.nodes[node_id]
            if allowed_kinds is not None and node.kind not in allowed_kinds:
                continue
            haystack = (node.text or "").casefold()
            if not haystack or needle not in haystack:
                continue
            section_path_ids, section_path_titles = self._section_path(node.node_id)
            hits.append(
                TextSearchHit(
                    node_id=node.node_id,
                    node_kind=node.kind,
                    page_number=node.page_number,
                    text_preview=(node.text or "")[:240],
                    match_count=haystack.count(needle),
                    section_path_node_ids=section_path_ids,
                    section_path_titles=section_path_titles,
                    scope=scope,
                )
            )
            if len(hits) >= limit:
                break
        return tuple(hits)

    def _section_path(self, node_id: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
        ids: list[str] = []
        titles: list[str] = []
        path_ids = self.get_ancestry(node_id, include_self=True)
        for candidate in path_ids:
            if candidate == self.root_id or self.nodes.get(candidate, None) is None:
                continue
            node = self.nodes[candidate]
            if node.kind not in _STRUCTURAL_KINDS:
                continue
            ids.append(node.node_id)
            if node.text:
                titles.append(node.text[:160])
        return tuple(ids), tuple(titles)


def _infer_root_id(nodes: list[InMemoryNode]) -> str | None:
    explicit_roots = [node.node_id for node in nodes if node.parent_node_id is None and node.kind == "document"]
    if explicit_roots:
        return explicit_roots[0]
    return None
