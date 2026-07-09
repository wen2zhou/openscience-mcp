# Contributing to openscience-mcp

Thanks for your interest! This is an operational guide — read it before opening a PR.

## What this project is

`openscience-mcp` is a single Claude Code plugin that registers 23 life-sciences
MCP servers. The servers under `plugins/openscience/runtime/lib/` are **vendored**
from the Claude Science bundled bio-tools MCP servers; the plugin bootstraps its
own virtualenv so it runs with no Claude Science installation.

## Repository layout

```
plugins/openscience/
  .claude-plugin/plugin.json   # plugin manifest (config)
  .mcp.json                    # registers the 23 servers (config)
  bin/launch.sh                # first-party launcher (venv bootstrap + stdio)
  runtime/lib/                 # VENDORED upstream server code — do not hand-edit
  runtime/requirements.txt     # pinned deps (must match the vendored snapshot)
tests/
  launch_smoke.sh              # launcher unit + integration tests
  test_all_servers.py          # full 23-server handshake + representative calls
.claude-plugin/marketplace.json
```

## Prerequisites

- Claude Code (recent version with plugin support)
- Python ≥ 3.11 on your `PATH`
- Network access on first run (to build the venv and `pip install`)

## The one rule about vendored code

**Do not hand-edit `plugins/openscience/runtime/lib/`.** It is vendored upstream
code, refreshed by maintainers via a private sync tool. If a server returns wrong
results or errors against its upstream database, that is almost always an upstream
issue — open an issue describing it rather than patching the vendored tree. PRs
that modify `runtime/lib/` by hand will be asked for changes.

First-party code you *can* change: `bin/launch.sh`, `tests/`, the JSON config,
and docs.

## Running tests locally

Fast launcher unit tests (no network):

```shell
SKIP_INTEGRATION=1 bash tests/launch_smoke.sh
```

Full launcher test (builds a real venv + MCP handshake, ~1 min first run):

```shell
bash tests/launch_smoke.sh
```

Full integration sweep — boots every server, enumerates tools, runs a
representative live call per server (needs network; upstream databases may
rate-limit, so occasional live-call failures are expected):

```shell
python tests/test_all_servers.py                 # all servers
python tests/test_all_servers.py chemistry biomart   # a subset
```

## Pull requests

- Branch from `master`; direct pushes to `master` are not allowed.
- CI (`.github/workflows/ci.yml`) must pass: shellcheck, config validation,
  ruff on first-party Python, and a representative-server boot smoke test.
- Keep changes focused. Update `CHANGELOG.md` under **Unreleased** for
  user-facing changes.
- If you change `.mcp.json` / `plugin.json` / `marketplace.json`, make sure they
  still parse and satisfy the config-validation job.

## Reporting bugs and requesting features

Use the issue forms (Bug report / Feature request). For questions and ideas,
prefer Discussions. For security issues, see [SECURITY.md](SECURITY.md) — do not
open a public issue.
