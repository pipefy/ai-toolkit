"""``docs/config.md`` names every settings variable, and its TOML example sets only real fields."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
from pipefy_auth.settings import AuthSettings, JwtValidationSettings
from pipefy_mcp.settings import IpaasSettings, McpSettings, ResourceServerSettings
from pipefy_sdk.settings import PipefySettings
from pydantic import AliasChoices

_CONFIG_MD = Path(__file__).resolve().parent.parent / "docs" / "config.md"

# The models that load ``config.toml`` through ``PipefyTomlConfigSource``.
_TOML_MODELS = (AuthSettings, PipefySettings, McpSettings)
_ENV_MODELS = (
    *_TOML_MODELS,
    JwtValidationSettings,
    ResourceServerSettings,
    IpaasSettings,
)


def env_names(model):
    """Map each field of a settings model to the environment variable names that set it."""
    prefix = model.model_config.get("env_prefix", "")
    names = {}
    for field, info in model.model_fields.items():
        alias = info.validation_alias
        if isinstance(alias, AliasChoices):
            names[field] = [str(choice) for choice in alias.choices]
        elif isinstance(alias, str):
            names[field] = [alias]
        else:
            names[field] = [f"{prefix}{field}".upper()]
    return names


def _doc():
    return _CONFIG_MD.read_text(encoding="utf-8")


def _toml_example_keys():
    block = re.search(r"```toml\n(.*?)```", _doc(), re.DOTALL)
    assert block, "docs/config.md has no ```toml example"
    return set(tomllib.loads(block.group(1)))


@pytest.mark.parametrize("model", _ENV_MODELS, ids=lambda m: m.__name__)
def test_every_settings_variable_is_documented(model):
    documented = set(re.findall(r"`(PIPEFY_[A-Z0-9_]+)`", _doc()))
    missing = [
        names[0] for names in env_names(model).values() if not documented & set(names)
    ]
    assert not missing, f"docs/config.md does not name: {', '.join(missing)}"


def test_toml_example_sets_only_real_fields():
    fields = {field for model in _TOML_MODELS for field in model.model_fields}
    unknown = sorted(_toml_example_keys() - fields)
    assert not unknown, (
        f"docs/config.md TOML example sets unknown keys: {', '.join(unknown)}"
    )
