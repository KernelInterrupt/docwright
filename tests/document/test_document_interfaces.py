from dataclasses import dataclass, field

from docwright.document.interfaces import (
    DocumentHandle,
    InternalLinkHit,
    NodeContextSlice,
    NodeHandle,
    NodeRelationRef,
    NodeStructureSlice,
    PageHandle,
)


@dataclass(slots=True)
class DummyNode:
    node_id: str
    kind: str = "paragraph"
    page_number: int = 1
    parent_node_id: str | None = None
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
    root_id = "root"
    reading_order = ("node-1", "node-2")

    def get_page(self, page_number: int) -> DummyPage:
        return DummyPage(page_number=page_number, node_ids=("node-1",))

    def get_node(self, node_id: str) -> DummyNode:
        parent = {"node-1": "section-1", "node-2": "section-1", "section-1": "root"}.get(node_id)
        return DummyNode(node_id=node_id, parent_node_id=parent)

    def get_context(self, node_id: str, *, before: int = 1, after: int = 1) -> NodeContextSlice:
        assert node_id == "node-2"
        return NodeContextSlice(focus_node_id=node_id, before_node_ids=("node-1",), after_node_ids=())

    def get_parent_id(self, node_id: str) -> str | None:
        return {"node-1": "section-1", "node-2": "section-1", "section-1": "root"}.get(node_id)

    def get_child_ids(self, node_id: str) -> tuple[str, ...]:
        return {"root": ("section-1",), "section-1": ("node-1", "node-2")}.get(node_id, ())

    def get_sibling_ids(self, node_id: str) -> tuple[str, ...]:
        return {"node-1": ("node-2",), "node-2": ("node-1",), "section-1": ()}.get(node_id, ())

    def get_ancestry(self, node_id: str, *, include_self: bool = False) -> tuple[str, ...]:
        ancestry = {"node-1": ("root", "section-1"), "node-2": ("root", "section-1"), "section-1": ("root",)}.get(node_id, ())
        return ancestry + ((node_id,) if include_self else ())

    def get_subtree_node_ids(self, node_id: str, *, include_self: bool = True) -> tuple[str, ...]:
        subtree = {"section-1": ("section-1", "node-1", "node-2"), "node-1": ("node-1",), "node-2": ("node-2",)}.get(node_id, ())
        if include_self:
            return subtree
        return tuple(candidate for candidate in subtree if candidate != node_id)


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


def test_document_navigation_dataclasses_capture_structure_and_links() -> None:
    structure = NodeStructureSlice(
        focus_node_id="node-2",
        root_id="root",
        parent_node_id="section-1",
        child_node_ids=(),
        sibling_node_ids=("node-1",),
        ancestry_node_ids=("root", "section-1"),
        section_path_node_ids=("section-1",),
        section_path_titles=("Guide",),
    )
    link = InternalLinkHit(
        relation_id="rel-link-1",
        source_node_id="node-1",
        target_node_id="section-2",
        target_kind="section",
        target_page_number=2,
        target_text_preview="Device B",
        score=0.8,
    )

    assert structure.parent_node_id == "section-1"
    assert structure.section_path_titles == ("Guide",)
    assert link.target_node_id == "section-2"
    assert link.score == 0.8


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
    assert document.root_id == "root"
    assert tuple(document.reading_order) == ("node-1", "node-2")
    assert document.get_page(1) == DummyPage(page_number=1, node_ids=("node-1",))
    assert document.get_node("node-1") == DummyNode(node_id="node-1", parent_node_id="section-1")
    assert document.get_context("node-2") == NodeContextSlice(
        focus_node_id="node-2",
        before_node_ids=("node-1",),
        after_node_ids=(),
    )
    assert document.get_parent_id("node-1") == "section-1"
    assert document.get_child_ids("section-1") == ("node-1", "node-2")
    assert document.get_sibling_ids("node-1") == ("node-2",)
    assert document.get_ancestry("node-2") == ("root", "section-1")
    assert document.get_subtree_node_ids("section-1") == ("section-1", "node-1", "node-2")


def test_page_handle_protocol_captures_page_scoped_lookup_surface() -> None:
    page = DummyPage(page_number=1, node_ids=("node-1",))

    assert isinstance(page, PageHandle)
    assert page.page_number == 1
    assert tuple(page.node_ids) == ("node-1",)
    assert page.get_node("node-1") == DummyNode(node_id="node-1")


def test_node_handle_protocol_captures_query_surface() -> None:
    relation = NodeRelationRef(relation_id="rel-1", kind="supports", target_id="node-2")
    node = DummyNode(node_id="node-1", parent_node_id="section-1", relation_refs=(relation,))

    assert isinstance(node, NodeHandle)
    assert node.node_id == "node-1"
    assert node.kind == "paragraph"
    assert node.page_number == 1
    assert node.parent_node_id == "section-1"
    assert node.text_content() == "text for node-1"
    assert node.relations() == (relation,)
