"""Access the skill catalog shipped with this SDK release."""

from __future__ import annotations

from pathlib import Path

import yaml

SURFACES = frozenset({"sdk", "mcp", "cli"})


class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        mapping = super().construct_mapping(node, deep=deep)
        if len(mapping) != len(node.value):
            raise yaml.constructor.ConstructorError(
                None, None, "duplicate mapping key", node.start_mark
            )
        return mapping


def parse_skill_surfaces(text: str, name: str) -> frozenset[str]:
    """Return supported surfaces after parsing a skill's frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing closing frontmatter delimiter") from exc
    try:
        data = yaml.load("\n".join(lines[1:end]), Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a mapping")
    if data.get("name") != name:
        raise ValueError(f"name must match directory {name!r}")
    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("description must be a non-empty string")
    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a mapping")
    if "surfaces" not in metadata:
        return SURFACES
    value = metadata["surfaces"]
    if not isinstance(value, str) or not value.strip():
        raise ValueError("metadata.surfaces must be a non-empty string")
    tokens = value.split()
    surfaces = frozenset(tokens)
    if surfaces - SURFACES or len(tokens) != len(surfaces):
        raise ValueError("metadata.surfaces must contain unique sdk, mcp, cli tokens")
    return surfaces


def directory() -> Path:
    """Return the directory containing one folder per skill."""
    return Path(__file__).parent
