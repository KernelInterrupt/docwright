from docwright.document.handles import InMemoryDocument, InMemoryNode
from docwright.document.interfaces import NodeContextSlice, NodeRelationRef


def test_in_memory_document_groups_nodes_by_page_and_reading_order() -> None:
    relation = NodeRelationRef(relation_id="rel-1", kind="supports", target_id="node-2")
    document = InMemoryDocument.from_nodes(
        document_id="doc-1",
        root_id="root",
        nodes=[
            InMemoryNode(node_id="node-1", kind="paragraph", page_number=1, text="alpha", parent_node_id="root", relation_refs=(relation,)),
            InMemoryNode(node_id="node-2", kind="figure", page_number=2, text="beta", parent_node_id="root"),
        ],
    )

    assert document.document_id == "doc-1"
    assert document.root_id == "root"
    assert document.reading_order == ("node-1", "node-2")
    assert document.get_node("node-1").text_content() == "alpha"
    assert document.get_node("node-1").relations() == (relation,)
    assert document.get_page(2).node_ids == ("node-2",)
    assert document.get_context("node-2") == NodeContextSlice(
        focus_node_id="node-2",
        before_node_ids=("node-1",),
        after_node_ids=(),
    )


def test_in_memory_page_restricts_lookup_to_its_nodes() -> None:
    document = InMemoryDocument.from_nodes(
        document_id="doc-1",
        nodes=[
            InMemoryNode(node_id="node-1", kind="paragraph", page_number=1),
            InMemoryNode(node_id="node-2", kind="paragraph", page_number=2),
        ],
    )
    page = document.get_page(1)

    assert page.get_node("node-1").node_id == "node-1"


def test_in_memory_document_supports_keyword_search_and_structure_queries() -> None:
    document = InMemoryDocument.from_nodes(
        document_id="doc-1",
        root_id="root",
        nodes=[
            InMemoryNode(node_id="sec-1", kind="section", page_number=1, text="Guide", parent_node_id="root"),
            InMemoryNode(node_id="node-1", kind="paragraph", page_number=1, text="alpha beta alpha", parent_node_id="sec-1"),
            InMemoryNode(node_id="node-2", kind="paragraph", page_number=2, text="gamma", parent_node_id="sec-1"),
        ],
    )

    hits = document.search_text("alpha")

    assert len(hits) == 1
    assert hits[0].node_id == "node-1"
    assert hits[0].node_kind == "paragraph"
    assert hits[0].page_number == 1
    assert hits[0].match_count == 2
    assert hits[0].section_path_node_ids == ("sec-1",)
    assert hits[0].section_path_titles == ("Guide",)
    assert document.get_parent_id("node-1") == "sec-1"
    assert document.get_child_ids("sec-1") == ("node-1", "node-2")
    assert document.get_sibling_ids("node-1") == ("node-2",)
    assert document.get_ancestry("node-1") == ("root", "sec-1")
    assert document.get_subtree_node_ids("sec-1") == ("sec-1", "node-1", "node-2")
