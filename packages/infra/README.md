# pipefy-infra

Schema-agnostic helpers that every other `pipefy-*` package imports. It sits at the bottom of the workspace dependency graph and depends only on the standard library, `pydantic`, and `pydantic-settings`. The package root exposes only `__version__`.

- `pipefy_infra.config` finds the Pipefy config directory and reads `config.toml` as a `pydantic-settings` source. [`docs/config.md`](../../docs/config.md) describes the file and the precedence chain.
- `pipefy_infra.security` holds the SSRF defenses for a URL that the toolkit fetches. Import the module and call through it (`security.validate_https_url(...)`), so every call site stays greppable in an audit.

Each function documents its contract in its docstring. The package owns no schema: field definitions live with the settings models that use them, `pipefy_auth.AuthSettings` and `pipefy_sdk.PipefySettings`.
