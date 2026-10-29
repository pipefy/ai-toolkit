"""Tests for scripts/smoke_entry_points.py.

The script itself only runs inside a throwaway virtualenv in CI, so the logic that
decides *what* to launch -- and what counts as a failure -- is covered here, where
it runs on every suite. The two drift tests at the bottom are the point of the
explicit constants: they tie them to the workspace's own `pyproject.toml` files,
so adding a package or an entry point fails the suite instead of quietly
narrowing what the packaging gate checks.
"""

from __future__ import annotations

import importlib.util
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO_ROOT / "scripts" / "smoke_entry_points.py"
_spec = importlib.util.spec_from_file_location("smoke_entry_points", _SCRIPT)
assert _spec and _spec.loader
_smoke = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_smoke)


@dataclass(frozen=True)
class FakeEntryPoint:
    name: str
    group: str = "console_scripts"


@dataclass(frozen=True)
class FakeDistribution:
    """Stands in for importlib.metadata.Distribution: name plus entry points."""

    name: str
    entry_points: tuple[FakeEntryPoint, ...] = ()


def _full_install() -> list[FakeDistribution]:
    """Every published member installed, with the scripts they really ship."""
    return [
        FakeDistribution("pipefy"),
        FakeDistribution("pipefy-auth"),
        FakeDistribution("pipefy-infra"),
        FakeDistribution("pipefy-cli", (FakeEntryPoint("pipefy"),)),
        FakeDistribution("pipefy-mcp-server", (FakeEntryPoint("pipefy-mcp-server"),)),
    ]


# Wheel filenames as `uv build --all-packages --wheel` writes them: the
# distribution name is escaped with underscores.
_COMPLETE_WHEELS = [
    "pipefy-0.5.0a1-py3-none-any.whl",
    "pipefy_auth-0.5.0a1-py3-none-any.whl",
    "pipefy_cli-0.5.0a1-py3-none-any.whl",
    "pipefy_infra-0.5.0a1-py3-none-any.whl",
    "pipefy_mcp_server-0.5.0a1-py3-none-any.whl",
]


def _write_wheels(directory: Path, names: list[str]) -> None:
    for name in names:
        (directory / name).touch()


@dataclass
class FakeRunner:
    """Records the argv of each launch and replays canned results."""

    returncode: int = 0
    stderr: str = ""
    stdout: str = ""
    raises: BaseException | None = None
    calls: list[list[str]] = field(default_factory=list)

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        if self.raises is not None:
            raise self.raises
        return subprocess.CompletedProcess(
            argv, self.returncode, stdout=self.stdout, stderr=self.stderr
        )


class TestCanonicalName:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("pipefy-cli", "pipefy-cli"),
            ("pipefy_cli", "pipefy-cli"),
            ("Pipefy_MCP.Server", "pipefy-mcp-server"),
            ("pipefy__cli", "pipefy-cli"),
        ],
    )
    def test_normalizes_to_pep_503(self, raw: str, expected: str) -> None:
        assert _smoke.canonical_name(raw) == expected


class TestIndexPublished:
    def test_keeps_only_workspace_members(self) -> None:
        dists = [*_full_install(), FakeDistribution("httpx"), FakeDistribution("typer")]
        assert set(_smoke.index_published(dists)) == set(_smoke.PUBLISHED_DISTRIBUTIONS)

    def test_indexes_wheel_style_names_under_their_canonical_form(self) -> None:
        """A wheel records `pipefy_mcp_server`; the constant spells it with hyphens."""
        found = _smoke.index_published([FakeDistribution("pipefy_mcp_server")])
        assert set(found) == {"pipefy-mcp-server"}


