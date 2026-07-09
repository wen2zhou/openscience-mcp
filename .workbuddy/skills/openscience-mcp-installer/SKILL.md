---
name: openscience-mcp-installer
description: Install the openscience-mcp life-sciences MCP server suite into WorkBuddy. This skill should be used when a user wants to use openscience-mcp, install life-sciences / bioinformatics MCP servers, or register the aipoch/openscience-mcp plugin with WorkBuddy. It generates a WorkBuddy-compatible config from the Claude .mcp.json template and merges it into ~/.workbuddy/mcp.json with zero changes to the openscience-mcp repo.
agent_created: true
---

# openscience-mcp-installer

## Overview

This skill installs the [openscience-mcp](https://github.com/aipoch/openscience-mcp)
plugin — 23 life-sciences MCP servers (233 tools) over stdio — into WorkBuddy.
It requires **no modifications to the openscience-mcp repository**: the adapter
logic lives entirely in this skill, which reads the repo's Claude `.mcp.json`
template and rewrites it into WorkBuddy's literal config format.

## When to use

Trigger this skill when a user:

- asks to install / set up / use openscience-mcp in WorkBuddy;
- wants life-sciences or bioinformatics MCP servers (PubChem, Ensembl, UniProt, PDB, AlphaFold, PubMed, ClinVar, gnomAD, GTEx, etc.);
- references the `aipoch/openscience-mcp` plugin and wants it available as WorkBuddy tools.

## Prerequisites

- A local clone of openscience-mcp (or willingness to clone it). The clone
  stays untouched — only its `.mcp.json` is read.
- Python 3 on PATH (stdlib only; the bundled script uses no third-party packages).
- Python >= 3.11 reachable at runtime (launch.sh finds it automatically to
  build the server virtualenv on first tool call).

## Workflow

### 1. Locate or clone the repo

Determine the openscience-mcp clone path. If the user does not have one, clone it:

```shell
git clone https://github.com/aipoch/openscience-mcp.git
```

Record the absolute path; it becomes `--repo` in the next step.

### 2. Gather optional NCBI credentials

Ask (only if relevant to the user's needs; both may be left blank):

- NCBI contact email — required by a few PubMed/dbSNP/ClinVar/GEO tools.
- NCBI API key — raises the NCBI rate limit 3 -> 10 req/s.

For non-interactive use, read them from `OSPC_NCBI_EMAIL` / `OSPC_NCBI_KEY` env
or accept blank.

### 3. Optionally pick a server subset

Installing all 23 servers spawns 23 processes and loads 233 tool schemas into
context. Recommend a subset for most users. Consult
`references/servers.md` for the full catalog and which databases each server
covers, then suggest a relevant subset (e.g. a literature user needs `pubmed`,
`literature`, `biorxiv`; a chemist needs `chemistry`, `chembl`, `zinc`).

### 4. Run the installer script

Execute the bundled engine (it generates the config AND merges into the
WorkBuddy config atomically):

```shell
python3 scripts/install.py \
  --repo <abs path to openscience-mcp clone> \
  --email "<optional email>" \
  --ncbi-key "<optional key>" \
  --servers "<optional comma list>"      # omit for all 23
```

Defaults (overridable): `--config ~/.workbuddy/mcp.json`,
`--data-dir ~/.cache/openscience-mcp`.

The script:
- reads `<repo>/plugins/openscience/.mcp.json` and resolves Claude variables
  (`${CLAUDE_PLUGIN_ROOT}`, `${user_config.*}`) to literal absolute paths/values;
- injects `CLAUDE_PLUGIN_DATA` into each entry's `env` so launch.sh places the
  private venv under `--data-dir` (outside the repo) — this works against an
  unmodified launch.sh, which is why no repo edit is needed;
- merges into `~/.workbuddy/mcp.json`: existing entries are preserved, same-name
  servers are skipped (never overwritten), and a malformed existing config
  aborts without modification.

### 5. Guide the Trust step

After the merge, instruct the user to enable the new servers (required by
WorkBuddy):

1. Open WorkBuddy -> connector management (top-right).
2. For each new `openscience` server entry, click **Trust**.
3. On first tool call, launch.sh builds the venv at the `--data-dir` (one time,
   ~1 min); subsequent starts are instant.

### 6. Confirm

Tell the user how many servers were added vs skipped, where the venv will live,
and that they can now ask natural-language questions like "look up PubChem
properties of aspirin" or "find GWAS associations for height".

## How it works (no repo changes)

The openscience-mcp repo ships `plugins/openscience/.mcp.json` as a Claude Code
template using Claude-specific variable expansion. WorkBuddy does not expand
these variables, so this skill resolves them offline:

| Claude template variable | Resolved to |
|--------------------------|-------------|
| `${CLAUDE_PLUGIN_ROOT}` | absolute path to the clone's `plugins/openscience` |
| `${user_config.contact_email}` | literal email (or empty) |
| `${user_config.ncbi_api_key}` | literal key (or empty) |
| (venv location) | `CLAUDE_PLUGIN_DATA` env var -> `--data-dir` |

The repo's `bin/launch.sh` already reads `CLAUDE_PLUGIN_DATA` (with a repo-local
fallback), so injecting it via the env block places the venv outside the repo
without any edit to launch.sh. This is the key to zero-repo-change support.

## Removing / managing servers

To remove a server, delete its entry from `~/.workbuddy/mcp.json` (the config is
the single source of truth). Re-running the installer is idempotent: already-
present servers are skipped, never overwritten.

## Resources

- `scripts/install.py` — the install engine: config generation + atomic merge.
- `references/servers.md` — full 23-server catalog and database mapping; load
  this to help users choose a `--servers` subset.
