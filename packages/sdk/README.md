# pipefy

Python SDK for Pipefy's GraphQL API. `pipefy-mcp-server` and `pipefy-cli` call Pipefy through it. It owns the HTTP and GraphQL transport, the service classes, the query constants, the Pydantic models, the settings, and the exceptions.

The distribution is named `pipefy`, and the import module is `pipefy_sdk`.

```python
from pipefy_sdk import PipefyClient

client = PipefyClient(...)
card = await client.get_card(card_id="12345")
```

[`docs/sdk/README.md`](https://github.com/pipefy/ai-toolkit/blob/main/docs/sdk/README.md) explains how to use the library, and [`docs/config.md`](https://github.com/pipefy/ai-toolkit/blob/main/docs/config.md) lists the `PIPEFY_*` variables that its settings read.
