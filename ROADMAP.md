# Roadmap

## Phase 1 — Direct servers (shipped)

- One plugin registering **23 MCP servers** (233 tools) over public life-sciences databases.
- Self-contained: bootstraps its own Python virtualenv, no Claude Science dependency.
- Every server integration-tested.
- Host support: **Claude Code**.

## Phase 2 — Multi-framework support

- Extend beyond Claude Code to other agent frameworks and MCP hosts.

## Phase 3 — Dynamic tool discovery

- Expose tools on demand instead of loading all 233 definitions up front, to reduce
  per-session process count and context cost.
- Offer both a direct mode and a discovery mode; document the trade-offs.