class TestResolveScripts:
    def test_names_the_member_missing_from_the_install(self) -> None:
        partial = [d for d in _full_install() if d.name != "pipefy-infra"]
        with pytest.raises(
            _smoke.SmokeError, match="missing from the install: pipefy-infra"
        ):
            _smoke.resolve_scripts(_smoke.index_published(partial))

    def test_fails_when_an_installed_wheel_ships_no_entry_point(self) -> None:
        """Discovery alone would read a lost script as success; the floor catches it."""
        without_mcp_script = [
            d
            if d.name != "pipefy-mcp-server"
            else FakeDistribution("pipefy-mcp-server")
            for d in _full_install()
        ]
        with pytest.raises(
            _smoke.SmokeError, match="no console script named pipefy-mcp-server"
        ):
            _smoke.resolve_scripts(_smoke.index_published(without_mcp_script))

    def test_returns_the_required_scripts_sorted(self) -> None:
        scripts = _smoke.resolve_scripts(_smoke.index_published(_full_install()))
        assert scripts == ["pipefy", "pipefy-mcp-server"]

    def test_covers_a_newly_added_entry_point_without_a_code_change(self) -> None:
        extended = [
            d
            if d.name != "pipefy-cli"
            else FakeDistribution(
                "pipefy-cli", (FakeEntryPoint("pipefy"), FakeEntryPoint("pipefy-admin"))
            )
            for d in _full_install()
        ]
        scripts = _smoke.resolve_scripts(_smoke.index_published(extended))
        assert scripts == ["pipefy", "pipefy-admin", "pipefy-mcp-server"]

    def test_ignores_non_console_entry_points(self) -> None:
        with_plugin = [
            d
            if d.name != "pipefy"
            else FakeDistribution(
                "pipefy", (FakeEntryPoint("some_plugin", group="pytest11"),)
            )
            for d in _full_install()
        ]
        scripts = _smoke.resolve_scripts(_smoke.index_published(with_plugin))
        assert scripts == ["pipefy", "pipefy-mcp-server"]


class TestCheckWheels:
    """Membership must fail closed before pip runs, not after the install."""

    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("pipefy-0.5.0a1-py3-none-any.whl", "pipefy"),
            ("pipefy_mcp_server-0.5.0a1-py3-none-any.whl", "pipefy-mcp-server"),
            ("pipefy_cli-1.0.0-py3-none-any.whl", "pipefy-cli"),
        ],
    )
    def test_reads_the_distribution_from_the_filename(
        self, filename: str, expected: str
    ) -> None:
        assert _smoke.wheel_distribution(filename) == expected

    @pytest.mark.parametrize("distribution", sorted(_smoke.PUBLISHED_DISTRIBUTIONS))
    def test_wheel_stem_round_trips_every_published_member(
        self, distribution: str
    ) -> None:
        """`release.py` derives the wheel set it requires on a Release from this.

        The escaping is the whole risk: `pipefy-mcp-server` builds as
        `pipefy_mcp_server-...`, so a stem taken from the name as written would
        match nothing and read as a missing wheel.
        """
        stem = _smoke.wheel_stem(distribution)
        assert (
            _smoke.wheel_distribution(f"{stem}1.2.3-py3-none-any.whl") == distribution
        )
        assert "-" not in stem[:-1]

    def test_accepts_one_wheel_per_member(self, tmp_path: Path) -> None:
        _write_wheels(tmp_path, _COMPLETE_WHEELS)
        assert _smoke.check_wheels(tmp_path) == sorted(_COMPLETE_WHEELS)

    def test_rejects_a_missing_member(self, tmp_path: Path) -> None:
        """The regression this guard exists for.

        `pip install <dir>/*.whl` does not fail on an incomplete set: the sibling
        `==` pins let it satisfy the absent member from the index, so the smoke
        passes against a wheel the build never produced.
        """
        _write_wheels(tmp_path, [w for w in _COMPLETE_WHEELS if "infra" not in w])
        with pytest.raises(_smoke.SmokeError, match="has no wheel for: pipefy-infra"):
            _smoke.check_wheels(tmp_path)

    def test_rejects_an_empty_directory(self, tmp_path: Path) -> None:
        with pytest.raises(_smoke.SmokeError, match="has no wheel for:"):
            _smoke.check_wheels(tmp_path)

    def test_rejects_an_unexpected_sixth_member(self, tmp_path: Path) -> None:
        _write_wheels(
            tmp_path, [*_COMPLETE_WHEELS, "pipefy_extra-0.1.0-py3-none-any.whl"]
        )
        with pytest.raises(
            _smoke.SmokeError, match="unexpected wheel for: pipefy-extra"
        ):
            _smoke.check_wheels(tmp_path)

    def test_rejects_two_versions_of_one_member(self, tmp_path: Path) -> None:
        _write_wheels(
            tmp_path, [*_COMPLETE_WHEELS, "pipefy_cli-0.4.0b2-py3-none-any.whl"]
        )
        with pytest.raises(
            _smoke.SmokeError, match="more than one wheel for: pipefy-cli"
        ):
            _smoke.check_wheels(tmp_path)


