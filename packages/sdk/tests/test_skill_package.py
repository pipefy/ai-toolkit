"""Check that SDK builds carry the versioned skill catalog."""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "skills"


def catalog_files() -> set[str]:
    return {
        f"pipefy_sdk/skills/{skill.name}/{path.relative_to(skill).as_posix()}"
        for skill in CATALOG.glob("*/*")
        if (skill / "SKILL.md").is_file()
        for path in [skill / "SKILL.md", *(skill / "references").glob("**/*")]
        if path.is_file()
    }


@pytest.fixture(scope="module")
def artifacts(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    output = tmp_path_factory.mktemp("sdk-dist")
    subprocess.run(
        ["uv", "build", "--package", "pipefy", "--wheel", "--sdist", "-o", str(output)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return next(output.glob("*.whl")), next(output.glob("*.tar.gz"))


def test_directory_points_to_installed_catalog(
    artifacts: tuple[Path, Path], tmp_path: Path
) -> None:
    wheel, _ = artifacts
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(tmp_path)
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from pipefy_sdk import skills; "
            "root = skills.directory(); "
            "assert (root / 'pipefy-reports' / 'SKILL.md').is_file(); "
            "assert (root / 'pipefy-reports' / 'references' / 'mcp.md').is_file(); "
            "assert 'sdk' in skills.parse_skill_surfaces("
            "(root / 'pipefy-reports' / 'SKILL.md').read_text(), 'pipefy-reports'); "
            "assert 'sdk' not in skills.parse_skill_surfaces("
            "(root / 'pipefy-ipaas' / 'SKILL.md').read_text(), 'pipefy-ipaas')",
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        check=True,
        capture_output=True,
        text=True,
    )


def test_wheel_contains_flat_catalog(artifacts: tuple[Path, Path]) -> None:
    wheel, _ = artifacts
    with zipfile.ZipFile(wheel) as archive:
        packaged = {
            name for name in archive.namelist() if name.startswith("pipefy_sdk/skills/")
        }
        assert packaged == catalog_files() | {"pipefy_sdk/skills/__init__.py"}


def test_wheel_declares_yaml_runtime_dependency(artifacts: tuple[Path, Path]) -> None:
    wheel, _ = artifacts
    with zipfile.ZipFile(wheel) as archive:
        metadata = next(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        assert "Requires-Dist: pyyaml" in archive.read(metadata).decode()


def test_sdist_can_rebuild_wheel_with_catalog(
    artifacts: tuple[Path, Path], tmp_path: Path
) -> None:
    _, sdist = artifacts
    with tarfile.open(sdist, "r:gz") as archive:
        archive.extractall(tmp_path, filter="data")
    source = next(tmp_path.iterdir())
    rebuilt = tmp_path / "rebuilt"
    subprocess.run(
        ["uv", "build", "--wheel", "-o", str(rebuilt), str(source)],
        check=True,
        capture_output=True,
        text=True,
    )
    with zipfile.ZipFile(next(rebuilt.glob("*.whl"))) as archive:
        packaged = {
            name for name in archive.namelist() if name.startswith("pipefy_sdk/skills/")
        }
        assert packaged == catalog_files() | {"pipefy_sdk/skills/__init__.py"}
