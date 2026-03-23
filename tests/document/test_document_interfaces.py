from dataclasses import dataclass, field

from docwright.document.interfaces import (
    DocumentHandle,
    NodeContextSlice,
    NodeHandle,
    NodeRelationRef,
    PageHandle,
)


@dataclass(slots=True)
class DummyNode:
    node_id: str
    kind: str = "paragraph"
    page_number: int = 1
    relation_refs: tuple[NodeRelationRef, ...] = field(default_factory=tuple)

    def text_content(self) -> str | None:
        return f"text for {self.node_id}"

    def relations(self) -> tuple[NodeRelationRef, ...]:
        return self.relation_refs


@dataclass(slots=True)
class DummyPage:
    page_number: int
    node_ids: tuple[str, ...]

    def get_node(self, node_id: str) -> DummyNode:
        return DummyNode(node_id=node_id)


class DummyDocument:
    document_id = "doc-1"
    reading_order = ("node-1", "node-2")

    def get_page(self, page_number: int) -> DummyPage:
        return DummyPage(page_number=page_number, node_ids=("node-1",))

    def get_node(self, node_id: str) -> DummyNode:
        return DummyNode(node_id=node_id)

    def get_context(self, node_id: str, *, before: int = 1, after: int = 1) -> NodeContextSlice:
        assert node_id == "node-2"
        return NodeContextSlice(focus_node_id=node_id, before_node_ids=("node-1",), after_node_ids=())


def test_node_relation_ref_is_parser_neutral() -> None:
    relation = NodeRelationRef(
        relation_id="rel-1",
        kind="supports",
        target_id="node-2",
        score=0.9,
    )

    assert relation.relation_id == "rel-1"
    assert relation.kind == "supports"
    assert relation.target_id == "node-2"
    assert relation.score == 0.9


def test_node_context_slice_tracks_neighboring_ids() -> None:
    context = NodeContextSlice(
        focus_node_id="node-2",
        before_node_ids=("node-1",),
        after_node_ids=("node-3", "node-4"),
    )

    assert context.focus_node_id == "node-2"
    assert context.before_node_ids == ("node-1",)
    assert context.after_node_ids == ("node-3", "node-4")


def test_document_handle_protocol_captures_core_lookup_surface() -> None:
    document = DummyDocument()

    assert isinstance(document, DocumentHandle)
    assert document.document_id == "doc-1"
    assert tuple(document.reading_order) == ("node-1", "node-2")
    assert document.get_page(1) == DummyPage(page_number=1, node_ids=("node-1",))
    assert document.get_node("node-1") == DummyNode(node_id="node-1")
    assert document.get_context("node-2") == NodeContextSlice(
        focus_node_id="node-2",
        before_node_ids=("node-1",),
        after_node_ids=(),
    )


def test_page_handle_protocol_captures_page_scoped_lookup_surface() -> None:
    page = DummyPage(page_number=1, node_ids=("node-1",))

    assert isinstance(page, PageHandle)
    assert page.page_number == 1
    assert tuple(page.node_ids) == ("node-1",)
    assert page.get_node("node-1") == DummyNode(node_id="node-1")


def test_node_handle_protocol_captures_query_surface() -> None:
    relation = NodeRelationRef(relation_id="rel-1", kind="supports", target_id="node-2")
    node = DummyNode(node_id="node-1", relation_refs=(relation,))

    assert isinstance(node, NodeHandle)
    assert node.node_id == "node-1"
    assert node.kind == "paragraph"
    assert node.page_number == 1
    assert node.text_content() == "text for node-1"
    assert node.relations() == (relation,)
