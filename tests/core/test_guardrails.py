import pytest

from docwright.core.guardrails import (
    GuardrailCode,
    GuardrailViolationError,
    RuntimeGuardrailPolicy,
    RuntimePermissions,
)


def test_runtime_permissions_allow_actions_by_default() -> None:
    permissions = RuntimePermissions()

    for action in ("highlight", "warning", "open_workspace", "advance"):
        permissions.ensure_allowed(action)


def test_runtime_permissions_raise_structured_violation_for_blocked_action() -> None:
    permissions = RuntimePermissions(allow_advance=False)

    with pytest.raises(GuardrailViolationError) as exc_info:
        permissions.ensure_allowed("advance")

    assert exc_info.value.violation.code is GuardrailCode.ACTION_NOT_PERMITTED
    assert exc_info.value.violation.details == {"action": "advance"}


def test_runtime_guardrail_policy_defaults_remain_capability_neutral() -> None:
    policy = RuntimeGuardrailPolicy()

    assert policy.require_highlight_before_advance is False
    assert policy.max_workspaces_per_step is None
    assert policy.legacy_sequential_guardrails() == {}
    assert policy.selected_node_action_guardrails() == {}


def test_runtime_guardrail_policy_separates_legacy_and_selected_node_rules() -> None:
    policy = RuntimeGuardrailPolicy(
        require_highlight_before_advance=True,
        max_workspaces_per_step=2,
    )

    assert policy.legacy_sequential_guardrails() == {"highlight_before_advance": True}
    assert policy.selected_node_action_guardrails() == {"max_workspaces_per_selected_node": 2}
