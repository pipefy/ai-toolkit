"""Write the page list of a docs section landing page from the front matter of its pages."""

from __future__ import annotations

from pathlib import Path

import yaml

KIND_FOLDERS = (
    ("tutorial", "Tutorials"),
    ("how-to", "How-to guides"),
    ("reference", "Reference"),
    ("explanation", "Explanation"),
)


def front_matter(page: Path) -> dict[str, str]:
    _, block, _ = page.read_text(encoding="utf-8").split("---\n", 2)
    return yaml.safe_load(block)


def page_list(section: Path) -> str:
    lines: list[str] = []
    for folder, heading in KIND_FOLDERS:
        pages = sorted((section / folder).glob("*.md"))
        if not pages:
            continue
        lines += [f"### {heading}", ""]
        for page in pages:
            meta = front_matter(page)
            link = page.relative_to(section).as_posix()
            lines.append(f"- [{meta['title']}]({link}): {meta['description']}")
        lines.append("")
    return "\n".join(lines).rstrip()
