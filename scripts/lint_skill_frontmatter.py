"""Parse skill frontmatter and reject invalid surface declarations."""

from __future__ import annotations

import sys
from pathlib import Path

from pipefy_sdk.skills import parse_skill_surfaces


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("skills")
    paths = sorted(root.rglob("SKILL.md"))
    if not paths:
        print(f"{root}: no SKILL.md files found", file=sys.stderr)
        return 1
    errors = []
    for path in paths:
        try:
            parse_skill_surfaces(path.read_text(encoding="utf-8"), path.parent.name)
        except ValueError as exc:
            errors.append(f"{path}: {exc}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Skill frontmatter validation passed ({len(paths)} skills).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
