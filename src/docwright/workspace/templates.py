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
        if self.mode not in {"full_body", "marker_range"}:
            raise ValueError(f"unsupported editable region mode: {self.mode}")

    def as_runtime_region(self) -> EditableRegion:
        """Convert the declarative spec into the runtime editable-region view."""

        return EditableRegion(
            name=self.name,
            mode=self.mode,
            start_marker=self.start_marker,
            end_marker=self.end_marker,
        )

    def extract(self, source: str) -> str:
        """Extract the editable body from a concrete template source."""

        if self.mode == "full_body":
            return source
        start_index, end_index = self._marker_bounds(source)
        return source[start_index:end_index]

    def render(self, source: str, body: str) -> str:
        """Render the editable body back into a concrete template source."""

        if self.mode == "full_body":
            return body
        start_index, end_index = self._marker_bounds(source)
        return f"{source[:start_index]}{body}{source[end_index:]}"

    def validate_source(self, source: str) -> None:
        """Validate that the concrete source satisfies the editable-region rule."""

        if self.mode == "full_body":
            return
        self._marker_bounds(source)

    def _marker_bounds(self, source: str) -> tuple[int, int]:
        if self.start_marker is None or self.end_marker is None:
            raise ValueError("marker_range editable regions require both start_marker and end_marker")
        start_marker_index = source.find(self.start_marker)
        if start_marker_index < 0:
            raise ValueError(f"editable region start marker not found: {self.start_marker}")
        end_marker_index = source.find(self.end_marker)
        if end_marker_index < 0:
            raise ValueError(f"editable region end marker not found: {self.end_marker}")
        start_index = start_marker_index + len(self.start_marker)
        if end_marker_index < start_index:
            raise ValueError("editable region end marker must appear after start marker")
        return start_index, end_marker_index


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
        for region in self.editable_regions:
            region.validate_source(self.source)

    def region(self, name: str) -> EditableRegionSpec:
        """Return the named editable region or raise ``KeyError``."""

        for region in self.editable_regions:
            if region.name == name:
                return region
        raise KeyError(name)

    def default_region_spec(self) -> EditableRegionSpec:
        """Return the template's default editable region."""

        return self.region(self.default_region)

    def default_body(self) -> str:
        """Return the current editable body embedded in the template source."""

        return self.default_region_spec().extract(self.source)

    def render_body(self, body: str, *, region_name: str | None = None) -> str:
        """Render ``body`` into the template source for the target editable region."""

        region = self.default_region_spec() if region_name is None else self.region(region_name)
        return region.render(self.source, body)
