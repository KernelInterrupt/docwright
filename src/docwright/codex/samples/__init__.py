"""Optional packaged samples for DocWright Codex integrations."""

from docwright.codex.samples.attention_fixture import FIXTURE_PATH, build_attention_fixture_entry
from docwright.codex.samples.attention_smoke import run_attention_fixture_smoke

__all__ = ["FIXTURE_PATH", "build_attention_fixture_entry", "run_attention_fixture_smoke"]
