from docwright.document.handles import InMemoryDocument, InMemoryNode
from docwright.document.interfaces import NodeContextSlice, NodeRelationRef


def test_in_memory_document_groups_nodes_by_page_and_reading_order() -> None:
    relation = NodeRelationRef(relation_id="rel-1", kind="supports", target_id="node-2")
    document = InMemoryDocument.from_nodes(
        document_id="doc-1",
        nodes=[
            InMemoryNode(node_id="node-1", kind="paragraph", page_number=1, text="alpha", relation_refs=(relation,)),
            InMemoryNode(node_id="node-2", kind="figure", page_number=2, text="beta"),
        ],
    )

    assert document.document_id == "doc-1"
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
