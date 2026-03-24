from pathlib import Path

from docwright.workspace.sandbox import (
    LocalProcessSandboxBackend,
    SandboxCommand,
    SandboxInputFile,
    SandboxPolicy,
    SandboxRunRequest,
)


def test_local_process_sandbox_runs_command_and_collects_artifacts(tmp_path: Path) -> None:
    backend = LocalProcessSandboxBackend(base_dir=tmp_path)
    result = backend.run(
        SandboxRunRequest(
            command=SandboxCommand(
                argv=(
                    "python",
                    "-c",
                    "from pathlib import Path; Path('out.txt').write_text(Path('input.txt').read_text().upper()); print('done')",
                )
            ),
            files=(SandboxInputFile(path="input.txt", content="hello sandbox"),),
            artifact_paths=("out.txt",),
            policy=SandboxPolicy(timeout_seconds=5),
        )
    )

    assert result.backend_name == "local_process"
    assert result.returncode == 0
    assert result.stdout.strip() == "done"
    assert result.artifacts[0].path == "out.txt"
    assert Path(result.artifacts[0].absolute_path).read_text() == "HELLO SANDBOX"


def test_local_process_sandbox_reports_missing_command(tmp_path: Path) -> None:
    backend = LocalProcessSandboxBackend(base_dir=tmp_path)
    result = backend.run(
        SandboxRunRequest(
            command=SandboxCommand(argv=("definitely-missing-docwright-command",)),
            policy=SandboxPolicy(timeout_seconds=1),
        )
    )

    assert result.command_not_found is True
    assert result.returncode is None
