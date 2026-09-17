# ADR-0001: Layered responsibility

Status: proposed
Date: 2026-07-20

## Context

The SDK, the MCP server, and the CLI all touch the same domain. Without a stated rule, multi-step logic and product decisions drifted into whichever layer was open. A hidden `get_pipe` inside an SDK method is the symptom: orchestration the caller cannot see, living below the layer that owns the intent. A second question was left open: when can identifier resolution live in the SDK at all?

A later pass found the vocabulary itself defective. [`architecture.md`](../architecture.md) named four roles inside a package: a domain type, a driven adapter, a use case, and a facade. Two of the four have no counterpart in any published model. A facade is a structural pattern, not a layer. A use case placed under a facade inverts the standard stack, where the application layer sits above the domain. That placement made correct code read as a defect. The SDK preflight modules read as an inversion, and a risks entry described an application layer that the SDK never holds.

## Decision

The stack has four layers, top to bottom, which is the path a call travels.

- Presentation. What the outside touches, and what shapes the answer that goes back out.
- Application. Intent and orchestration, which is which operations run to satisfy one request.
- Service. The domain rules and the domain types, where one answer is correct for every caller.
- Gateway. The outbound effect, which is the network, the keychain, the file system, and the log stream.

Two positions are not layers. A facade is the published face of a layer. A composition root sits off the stack, because it builds every part and therefore imports across the direction.

An application holds all four layers. A library holds the bottom two. The SDK and `packages/auth` therefore hold no application layer, which settles where multi-step logic lives inside them with no special rule. Such a behavior is a service, because a library answers every caller the same way.

The SDK is an Open Host Service with a Published Language. It publishes one surface for the CLI, the MCP server, and any external caller, and it accommodates none of them privately. A consumer-specific step inside it is therefore a defect and not a convenience.

The layer order is not the import order on every edge. Presentation imports application, and application imports service, so those two edges agree with the stack. The edge between service and gateway inverts where that edge carries a port, because the service declares the port and the gateway fulfills it. Where the edge carries no port, the service imports the gateway. `PORT-1` to `PORT-3` in [`conventions.md`](../conventions.md) decide which edges earn one.

The SDK is the deterministic execution layer. The application layer, which is the MCP tools and the CLI, owns intent, orchestration, and product policy. The SDK executes a named operation predictably. The application layer decides which operations to run to satisfy an intent.

Place a behavior by its determinism. Deterministic resolution, where the scoping id makes exactly one answer correct, lives in the SDK. The technique is to require the scoping id that makes the key unique, for example resolving `(repo_id, slug)` rather than a bare slug. Genuine ambiguity, where choosing an answer is a judgment call, lives in the application layer.

This split covers the SDK, the CLI, the MCP server, and the shared support libraries (`auth`, `infra`). A library adds a port on a gateway edge only where there is payoff, so a pure-utility library holds none.

## Consequences

A reader locates any behavior by one question: is it how to execute an operation (SDK) or what the user wants (application layer). This is the mainstream split between the application layer and the domain beneath it, so the model is recognizable to any contributor. Resolution placement is the sharpest rule and the least standardized, so it carries the highest teaching burden. A newcomer will not arrive knowing it, and mis-classifying an ambiguous resolution as deterministic puts a judgment call in the wrong layer. No row demands that placement, so a review holds the placement rather than a check.

Three alternatives were rejected. Ports and adapters over one shared application core fails, because a published package cannot hold the front ends' use cases. A shared kernel fails, because it shares domain model, and the duplication found here is application logic. A fifth package fails, because the one duplication found is a vendor-shaped sequence, and that moves down into the service layer instead.

One name now costs something. `services/` in the SDK holds mostly gateways, so the folder name contradicts the layer name until the folder moves. [ADR-0004](0004-vertical-slice-structure.md) carries the folder axis and that rename.

The current rule lives in [`architecture.md`](../architecture.md).
