from pathlib import Path

import pytest

from docwright.document.ir_loader import in_memory_document_from_ir, load_in_memory_document_from_ir_path

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "document_ir" / "attention_is_all_you_need.document_ir.json"


def test_ir_loader_reads_prepared_document_ir_fixture() -> None:
    document = load_in_memory_document_from_ir_path(FIXTURE)

    assert document.document_id == "attention_is_all_you_need.pdf"
    assert len(document.reading_order) == 20
    first = document.get_node(document.reading_order[0])
    assert first.node_id == "para_0001"
    assert first.kind == "paragraph"
    assert first.page_number == 1
    assert first.text_content() is not None


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
