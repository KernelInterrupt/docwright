from docwright.capabilities.manual_task import MANUAL_TASK_NAME, ManualTaskCapability


def test_manual_task_capability_uses_relaxed_guardrails() -> None:
    capability = ManualTaskCapability()
    policy = capability.guardrail_policy()

    assert capability.descriptor.name == MANUAL_TASK_NAME
    assert capability.descriptor.description == "Manual node-targeted document task mode with relaxed runtime guardrails."
    assert policy.require_highlight_before_advance is False
    assert policy.max_workspaces_per_step == 1
