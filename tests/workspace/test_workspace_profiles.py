from docwright.workspace import EditableRegion
from docwright.workspace.profiles import WorkspaceProfile
from docwright.workspace.registry import WorkspaceProfileRegistry, WorkspaceRegistryError
from docwright.workspace.templates import EditableRegionSpec, WorkspaceTemplate


def test_editable_region_spec_can_create_runtime_region() -> None:
    region_spec = EditableRegionSpec(
        name="body",
        mode="marker_range",
        start_marker="% DOCWRIGHT:BODY_START",
        end_marker="% DOCWRIGHT:BODY_END",
    )

    assert region_spec.as_runtime_region() == EditableRegion(
        name="body",
        start_marker="% DOCWRIGHT:BODY_START",
        end_marker="% DOCWRIGHT:BODY_END",
    )


def test_workspace_template_resolves_default_region() -> None:
    template = WorkspaceTemplate(
        template_id="default_annotation_tex",
        task="annotation",
        body_kind="latex_body",
        source="\n".join(
            [
                r"\documentclass{article}",
                "% DOCWRIGHT:BODY_START",
                "% DOCWRIGHT:BODY_END",
            ]
        ),
        editable_regions=(
            EditableRegionSpec(
                name="body",
                mode="marker_range",
                start_marker="% DOCWRIGHT:BODY_START",
                end_marker="% DOCWRIGHT:BODY_END",
            ),
        ),
    )

    assert template.default_region_spec().name == "body"
    assert template.region("body").mode == "marker_range"


def test_workspace_profile_registry_resolves_profiles_and_templates() -> None:
    registry = WorkspaceProfileRegistry()
    template = registry.register_template(
        WorkspaceTemplate(
            template_id="default_annotation_tex",
            task="annotation",
            body_kind="latex_body",
            source="body shell",
            editable_regions=(EditableRegionSpec(name="body"),),
        )
    )
    profile = registry.register_profile(
        WorkspaceProfile(
            profile_name="latex_annotation",
            task="annotation",
            template_id=template.template_id,
            body_kind="latex_body",
            locked_sections=("preamble", "document_structure"),
            model_summary="Edit only the annotation body.",
        )
    )

    assert registry.profile("latex_annotation") is profile
    assert registry.template("default_annotation_tex") is template
    assert registry.resolve_template_for_profile("latex_annotation") is template
    assert registry.supported_profiles() == ("latex_annotation",)
    assert registry.supported_templates() == ("default_annotation_tex",)


def test_workspace_profile_registry_raises_structured_errors_for_unknown_entries() -> None:
    registry = WorkspaceProfileRegistry()

    try:
        registry.profile("missing")
    except WorkspaceRegistryError as exc:
        assert "unknown workspace profile" in str(exc)
    else:
        raise AssertionError("expected missing profile to raise WorkspaceRegistryError")
