import shutil

import pytest

from docwright.workspace.sandbox import (
    BubblewrapSandboxBackend,
    SandboxCommand,
    SandboxInputFile,
    SandboxPolicy,
    SandboxRunRequest,
)


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is not available")
def test_bubblewrap_sandbox_isolates_workspace_from_host_repo(tmp_path) -> None:
    backend = BubblewrapSandboxBackend(base_dir=tmp_path)

    result = backend.run(
        SandboxRunRequest(
            command=SandboxCommand(
                argv=(
                    "/bin/sh",
                    "-lc",
                    "test ! -e /home/pc/docwright && cat note.txt && printf '\nsecure' > out.txt",
                )
            ),
            files=(SandboxInputFile(path="note.txt", content="hello bubblewrap"),),
            artifact_paths=("out.txt",),
            policy=SandboxPolicy(timeout_seconds=5),
        )
    )

    assert result.backend_name == "bubblewrap"
    assert result.returncode == 0
    assert "hello bubblewrap" in result.stdout
    assert result.artifacts[0].path == "out.txt"


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is not available")
def test_bubblewrap_sandbox_reports_missing_command_inside_sandbox(tmp_path) -> None:
    backend = BubblewrapSandboxBackend(base_dir=tmp_path)

    result = backend.run(
        SandboxRunRequest(
            command=SandboxCommand(argv=("definitely-missing-docwright-command",)),
            policy=SandboxPolicy(timeout_seconds=5),
        )
    )

    assert result.backend_name == "bubblewrap"
    assert result.command_not_found is True
