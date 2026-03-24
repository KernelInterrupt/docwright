"""Lazy document-backend facade for the unified ``docwright.document`` surface."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Any

DOCUMENT_BACKEND_MODULE_CANDIDATES = (
    "docwright_document.api",
    "docwright_document",
)


class MissingDocumentBackendError(RuntimeError):
    """Raised when optional document-conversion functionality is requested without a backend."""


def _load_document_backend() -> tuple[ModuleType | None, str | None]:
    for module_name in DOCUMENT_BACKEND_MODULE_CANDIDATES:
        try:
            module = import_module(module_name)
        except ImportError:
            continue
        return module, module_name
    return None, None


def document_backend_status() -> dict[str, Any]:
    """Return availability information for the optional document backend."""

    module, module_name = _load_document_backend()
    return {
        "available": module is not None,
        "provider": module_name,
    }


def document_backend_available() -> bool:
    """Whether the optional document backend is currently importable."""

    return bool(document_backend_status()["available"])


def ir_converter(*args: Any, **kwargs: Any) -> Any:
    """Convert source documents to Document IR through an optional backend.

    The unified ``docwright`` package intentionally exposes this facade even when
    the heavy document-conversion backend is not installed. Importing
    ``docwright.document`` should stay safe; only calling this function requires
    the optional backend.
    """

    module, module_name = _load_document_backend()
    if module is None:
        raise MissingDocumentBackendError(
            "Document conversion backend is not installed. Install `docwright[document]` "
            "or `docwright[full]`."
        )

    converter = getattr(module, "ir_converter", None)
    if not callable(converter):
        raise MissingDocumentBackendError(
            f"Document backend {module_name!r} does not expose a callable ir_converter()."
        )
    return converter(*args, **kwargs)
