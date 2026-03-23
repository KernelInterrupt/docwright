"""Compatibility helpers for supported Python versions."""

from __future__ import annotations

from enum import Enum

try:
    from enum import StrEnum as _StrEnum
except ImportError:
    class _StrEnum(str, Enum):
        """Python <3.11 fallback for StrEnum."""

        pass

StrEnum = _StrEnum