class TestLaunch:
    def test_runs_help_for_each_script_from_the_venv_bin(self, tmp_path: Path) -> None:
        for name in ("pipefy", "pipefy-mcp-server"):
            (tmp_path / name).touch()
        runner = FakeRunner()
        _smoke.launch(["pipefy", "pipefy-mcp-server"], tmp_path, runner=runner)
        assert runner.calls == [
            [str(tmp_path / "pipefy"), "--help"],
            [str(tmp_path / "pipefy-mcp-server"), "--help"],
        ]

    def test_fails_when_the_declared_script_is_not_on_disk(
        self, tmp_path: Path
    ) -> None:
        runner = FakeRunner()
        with pytest.raises(_smoke.SmokeError, match="does not exist"):
            _smoke.launch(["pipefy"], tmp_path, runner=runner)
        assert runner.calls == []

    def test_surfaces_the_exit_code_and_stderr(self, tmp_path: Path) -> None:
        (tmp_path / "pipefy").touch()
        runner = FakeRunner(
            returncode=1, stderr="ModuleNotFoundError: mcp.server.fastmcp"
        )
        with pytest.raises(_smoke.SmokeError, match="mcp.server.fastmcp") as excinfo:
            _smoke.launch(["pipefy"], tmp_path, runner=runner)
        assert "exited 1" in str(excinfo.value)

    def test_falls_back_to_stdout_when_stderr_is_empty(self, tmp_path: Path) -> None:
        (tmp_path / "pipefy").touch()
        runner = FakeRunner(returncode=2, stdout="usage error on stdout")
        with pytest.raises(_smoke.SmokeError, match="usage error on stdout"):
            _smoke.launch(["pipefy"], tmp_path, runner=runner)

    def test_a_hung_launch_is_a_failure_not_a_stall(self, tmp_path: Path) -> None:
        (tmp_path / "pipefy").touch()
        runner = FakeRunner(raises=subprocess.TimeoutExpired(cmd="pipefy", timeout=120))
        with pytest.raises(_smoke.SmokeError, match="did not return within"):
            _smoke.launch(["pipefy"], tmp_path, runner=runner)

    def test_stops_at_the_first_failure(self, tmp_path: Path) -> None:
        for name in ("pipefy", "pipefy-mcp-server"):
            (tmp_path / name).touch()
        runner = FakeRunner(returncode=1)
        with pytest.raises(_smoke.SmokeError):
            _smoke.launch(["pipefy", "pipefy-mcp-server"], tmp_path, runner=runner)
        assert len(runner.calls) == 1


