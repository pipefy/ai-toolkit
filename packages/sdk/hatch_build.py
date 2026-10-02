"""Include the shared skill catalog in SDK wheels and source distributions."""

from __future__ import annotations

from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        root = Path(self.root)
        catalog = root.parent.parent / "skills"
        if not catalog.is_dir():
            catalog = root / "skills"

        skills = sorted(
            path for path in catalog.glob("*/*") if (path / "SKILL.md").is_file()
        )
        if not skills:
            raise RuntimeError("Skill catalog is missing from the SDK build source")

        for skill in skills:
            files = [skill / "SKILL.md", *(skill / "references").glob("**/*")]
            for path in files:
                if not path.is_file():
                    continue
                if self.target_name == "sdist":
                    destination = Path("skills") / path.relative_to(catalog)
                else:
                    destination = (
                        Path("pipefy_sdk/skills") / skill.name / path.relative_to(skill)
                    )
                build_data["force_include"][str(path)] = destination.as_posix()
