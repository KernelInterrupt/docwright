"""Registry for declarative workspace profiles and templates."""

from __future__ import annotations

from dataclasses import dataclass, field

from docwright.workspace.profiles import WorkspaceProfile
from docwright.workspace.templates import WorkspaceTemplate


class WorkspaceRegistryError(KeyError):
    """Raised when a requested workspace profile or template is unavailable."""


@dataclass(slots=True)
class WorkspaceProfileRegistry:
    """Explicit registry for workspace profiles and templates."""

    _profiles: dict[str, WorkspaceProfile] = field(default_factory=dict)
    _templates: dict[str, WorkspaceTemplate] = field(default_factory=dict)

    def register_profile(self, profile: WorkspaceProfile) -> WorkspaceProfile:
        """Register a profile by name and return it."""

        self._profiles[profile.profile_name] = profile
        return profile

    def register_template(self, template: WorkspaceTemplate) -> WorkspaceTemplate:
        """Register a template by ID and return it."""

        self._templates[template.template_id] = template
        return template

    def profile(self, profile_name: str) -> WorkspaceProfile:
        """Resolve a registered workspace profile."""

        try:
            return self._profiles[profile_name]
        except KeyError as exc:
            raise WorkspaceRegistryError(f"unknown workspace profile: {profile_name}") from exc

    def template(self, template_id: str) -> WorkspaceTemplate:
        """Resolve a registered workspace template."""

        try:
            return self._templates[template_id]
        except KeyError as exc:
            raise WorkspaceRegistryError(f"unknown workspace template: {template_id}") from exc

    def resolve_template_for_profile(
        self,
        profile_name: str,
        *,
        template_id: str | None = None,
    ) -> WorkspaceTemplate:
        """Resolve the template for a profile, optionally overriding the template ID."""

        profile = self.profile(profile_name)
        return self.template(template_id or profile.template_id)

    def supported_profiles(self) -> tuple[str, ...]:
        """Return registered profile names in insertion order."""

        return tuple(self._profiles)

    def supported_templates(self) -> tuple[str, ...]:
        """Return registered template IDs in insertion order."""

        return tuple(self._templates)
