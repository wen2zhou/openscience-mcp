#!/usr/bin/env bash
# launch.sh — self-contained launcher for a vendored bio-tools MCP server.
#
# Usage: launch.sh <mcp_package>   e.g. launch.sh mcp_chemistry
#
# Wired from .mcp.json as:
#   "command": "${CLAUDE_PLUGIN_ROOT}/bin/launch.sh", "args": ["mcp_chemistry"]
#
# On first run it bootstraps a private virtualenv (in ${CLAUDE_PLUGIN_DATA},
# which survives plugin-cache copies) and pip-installs the pinned deps from
# runtime/requirements.txt. Subsequent runs skip install when the requirements
# hash is unchanged, then exec the stdio MCP server. No dependency on any
# claude-science installation.
set -euo pipefail

# Plugin root: the dir containing bin/ and runtime/. Prefer the env Claude Code
# sets; fall back to this script's parent so tests and manual runs work too.
OSPC_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OSPC_RUNTIME="$OSPC_ROOT/runtime"
OSPC_REQ="$OSPC_RUNTIME/requirements.txt"

# List launchable servers: vendored lib packages that ship a server.py. Derived
# from disk so it stays in lockstep with vendor-sync (mirrors run_server.py).
ospc_valid_servers() {
  local d
  for d in "$OSPC_RUNTIME"/lib/mcp_*; do
    [ -f "$d/server.py" ] && basename "$d"
  done | sort
}

# Where the private venv lives. CLAUDE_PLUGIN_DATA is a stable, writable,
# per-plugin dir that is NOT copied into the plugin cache; fall back to a
# repo-local dir for tests/manual use.
ospc_venv_dir() {
  echo "${CLAUDE_PLUGIN_DATA:-$OSPC_ROOT/.venv-local}/venv"
}

ospc_req_hash() {
  shasum -a 256 "$OSPC_REQ" | awk '{print $1}'
}

# Find a base python3 >= 3.11 on PATH. Prints the interpreter, or fails.
ospc_resolve_python() {
  local cand
  for cand in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
      if "$cand" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,11) else 1)' 2>/dev/null; then
        command -v "$cand"; return 0
      fi
    fi
  done
  return 1
}

# Create the venv and install deps if the requirements hash changed. Idempotent:
# a matching .requirements.sha256 stamp short-circuits the whole thing.
ospc_ensure_venv() {
  local venv stamp want py
  venv="$(ospc_venv_dir)"
  stamp="$venv/.requirements.sha256"
  want="$(ospc_req_hash)"
  if [ -x "$venv/bin/python" ] && [ "$(cat "$stamp" 2>/dev/null || true)" = "$want" ]; then
    return 0
  fi
  py="$(ospc_resolve_python)" || {
    echo "ERROR: need python3 >= 3.11 on PATH to bootstrap the MCP servers." >&2
    exit 1
  }
  echo "[openscience] bootstrapping venv at $venv (first run may take a minute)..." >&2
  mkdir -p "$(dirname "$venv")"
  "$py" -m venv "$venv" >&2
  "$venv/bin/python" -m pip install --quiet --upgrade pip >&2
  "$venv/bin/python" -m pip install --quiet -r "$OSPC_REQ" >&2
  echo "$want" > "$stamp"
}

ospc_main() {
  local server="${1:-}"
  if [ -z "$server" ] || ! ospc_valid_servers | grep -qx "$server"; then
    echo "usage: launch.sh <server package>" >&2
    echo "valid: $(ospc_valid_servers | paste -sd ', ' -)" >&2
    exit 2
  fi
  ospc_ensure_venv
  local venv; venv="$(ospc_venv_dir)"
  exec "$venv/bin/python" "$OSPC_RUNTIME/run_server.py" "$server"
}

# Run main only when executed directly, not when sourced by tests.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  ospc_main "$@"
fi
