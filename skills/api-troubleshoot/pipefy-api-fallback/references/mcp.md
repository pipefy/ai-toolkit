# MCP reference

## 3-tier resolution strategy (always follow in order)

| Tier | Method | When |
|------|--------|------|
| **1** | Dedicated MCP tool (`create_card`, `get_phase_cards`, `get_phase_allowed_move_targets`, `update_pipe`, etc.) | Always try first. For card/phase seeding and inventory, see `pipefy-pipes-and-cards` — seed pipe across phases. |
| **2** | Introspection + `execute_graphql` | When no dedicated tool exists or a tool fails unexpectedly. See `pipefy-introspection`. |
| **3** | Direct HTTP via curl / httpx (this skill) | When the MCP server itself is unavailable, or `execute_graphql` fails with an infrastructure error. |

**Do not jump to Tier 3 after a single tool failure.** Follow the tiers in order.

---

## When to use direct API vs MCP tools

| Situation | Use |
|-----------|-----|
| MCP server running normally | MCP tools (Tier 1 or 2) |
| MCP server down / unreachable | Direct API (Tier 3) |
| `execute_graphql` returns 500 error | Direct API (Tier 3) |
| Testing a new mutation before MCP tool exists | `execute_graphql` (Tier 2) — not direct API |

---

The MCP server routes operations and introspection automatically; both endpoints derive from `PIPEFY_BASE_URL`.
