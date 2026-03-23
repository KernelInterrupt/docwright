"""Minimal headless runner scaffold."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from docwright.adapters.agent.base import AgentAdapter
from docwright.capabilities.base import CapabilityProfile
from docwright.core.models import RuntimeSessionStatus
from docwright.core.session import RuntimeSession


@dataclass(slots=True)
class HeadlessRunner:
    """Minimal transport-neutral runner for adapter-driven sessions."""

    adapter: AgentAdapter
    capability: CapabilityProfile | None = None

    def run_once(self, session: RuntimeSession) -> tuple[object, ...]:
        asyncio.run(self.adapter.run_step(session, self.capability))
        return session.events()

    def run_until_complete(self, session: RuntimeSession, *, max_steps: int = 100) -> tuple[object, ...]:
        steps = 0
        while session.model.status is RuntimeSessionStatus.ACTIVE:
            self.run_once(session)
            steps += 1
            if steps >= max_steps:
                raise RuntimeError("headless runner exceeded max_steps before completion")
        return session.events()
