"""Pipe subcommands."""

from __future__ import annotations

from typing import Any

import typer
from pipefy_sdk import (
    CreatePipeLabel,
    CreatePipePhase,
    CreatePipeStartFormField,
    PipefyClient,
)
from pipefy_sdk.graphql_inputs import (
    UpdatePipeInput,
    describe_input_rejection,
)
from pydantic import TypeAdapter, ValidationError

from pipefy_cli.commands._common import (
    ID_POSITIONAL_CONTEXT_SETTINGS,
    confirm_destructive,
    graphql_input_or_bad_parameter,
    parse_json_object,
    parse_json_value,
    resource_id_argument,
    run_cli_command,
)

pipe_app = typer.Typer(help="Pipe operations.", no_args_is_help=True)


def _json_items(raw: str | None, option_name: str, item: Any) -> list[Any] | None:
    """Parse a JSON array option into ``item`` dicts, rejecting unknown keys."""
    parsed = parse_json_value(raw, option_name)
    if parsed is None:
        return None
    try:
        return TypeAdapter(list[item]).validate_python(parsed)
    except ValidationError as exc:
        raise typer.BadParameter(
            f"{option_name}: {describe_input_rejection(exc)}."
        ) from exc


@pipe_app.command("get", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def pipe_get(
    ctx: typer.Context,
    pipe_id: str = resource_id_argument(help="Pipe id."),
    json_out: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Print machine-readable JSON to stdout.",
    ),
) -> None:
    """Load a pipe by id (phases, labels, start form)."""

    async def factory(client: PipefyClient):
        return await client.get_pipe(pipe_id)

    run_cli_command(ctx, json_out, factory)


@pipe_app.command("start-form", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def pipe_start_form(
    ctx: typer.Context,
    pipe_id: str = resource_id_argument(help="Pipe id."),
    required_only: bool = typer.Option(
        False,
        "--required-only",
        help="Return only required fields.",
    ),
    json_out: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """List start-form fields for card creation (``get_start_form_fields``)."""

    async def factory(client: PipefyClient):
        return await client.get_start_form_fields(pipe_id, required_only=required_only)

    run_cli_command(ctx, json_out, factory)


@pipe_app.command("list")
def pipe_list(
    ctx: typer.Context,
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Optional pipe name filter (fuzzy match server-side).",
    ),
    max_per_org: int = typer.Option(
        500,
        "--max-per-org",
        min=1,
        max=500,
        help="Maximum pipes returned per organization (1-500).",
    ),
    json_out: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Search pipes across organizations (same as MCP ``search_pipes``).

    Results are membership scoped: each organization returns only the
    pipes the calling identity is a member of, so the list can fall below
    the org-wide ``pipesCount`` even when nothing was truncated.
    """

    async def factory(client: PipefyClient):
        return await client.search_pipes(name, max_pipes_per_org=max_per_org)

    run_cli_command(ctx, json_out, factory)


@pipe_app.command("create")
def pipe_create(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Display name for the new pipe."),
    org_id: str = typer.Option(
        ...,
        "--org",
        help="Organization id that will own the pipe.",
    ),
    phases: str | None = typer.Option(
        None,
        "--phases",
        help=(
            'JSON array of phases in order, e.g. [{"name": "Triage"}, '
            '{"name": "Done", "done": true}]. Replaces the default phases.'
        ),
    ),
    start_form_fields: str | None = typer.Option(
        None,
        "--start-form-fields",
        help=(
            "JSON array of start form fields: label, type_id, and optional "
            "description, help, required, editable, options."
        ),
    ),
    labels: str | None = typer.Option(
        None,
        "--labels",
        help="JSON array of labels: name and color (hex #RGB or #RRGGBB).",
    ),
    json_out: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Create a pipe, optionally with its phases, start form fields and labels.

    Without ``--phases`` the pipe gets the default phases Inbox, Doing and Done.
    With it, the pipe gets exactly those phases, in order, each connected to the
    phases beside it. The result lists the new phases, fields and labels with ids.
    """

    stripped = name.strip()
    if not stripped:
        typer.echo("Pipe name must be non-empty.", err=True)
        raise typer.Exit(2)
    phase_list = _json_items(phases, "--phases", CreatePipePhase)
    field_list = _json_items(
        start_form_fields, "--start-form-fields", CreatePipeStartFormField
    )
    label_list = _json_items(labels, "--labels", CreatePipeLabel)

    async def factory(client: PipefyClient):
        return await client.create_pipe(
            stripped,
            org_id,
            phases=phase_list,
            start_form_fields=field_list,
            labels=label_list,
        )

    run_cli_command(ctx, json_out, factory)


@pipe_app.command("update", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def pipe_update(
    ctx: typer.Context,
    pipe_id: str = resource_id_argument(help="Pipe id."),
    name: str | None = typer.Option(None, "--name"),
    icon: str | None = typer.Option(None, "--icon"),
    color: str | None = typer.Option(None, "--color"),
    preferences_json: str | None = typer.Option(
        None,
        "--preferences",
        help="JSON object for pipe preferences (UpdatePipeInput).",
    ),
    json_out: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Update pipe settings (pass at least one attribute)."""

    preferences = parse_json_object(preferences_json, "--preferences")
    if preferences == {}:
        preferences = None
    if all(x is None for x in (name, icon, color, preferences)):
        raise typer.BadParameter(
            "Provide at least one of: --name, --icon, --color, --preferences (non-empty)."
        )

    update_input = graphql_input_or_bad_parameter(
        UpdatePipeInput,
        {
            "id": pipe_id,
            "name": name,
            "icon": icon,
            "color": color,
            "preferences": preferences,
        },
    )

    async def factory(client: PipefyClient):
        return await client.update_pipe(update_input)

    run_cli_command(ctx, json_out, factory)


@pipe_app.command("delete", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def pipe_delete(
    ctx: typer.Context,
    pipe_id: str = resource_id_argument(help="Pipe id."),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt.",
    ),
    json_out: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Delete a pipe permanently."""

    confirm_destructive(yes=yes, description=f"pipe {pipe_id}")

    async def factory(client: PipefyClient):
        return await client.delete_pipe(pipe_id)

    run_cli_command(ctx, json_out, factory)


@pipe_app.command("clone", context_settings=ID_POSITIONAL_CONTEXT_SETTINGS)
def pipe_clone(
    ctx: typer.Context,
    template_pipe_id: str = resource_id_argument(
        help="Source pipe id to use as template.",
    ),
    org_id: str | None = typer.Option(
        None,
        "--org",
        help="Optional organization id for the cloned pipe.",
    ),
    json_out: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Clone a pipe from a template pipe id."""

    async def factory(client: PipefyClient):
        return await client.clone_pipe(
            template_pipe_id,
            organization_id=org_id,
        )

    run_cli_command(ctx, json_out, factory)
