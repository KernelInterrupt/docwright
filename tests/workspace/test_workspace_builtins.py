from docwright.workspace import (
    build_bubblewrap_latex_workspace_compiler,
    build_default_workspace_registry,
    build_local_latex_workspace_compiler,
)


def test_default_workspace_registry_exposes_annotation_profile_and_template() -> None:
    registry = build_default_workspace_registry()

    profile = registry.profile("latex_annotation")
    template = registry.template("default_annotation_tex")

    assert profile.sandbox_profile == "local_process"
    assert template.compiler_profile == "tectonic"
    assert template.default_region_spec().start_marker == "% DOCWRIGHT:BODY_START"


def test_local_latex_workspace_compiler_describe_exposes_local_process_backend(tmp_path) -> None:
    compiler = build_local_latex_workspace_compiler(base_dir=str(tmp_path))

    described = compiler.describe()

    assert described.sandbox_backend == "local_process"
    assert described.profile == "tectonic"


def test_bubblewrap_latex_workspace_compiler_describe_exposes_bubblewrap_backend(tmp_path) -> None:
    compiler = build_bubblewrap_latex_workspace_compiler(base_dir=str(tmp_path))

    described = compiler.describe()

    assert described.sandbox_backend == "bubblewrap"
