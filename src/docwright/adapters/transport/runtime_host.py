"""Backward-compatible alias for the Codex-scoped host bridge.

The current direct-library host bridge is still Codex-specific. ``RuntimeHostBridge``
remains as a compatibility import surface for older code, but the canonical
implementation now lives in ``docwright.adapters.transport.codex_host``.
"""

from docwright.adapters.transport.codex_host import CodexHostBridge

RuntimeHostBridge = CodexHostBridge

__all__ = ["RuntimeHostBridge"]
