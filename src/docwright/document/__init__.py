"""Unified document-facing surface for DocWright.

This package keeps lightweight in-repo document interfaces/loaders available by
default while exposing optional heavy document-conversion entrypoints through a
lazy facade. Concrete ingest and IR-conversion ownership stays with the
optional ``docwright-document`` backend rather than Core.
"""

from docwright.document.facade import (
    MissingDocumentBackendError,
    document_backend_available,
    document_backend_status,
    ir_converter,
)
from docwright.document.handles import InMemoryDocument, InMemoryNode
from docwright.document.interfaces import (
    DocumentHandle,
    InternalLinkHit,
    NodeContextSlice,
    NodeHandle,
    NodeRelationRef,
    NodeStructureSlice,
    PageHandle,
    TextSearchHit,
)
from docwright.document.ir_loader import in_memory_document_from_ir, load_in_memory_document_from_ir_path

__all__ = [
    "DocumentHandle",
    "InMemoryDocument",
    "InMemoryNode",
    "InternalLinkHit",
    "MissingDocumentBackendError",
    "NodeContextSlice",
    "NodeHandle",
    "NodeRelationRef",
    "NodeStructureSlice",
    "PageHandle",
    "TextSearchHit",
    "document_backend_available",
    "document_backend_status",
    "in_memory_document_from_ir",
    "ir_converter",
    "load_in_memory_document_from_ir_path",
]