class TestAuthenticatedCall:
    """Runs the real SDK from the workspace venv against the stub endpoint."""

    def test_passes_when_the_sdk_sends_the_bearer(self) -> None:
        _smoke.authenticated_call()

    def test_ignores_the_operators_pipefy_settings(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Schema reuse would send an introspection query the stub cannot answer."""
        monkeypatch.setenv("PIPEFY_GQL_REUSE_FETCHED_GRAPHQL_SCHEMA", "true")
        _smoke.authenticated_call()

    def test_bypasses_an_environment_proxy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for name in ("HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
            monkeypatch.setenv(name, "http://127.0.0.1:9")
        _smoke.authenticated_call()

    def test_a_loopback_bind_failure_is_a_smoke_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def refuse(*_args: object) -> None:
            raise PermissionError("bind refused")

        monkeypatch.setattr(_smoke, "ThreadingHTTPServer", refuse)
        with pytest.raises(_smoke.SmokeError, match="bind refused"):
            _smoke.authenticated_call()

    def test_a_wrong_payload_is_a_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def answer_null_me(handler) -> None:
            handler.rfile.read(int(handler.headers.get("Content-Length", 0)))
            handler._reply(200, b'{"data": {"me": null}}', "application/json")

        monkeypatch.setattr(_smoke._StubGraphQLHandler, "do_POST", answer_null_me)
        with pytest.raises(_smoke.SmokeError, match="get_me returned None"):
            _smoke.authenticated_call()

    def test_a_rejected_bearer_is_a_failure(self) -> None:
        with pytest.raises(_smoke.SmokeError, match="401"):
            _smoke.authenticated_call(token="wrong-token")

    def test_fails_when_the_transport_builds_an_httpx2_client(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The break this check exists for: gql 4.4 picks httpx2 when it is installed."""
        httpx2 = pytest.importorskip("httpx2")
        import gql.transport.httpx as gql_httpx

        monkeypatch.setattr(gql_httpx, "httpx", httpx2)
        with pytest.raises(_smoke.SmokeError, match='Invalid "auth" argument'):
            _smoke.authenticated_call()


class TestMain:
    def test_reports_failure_on_stderr_and_exits_non_zero(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(_smoke, "distributions", lambda: [])
        assert _smoke.main() == 1
        assert "packaging smoke failed" in capsys.readouterr().err

    def test_succeeds_when_every_entry_point_launches(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        for name in ("pipefy", "pipefy-mcp-server"):
            (tmp_path / name).touch()
        runner = FakeRunner()
        calls: list[str] = []
        monkeypatch.setattr(_smoke, "distributions", _full_install)
        monkeypatch.setattr(_smoke.sysconfig, "get_path", lambda _name: str(tmp_path))
        monkeypatch.setattr(_smoke.subprocess, "run", runner)
        monkeypatch.setattr(
            _smoke, "authenticated_call", lambda: calls.append("authenticated_call")
        )
        assert _smoke.main() == 0
        assert "an authenticated call went through." in capsys.readouterr().out
        # Asserted explicitly: without this, removing the launch() or the
        # authenticated_call() from main leaves both the exit code and the
        # banner intact.
        assert runner.calls == [
            [str(tmp_path / "pipefy"), "--help"],
            [str(tmp_path / "pipefy-mcp-server"), "--help"],
        ]
        assert calls == ["authenticated_call"]

    def test_a_failed_authenticated_call_exits_non_zero(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        for name in ("pipefy", "pipefy-mcp-server"):
            (tmp_path / name).touch()

        def fail() -> None:
            raise _smoke.SmokeError("TypeError: Invalid auth argument")

        monkeypatch.setattr(_smoke, "distributions", _full_install)
        monkeypatch.setattr(_smoke.sysconfig, "get_path", lambda _name: str(tmp_path))
        monkeypatch.setattr(_smoke.subprocess, "run", FakeRunner())
        monkeypatch.setattr(_smoke, "authenticated_call", fail)
        assert _smoke.main() == 1
        assert "Invalid auth argument" in capsys.readouterr().err

    def test_check_wheels_mode_passes_on_a_complete_directory(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        _write_wheels(tmp_path, _COMPLETE_WHEELS)
        assert _smoke.main(["--check-wheels", str(tmp_path)]) == 0
        assert "holds one wheel per published member" in capsys.readouterr().out

    def test_check_wheels_mode_fails_on_an_incomplete_directory(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        _write_wheels(tmp_path, [w for w in _COMPLETE_WHEELS if "infra" not in w])
        assert _smoke.main(["--check-wheels", str(tmp_path)]) == 1
        assert "has no wheel for: pipefy-infra" in capsys.readouterr().err

    @pytest.mark.parametrize("argv", [["--check-wheels"], ["--check-wheels", "a", "b"]])
    def test_rejects_a_malformed_invocation(
        self, argv: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert _smoke.main(argv) == 1
        assert "usage:" in capsys.readouterr().err

    def test_rejects_an_unknown_argument(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert _smoke.main(["--launch-everything"]) == 1
        assert "usage:" in capsys.readouterr().err


class TestConstantsTrackTheWorkspace:
    """The explicit constants exist to force a decision when packaging changes."""

    @staticmethod
    def _workspace_pyprojects() -> list[dict]:
        return [
            tomllib.loads(path.read_text(encoding="utf-8"))
            for path in sorted((_REPO_ROOT / "packages").glob("*/pyproject.toml"))
        ]

    def test_published_distributions_matches_the_workspace_members(self) -> None:
        declared = {
            _smoke.canonical_name(data["project"]["name"])
            for data in self._workspace_pyprojects()
        }
        assert declared == set(_smoke.PUBLISHED_DISTRIBUTIONS)

    def test_required_scripts_matches_the_declared_console_scripts(self) -> None:
        declared = {
            name
            for data in self._workspace_pyprojects()
            for name in data["project"].get("scripts", {})
        }
        assert declared == set(_smoke.REQUIRED_SCRIPTS)
