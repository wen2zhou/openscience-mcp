#!/usr/bin/env bash
# launch.sh — POSIX wrapper around the cross-platform bin/bootstrap.py.
#
# Usage: launch.sh <mcp_package>   e.g. launch.sh mcp_chemistry
#
# The venv-bootstrap logic now lives in bootstrap.py so it runs unchanged on
# macOS, Linux, and Windows. This wrapper is kept only for backward compatibility
# with any direct POSIX callers; .mcp.json now invokes bootstrap.py via `python`.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find a python3 >= 3.11 on PATH to run the bootstrap.
for cand in python3.13 python3.12 python3.11 python3 python; do
  if command -v "$cand" >/dev/null 2>&1 &&
     "$cand" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,11) else 1)' 2>/dev/null; then
    exec "$cand" "$HERE/bootstrap.py" "$@"
  fi
done

echo "ERROR: need python3 >= 3.11 on PATH to bootstrap the MCP servers." >&2
exit 1
