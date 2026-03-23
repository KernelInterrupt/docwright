from docwright.core.models import RuntimeSessionModel, RuntimeSessionStatus
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode
from docwright.document.interfaces import DocumentHandle


def test_runtime_session_consumes_document_handle_protocol_without_parser_internals() -> None:
    document = InMemoryDocument.from_nodes(
        document_id="doc-1",
        nodes=[
            InMemoryNode(node_id="node-1", kind="paragraph", text="alpha", page_number=1),
            InMemoryNode(node_id="node-2", kind="figure", text="beta", page_number=2),
        ],
    )

    assert isinstance(document, DocumentHandle)

    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id=document.document_id),
        document=document,
    )

    first_node = session.current_node()
    second_node = session.advance()
    completed = session.advance()

    assert first_node is not None
    assert first_node.node_id == "node-1"
    assert first_node.text_content() == "alpha"
    assert second_node is not None
    assert second_node.node_id == "node-2"
    assert second_node.kind == "figure"
    assert completed is None
    assert session.model.status is RuntimeSessionStatus.COMPLETED
