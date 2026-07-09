#!/usr/bin/env bash
# launch_smoke.sh — tests for the plugin MCP launcher (bin/launch.sh).
#
# Layered:
#   * Fast unit tests: source launch.sh and exercise its functions + arg
#     validation. No venv / no network.
#   * Integration test: build a real venv in a temp CLAUDE_PLUGIN_DATA, run a
#     full MCP handshake against mcp_chemistry, and assert idempotent stamping.
#     Runs a real `pip install` the first time (network, ~1 min). Skip with
#     SKIP_INTEGRATION=1.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCH="$REPO_ROOT/plugins/openscience/bin/launch.sh"
PASS=0; FAIL=0
ok()   { echo "  ok  - $1"; PASS=$((PASS+1)); }
bad()  { echo "  FAIL- $1"; FAIL=$((FAIL+1)); }

echo "== unit: source launch.sh without running main =="
# shellcheck disable=SC1090
source "$LAUNCH"
# launch.sh sets `set -euo pipefail` for its executed path; neutralize the leak
# so the harness can drive intentionally-failing cases without aborting.
set +e +u +o pipefail
if declare -f ospc_valid_servers >/dev/null; then ok "functions load on source"; else bad "source ran main or missing functions"; fi

echo "== unit: ospc_valid_servers enumerates 24 vendored servers =="
servers="$(ospc_valid_servers)"
n=$(printf '%s\n' "$servers" | grep -c .)
printf '%s\n' "$servers" | grep -qx mcp_chemistry && ok "includes mcp_chemistry" || bad "missing mcp_chemistry"
[ "$n" = "24" ] && ok "exactly 24 servers ($n)" || bad "expected 24, got $n"
printf '%s\n' "$servers" | grep -qx mcp_servers_common && bad "helper leaked as server" || ok "helper pkg excluded"

echo "== unit: ospc_venv_dir honors CLAUDE_PLUGIN_DATA =="
out="$(CLAUDE_PLUGIN_DATA=/tmp/xyz ospc_venv_dir)"
[ "$out" = "/tmp/xyz/venv" ] && ok "venv under CLAUDE_PLUGIN_DATA" || bad "got '$out'"

echo "== unit: invalid server exits 2 with usage, no venv build =="
err="$(CLAUDE_PLUGIN_DATA=/tmp/ospc-should-not-exist-$$ bash "$LAUNCH" not_a_server 2>&1 >/dev/null)"; rc=$?
[ "$rc" = "2" ] && ok "exit code 2" || bad "exit code $rc"
printf '%s' "$err" | grep -qi "valid:" && ok "usage lists valid servers" || bad "no usage text"
[ -d "/tmp/ospc-should-not-exist-$$" ] && bad "built venv for invalid arg" || ok "no venv built for invalid arg"

if [ "${SKIP_INTEGRATION:-0}" = "1" ]; then
  echo "== integration skipped (SKIP_INTEGRATION=1) =="
else
  echo "== integration: real venv + MCP handshake against mcp_chemistry =="
  DATA="$(mktemp -d)"; trap 'rm -rf "$DATA"' EXIT
  req="$REPO_ROOT/plugins/openscience/runtime/requirements.txt"
  handshake='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
  resp="$(printf '%s\n' "$handshake" | perl -e 'alarm 300; exec @ARGV' env CLAUDE_PLUGIN_DATA="$DATA" bash "$LAUNCH" mcp_chemistry 2>"$DATA/err.log")"
  printf '%s' "$resp" | grep -q '"pubchem_search_compounds"' && ok "handshake returned chemistry tools" || { bad "no tools in handshake"; tail -5 "$DATA/err.log"; }
  [ -x "$DATA/venv/bin/python" ] && ok "venv python created" || bad "no venv python"
  # stamp must equal sha256 of requirements.txt
  want="$(shasum -a 256 "$req" | awk '{print $1}')"
  got="$(cat "$DATA/venv/.requirements.sha256" 2>/dev/null)"
  [ "$want" = "$got" ] && ok "stamp matches requirements hash" || bad "stamp '$got' != '$want'"
  # second run is idempotent: stamp file mtime unchanged (no reinstall)
  before="$(stat -f %m "$DATA/venv/.requirements.sha256" 2>/dev/null)"
  printf '%s\n' "$handshake" | perl -e 'alarm 120; exec @ARGV' env CLAUDE_PLUGIN_DATA="$DATA" bash "$LAUNCH" mcp_chemistry >/dev/null 2>&1
  after="$(stat -f %m "$DATA/venv/.requirements.sha256" 2>/dev/null)"
  [ "$before" = "$after" ] && ok "second run did not reinstall (idempotent)" || bad "stamp changed on second run"
fi

echo ""
echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" = "0" ]
