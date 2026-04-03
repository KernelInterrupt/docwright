"""Minimal headless runner scaffold."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from docwright.adapters.agent.base import AgentAdapter
from docwright.capabilities.base import CapabilityProfile
from docwright.core.models import RuntimeSessionStatus
from docwright.core.session import RuntimeSession
from docwright.protocol.events import ProtocolEvent


@dataclass(slots=True)
class HeadlessRunner:
    """Minimal headless transport for adapter-driven sessions.

    The headless runner executes Core sessions through an adapter, but it
    exposes only protocol-safe events back to transport callers rather than
    leaking Core-owned runtime event envelopes.
    """

    adapter: AgentAdapter
    capability: CapabilityProfile | None = None

    def protocol_events(self, session: RuntimeSession) -> tuple[ProtocolEvent, ...]:
        """Return the session event stream as transport-safe protocol events."""

        return tuple(event.as_protocol_event() for event in session.events())

    def run_once(self, session: RuntimeSession) -> tuple[ProtocolEvent, ...]:
        asyncio.run(self.adapter.run_step(session, self.capability))
        return self.protocol_events(session)

    def run_until_complete(self, session: RuntimeSession, *, max_steps: int = 100) -> tuple[ProtocolEvent, ...]:
        steps = 0
        while session.model.status is RuntimeSessionStatus.ACTIVE:
            self.run_once(session)
            steps += 1
            if steps >= max_steps:
                raise RuntimeError("headless runner exceeded max_steps before completion")
        return self.protocol_events(session)
