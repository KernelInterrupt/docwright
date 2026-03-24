"""Backward-compatible Codex bridge alias.

`RuntimeHostBridge` is the canonical generic host-facing bridge. This module is
kept as a compatibility import surface for older Codex-specific integrations.
"""

from docwright.adapters.transport.runtime_host import RuntimeHostBridge

CodexLibraryBridge = RuntimeHostBridge

__all__ = ['CodexLibraryBridge']
