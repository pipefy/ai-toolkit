#!/usr/bin/env python3
"""Guard the packaging smoke install: check the wheels, then launch every command.

Two modes, both keyed off one list of published members
(``PUBLISHED_DISTRIBUTIONS``):

``--check-wheels <directory>``
    Run with any interpreter, **before** the install. Asserts the directory holds
    exactly one wheel per published member. An incomplete set must not reach
    ``pip``: the sibling ``==`` pins let pip resolve the absent member from the
    index, so the smoke would pass against an artifact this build never produced.

no arguments
    Run with the **smoke virtualenv's** interpreter, after the install::

        .venv-smoke/bin/python scripts/smoke_entry_points.py

    Launches every console entry point. It reads installed distribution metadata
    rather than the checkout's ``pyproject.toml`` files, so it reports what an
    install actually exposes: a wheel that ships without its entry point, or a
    member missing from the install, fails here. Then it makes one authenticated
    GraphQL call through the installed SDK against a local stub endpoint, so a
    break between the auth classes and the resolved HTTP stack fails here too.

Three workflows share this script -- ``ci.yml``, ``release.yml``, and
``packaging-smoke.yml`` -- as does ``release.py``, which runs both modes before
the tag push so the same check happens while it is still free. "Every published
entry point" therefore has one definition instead of a launch list copied into
each job, where a newly added script would have to be remembered four times.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import sysconfig
import threading
from collections.abc import Callable, Iterable, Mapping, Sequence
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import Distribution, distributions
from pathlib import Path
from unittest.mock import patch

# The workspace members published to PyPI. Explicit rather than discovered so
# that adding a member forces a decision here; release.yml guards the same list
# from the wheel side (it fails unless dist/ holds exactly one wheel per member).
PUBLISHED_DISTRIBUTIONS = frozenset(
    {"pipefy", "pipefy-auth", "pipefy-cli", "pipefy-infra", "pipefy-mcp-server"}
)

# Every discovered script is launched, so a newly added entry point is covered
# without touching this file. This floor is what catches a *lost* one, which
# discovery alone would read as success.
REQUIRED_SCRIPTS = frozenset({"pipefy", "pipefy-mcp-server"})

LAUNCH_TIMEOUT_SECONDS = 120

# The bearer the stub endpoint accepts, and the ``me`` payload it answers with.
SMOKE_BEARER_TOKEN = "packaging-smoke-token"
SMOKE_ME = {"email": "smoke@example.com", "name": "Packaging Smoke"}

USAGE = "usage: smoke_entry_points.py [--check-wheels <directory>]"

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


class SmokeError(RuntimeError):
    """A fresh install is missing a package or a script, or fails to launch one."""


def canonical_name(raw: str) -> str:
    """Normalize to PEP 503 form, so ``pipefy_cli`` and ``pipefy-cli`` compare equal."""
    return re.sub(r"[-_.]+", "-", raw).lower()


def index_published(dists: Iterable[Distribution]) -> dict[str, Distribution]:
    """Map canonical name to distribution, keeping only published workspace members."""
    found: dict[str, Distribution] = {}
    for dist in dists:
        name = canonical_name(dist.name)
        if name in PUBLISHED_DISTRIBUTIONS:
            found.setdefault(name, dist)
    return found


def resolve_scripts(found: Mapping[str, Distribution]) -> list[str]:
    """Return the console scripts the installed members declare, or raise."""
    missing = sorted(PUBLISHED_DISTRIBUTIONS - set(found))
    if missing:
        raise SmokeError(
            f"missing from the install: {', '.join(missing)}. "
            "A fresh install must carry every published workspace member."
        )
    scripts = {
        entry_point.name
        for dist in found.values()
        for entry_point in dist.entry_points
        if entry_point.group == "console_scripts"
    }
    absent = sorted(REQUIRED_SCRIPTS - scripts)
    if absent:
        raise SmokeError(
            f"installed, but no console script named {', '.join(absent)}: "
            "a wheel stopped shipping its entry point."
        )
    return sorted(scripts)


def wheel_distribution(filename: str) -> str:
    """Read the distribution name out of a wheel filename (PEP 427 name-version-...)."""
    return canonical_name(filename.split("-")[0])


def wheel_stem(distribution: str) -> str:
    """The filename prefix wheels of ``distribution`` carry, up to the version dash.

    The inverse of ``wheel_distribution``: a wheel filename escapes the
    distribution name (``pipefy-mcp-server`` builds as
    ``pipefy_mcp_server-<version>-...whl``), so a caller matching wheels by name
    cannot use the distribution name as written. ``release.py`` derives what a
    GitHub Release must attach through this, so the published-member list stays
    one definition rather than a hand-escaped copy.
    """
    return f"{canonical_name(distribution).replace('-', '_')}-"


def check_wheels(directory: str | Path) -> list[str]:
    """Assert the directory holds exactly one wheel per published member.

    Installing an incomplete set is not a hard error for pip: it satisfies the
    absent member from the index through the sibling ``==`` pins, and the smoke
    then passes against a wheel this build never produced. So the membership
    check has to happen before the install, not after it.
    """
    wheels = sorted(path.name for path in Path(directory).glob("*.whl"))
    by_distribution: dict[str, list[str]] = {}
    for name in wheels:
        by_distribution.setdefault(wheel_distribution(name), []).append(name)

    missing = sorted(PUBLISHED_DISTRIBUTIONS - set(by_distribution))
    if missing:
        raise SmokeError(
            f"{directory} has no wheel for: {', '.join(missing)}. "
            "pip would resolve that member from the index instead, so the smoke "
            "would test an artifact this build did not produce."
        )
    unexpected = sorted(set(by_distribution) - PUBLISHED_DISTRIBUTIONS)
    if unexpected:
        raise SmokeError(
            f"{directory} holds an unexpected wheel for: {', '.join(unexpected)}. "
            "Add the member to PUBLISHED_DISTRIBUTIONS, or remove the wheel."
        )
    duplicated = sorted(
        name for name, built in by_distribution.items() if len(built) > 1
    )
    if duplicated:
        raise SmokeError(
            f"{directory} holds more than one wheel for: {', '.join(duplicated)}. "
            "A wheel left over from an earlier version makes the install ambiguous."
        )
    return wheels


def launch(
    scripts: Sequence[str],
    script_dir: str | Path,
    runner: Runner | None = None,
) -> None:
    """Run ``<script> --help`` for each script, raising on the first failure."""
    # Resolved here rather than as a default argument, which would bind
    # subprocess.run once at import and ignore any later substitution.
    runner = runner if runner is not None else subprocess.run
    for script in scripts:
        path = Path(script_dir) / script
        if not path.exists():
            raise SmokeError(
                f"{script} is declared in the installed metadata, but {path} does not exist."
            )
        try:
            completed = runner(
                [str(path), "--help"],
                capture_output=True,
                text=True,
                timeout=LAUNCH_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise SmokeError(
                f"{script} --help did not return within {LAUNCH_TIMEOUT_SECONDS}s."
            ) from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise SmokeError(
                f"{script} --help exited {completed.returncode}.\n{detail}"
            )
        print(f"  {script} --help -> ok")


class _StubGraphQLHandler(BaseHTTPRequestHandler):
    """Answer a POST carrying the smoke bearer with ``me``; answer anything else 401."""

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.headers.get("Authorization") != f"Bearer {SMOKE_BEARER_TOKEN}":
            self._reply(401, b"Unauthorized", "text/plain")
            return
        body = json.dumps({"data": {"me": SMOKE_ME}}).encode()
        self._reply(200, body, "application/json")

    def _reply(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


def authenticated_call(token: str = SMOKE_BEARER_TOKEN) -> None:
    """Run one ``get_me`` through the installed SDK against a local stub endpoint.

    ``--help`` never builds an HTTP client, so it cannot see a break between the
    ``httpx.Auth`` classes in ``pipefy_auth`` and the HTTP stack gql resolves at
    install time. gql 4.4 builds an ``httpx2`` client whenever ``httpx2`` is
    installed, and that client rejects those classes on every call. This builds
    ``PipefyClient`` with a bearer, as the CLI and MCP server do, and sends a real
    request over loopback.
    """
    # Imported here: --check-wheels runs under an interpreter without the SDK.
    from pipefy_auth import StaticBearerAuth
    from pipefy_sdk import PipefyClient, PipefySettings

    try:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _StubGraphQLHandler)
    except OSError as exc:
        raise SmokeError(
            f"could not start the stub endpoint on loopback: {exc}"
        ) from exc
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        # model_construct skips the env, .env and config.toml sources and
        # validation, so the operator's own settings cannot change the request.
        settings = PipefySettings.model_construct(
            base_url=f"http://127.0.0.1:{server.server_port}"
        )
        client = PipefyClient(settings, auth=StaticBearerAuth(token))
        with patch.dict(os.environ, {"NO_PROXY": "*", "no_proxy": "*"}):
            me = asyncio.run(client.get_me())
    except Exception as exc:
        raise SmokeError(
            "an authenticated GraphQL call through the installed SDK failed: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    finally:
        server.shutdown()
        server.server_close()
    if me != SMOKE_ME:
        raise SmokeError(f"get_me returned {me!r}, expected {SMOKE_ME!r}.")
    print("  authenticated get_me through the SDK -> ok")


def main(argv: Sequence[str] | None = None) -> int:
    # sys.argv is read at the entry point below, never here: a default that
    # reached for it would pick up the arguments of whatever runs this module.
    args = [] if argv is None else list(argv)
    try:
        if args[:1] == ["--check-wheels"]:
            if len(args) != 2:
                raise SmokeError(USAGE)
            directory = args[1]
            wheels = check_wheels(directory)
            print(f"{directory} holds one wheel per published member:")
            for name in wheels:
                print(f"  {name}")
            return 0
        if args:
            raise SmokeError(USAGE)
        script_dir = sysconfig.get_path("scripts")
        scripts = resolve_scripts(index_published(distributions()))
        print(f"Launching {len(scripts)} console entry point(s) from {script_dir}")
        launch(scripts, script_dir)
        authenticated_call()
    except SmokeError as exc:
        print(f"packaging smoke failed: {exc}", file=sys.stderr)
        return 1
    print(
        "Every published console entry point launched, and an authenticated call went through."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
