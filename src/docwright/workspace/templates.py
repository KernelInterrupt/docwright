"""Declarative workspace template contracts."""

from __future__ import annotations

from dataclasses import dataclass

from docwright.workspace.models import EditableRegion


@dataclass(slots=True, frozen=True)
class EditableRegionSpec:
    """Declarative description of an editable workspace region."""

    name: str
    mode: str = "full_body"
    start_marker: str | None = None
    end_marker: str | None = None
    required: bool = True

    def __post_init__(self) -> None:
        if self.mode == "marker_range" and (self.start_marker is None or self.end_marker is None):
            raise ValueError("marker_range editable regions require both start_marker and end_marker")

    def as_runtime_region(self) -> EditableRegion:
        """Convert the declarative spec into the runtime editable-region view."""

        return EditableRegion(
            name=self.name,
            start_marker=self.start_marker,
            end_marker=self.end_marker,
        )


@dataclass(slots=True, frozen=True)
class WorkspaceTemplate:
    """Structured template shell behind a workspace session."""

    template_id: str
    task: str
    body_kind: str
    source: str
    editable_regions: tuple[EditableRegionSpec, ...]
    default_region: str = "body"
    compiler_profile: str | None = None

    def __post_init__(self) -> None:
        if not self.editable_regions:
            raise ValueError("workspace templates must define at least one editable region")
        names = [region.name for region in self.editable_regions]
        if len(names) != len(set(names)):
            raise ValueError("workspace template editable region names must be unique")
        if self.default_region not in set(names):
            raise ValueError("workspace template default_region must reference an existing editable region")

    def region(self, name: str) -> EditableRegionSpec:
        """Return the named editable region or raise ``KeyError``."""

        for region in self.editable_regions:
            if region.name == name:
                return region
        raise KeyError(name)

    def default_region_spec(self) -> EditableRegionSpec:
        """Return the template's default editable region."""

        return self.region(self.default_region)
