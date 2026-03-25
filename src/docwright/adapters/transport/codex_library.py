"""Backward-compatible Codex bridge alias."""

from docwright.adapters.transport.codex_host import CodexHostBridge

CodexLibraryBridge = CodexHostBridge

__all__ = ["CodexLibraryBridge"]
