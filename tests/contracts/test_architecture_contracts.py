from dataclasses import is_dataclass

from docwright.adapters.agent.base import AdapterDescriptor, AgentAdapter
from docwright.capabilities.base import CapabilityDescriptor, CapabilityProfile
from docwright.core.models import RuntimeSessionModel, RuntimeStepState
from docwright.document.interfaces import (
    DocumentHandle,
    NodeContextSlice,
    NodeHandle,
    NodeRelationRef,
    PageHandle,
)
from docwright.protocol.events import EventName, ProtocolEvent
from docwright.skills.base import SkillBundle, SkillDescriptor
from docwright.workspace.models import EditableRegion, WorkspaceHistoryEntry, WorkspaceSessionModel


def test_contract_modules_export_dataclass_models() -> None:
    for model in (
        RuntimeSessionModel,
        RuntimeStepState,
        WorkspaceSessionModel,
        WorkspaceHistoryEntry,
        EditableRegion,
        ProtocolEvent,
        EventName,
        NodeRelationRef,
        NodeContextSlice,
        AdapterDescriptor,
        CapabilityDescriptor,
        SkillDescriptor,
    ):
        assert is_dataclass(model)


def test_interface_boundaries_remain_protocols() -> None:
    for protocol in (
        DocumentHandle,
        PageHandle,
        NodeHandle,
        AgentAdapter,
        CapabilityProfile,
        SkillBundle,
    ):
        assert getattr(protocol, "_is_protocol", False) is True
