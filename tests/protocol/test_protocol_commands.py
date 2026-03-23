from docwright.protocol.commands import (
    AdvanceCommand,
    CommandName,
    HighlightCommand,
    OpenWorkspaceCommand,
    WarningCommand,
)


def test_command_schemas_capture_transport_neutral_actions() -> None:
    highlight = HighlightCommand(command_id="cmd-1", level="important", reason="key claim")
    warning = WarningCommand(
        command_id="cmd-2",
        kind="citation",
        severity="medium",
        message="Missing citation",
        evidence=("node-1",),
    )
    workspace = OpenWorkspaceCommand(command_id="cmd-3", task="annotation", capability="guided_reading")
    advance = AdvanceCommand(command_id="cmd-4")

    assert highlight.command_name is CommandName.HIGHLIGHT
    assert warning.command_name is CommandName.WARNING
    assert workspace.command_name is CommandName.OPEN_WORKSPACE
    assert advance.command_name is CommandName.ADVANCE
