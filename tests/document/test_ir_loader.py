from pathlib import Path

import pytest

from docwright.document.ir_loader import in_memory_document_from_ir, load_in_memory_document_from_ir_path

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "document_ir" / "attention_is_all_you_need.document_ir.json"
LINK_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "document_ir" / "navigation_with_links.document_ir.json"


def test_ir_loader_reads_prepared_document_ir_fixture() -> None:
    document = load_in_memory_document_from_ir_path(FIXTURE)

    assert document.document_id == "attention_is_all_you_need.pdf"
    assert document.root_id == "doc_root"
    assert len(document.reading_order) == 20
    first = document.get_node(document.reading_order[0])
    assert first.node_id == "para_0001"
    assert first.kind == "paragraph"
    assert first.page_number == 1
    assert first.parent_node_id == "doc_root"
    assert first.text_content() is not None


def test_ir_loader_preserves_hierarchy_and_internal_link_relations() -> None:
    document = load_in_memory_document_from_ir_path(LINK_FIXTURE)

    assert document.root_id == "doc_root"
    assert document.get_parent_id("para_intro") == "sec_intro"
    assert document.get_child_ids("sec_intro") == ("para_intro",)
    relations = document.get_node("para_intro").relations()
    assert len(relations) == 1
    assert relations[0].kind == "internal_link_to"
    assert relations[0].target_id == "sec_device_b"


def test_ir_loader_rejects_missing_reading_order_nodes() -> None:
    with pytest.raises(ValueError):
        in_memory_document_from_ir(
            {
                "document_id": "doc-1",
                "root_id": "root",
                "nodes": {
                    "root": {"id": "root", "kind": "document"},
                    "node-1": {"id": "node-1", "kind": "paragraph", "text": "alpha"},
                },
                "reading_order": ["missing-node"],
            }
        )
