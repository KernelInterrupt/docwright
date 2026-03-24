import types

import pytest

from docwright import document
from docwright.document.facade import MissingDocumentBackendError


def test_document_facade_import_is_safe_without_optional_backend() -> None:
    assert hasattr(document, "ir_converter")
    status = document.document_backend_status()
    assert status["available"] is False
    assert status["provider"] is None
    assert document.document_backend_available() is False


def test_document_facade_ir_converter_raises_clear_error_when_backend_missing() -> None:
    with pytest.raises(MissingDocumentBackendError, match=r"docwright\[document\]"):
        document.ir_converter("paper.pdf")


def test_document_facade_ir_converter_uses_lazy_backend_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_backend = types.SimpleNamespace(ir_converter=lambda path, *, mode="fast": {"path": path, "mode": mode})

    def fake_import_module(name: str):
        if name == "docwright_document.api":
            return fake_backend
        raise ImportError(name)

    monkeypatch.setattr("docwright.document.facade.import_module", fake_import_module)

    assert document.document_backend_available() is True
    assert document.document_backend_status() == {
        "available": True,
        "provider": "docwright_document.api",
    }
    assert document.ir_converter("paper.pdf", mode="accurate") == {
        "path": "paper.pdf",
        "mode": "accurate",
    }
