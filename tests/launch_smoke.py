#!/usr/bin/env python3
"""launch_smoke.py — cross-platform tests for the plugin MCP launcher.

Python port of launch_smoke.sh (which used bash-only shasum / stat -f). Runs on
macOS, Linux, and Windows.

Layered:
  * Fast unit tests: import bootstrap.py and exercise its functions + arg
    validation. No venv / no network.
  * Integration test: build a real venv in a temp CLAUDE_PLUGIN_DATA, run a full
    MCP handshake against mcp_chemistry, and assert idempotent stamping. Runs a
    real `pip install` the first time (network, ~1 min). Skip with
    SKIP_INTEGRATION=1.

Usage: python tests/launch_smoke.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN = REPO_ROOT / "plugins" / "openscience" / "bin"
BOOTSTRAP = BIN / "bootstrap.py"
REQ = REPO_ROOT / "plugins" / "openscience" / "runtime" / "requirements.txt"

PASS = 0
FAIL = 0


def ok(msg: str) -> None:
    global PASS
    print(f"  ok  - {msg}")
    PASS += 1


def bad(msg: str) -> None:
    global FAIL
    print(f"  FAIL- {msg}")
    FAIL += 1


def load_bootstrap():
    """Import bootstrap.py as a module without running main()."""
    spec = importlib.util.spec_from_file_location("bootstrap", BOOTSTRAP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    print("== unit: import bootstrap.py without running main ==")
    mod = load_bootstrap()
    if hasattr(mod, "valid_servers") and hasattr(mod, "ensure_venv"):
        ok("functions load on import")
    else:
        bad("missing functions")

    print("== unit: valid_servers enumerates 24 vendored servers ==")
    servers = mod.valid_servers()
    ok("includes mcp_chemistry") if "mcp_chemistry" in servers else bad("missing mcp_chemistry")
    ok(f"exactly 24 servers ({len(servers)})") if len(servers) == 24 else bad(
        f"expected 24, got {len(servers)}")
    bad("helper leaked as server") if "mcp_servers_common" in servers else ok(
        "helper pkg excluded")

    print("== unit: venv_dir honors CLAUDE_PLUGIN_DATA ==")
    prev = os.environ.get("CLAUDE_PLUGIN_DATA")
    os.environ["CLAUDE_PLUGIN_DATA"] = os.path.join(tempfile.gettempdir(), "xyz")
    got = mod.venv_dir()
    expected = Path(tempfile.gettempdir()) / "xyz" / "venv"
    ok("venv under CLAUDE_PLUGIN_DATA") if got == expected else bad(f"got '{got}'")
    if prev is None:
        del os.environ["CLAUDE_PLUGIN_DATA"]
    else:
        os.environ["CLAUDE_PLUGIN_DATA"] = prev

    print("== unit: invalid server exits 2 with usage, no venv build ==")
    nodir = Path(tempfile.gettempdir()) / f"ospc-should-not-exist-{os.getpid()}"
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(nodir)}
    proc = subprocess.run(
        [sys.executable, str(BOOTSTRAP), "not_a_server"],
        capture_output=True, text=True, env=env,
    )
    ok("exit code 2") if proc.returncode == 2 else bad(f"exit code {proc.returncode}")
    ok("usage lists valid servers") if "valid:" in proc.stderr.lower() else bad("no usage text")
    bad("built venv for invalid arg") if nodir.exists() else ok("no venv built for invalid arg")

    if os.environ.get("SKIP_INTEGRATION") == "1":
        print("== integration skipped (SKIP_INTEGRATION=1) ==")
    else:
        print("== integration: real venv + MCP handshake against mcp_chemistry ==")
        with tempfile.TemporaryDirectory() as data:
            data_p = Path(data)
            env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(data_p)}
            handshake = (
                '{"jsonrpc":"2.0","id":1,"method":"initialize","params":'
                '{"protocolVersion":"2024-11-05","capabilities":{},'
                '"clientInfo":{"name":"t","version":"1"}}}\n'
                '{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
                '{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n'
            )
            try:
                proc = subprocess.run(
                    [sys.executable, str(BOOTSTRAP), "mcp_chemistry"],
                    input=handshake, capture_output=True, text=True,
                    env=env, timeout=300,
                )
                resp = proc.stdout
            except subprocess.TimeoutExpired as e:
                resp = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            ok("handshake returned chemistry tools") if "pubchem_search_compounds" in resp else bad(
                "no tools in handshake")

            venv_py = mod.venv_python(data_p / "venv")
            ok("venv python created") if venv_py.exists() else bad("no venv python")

            stamp = data_p / "venv" / ".requirements.sha256"
            want = hashlib.sha256(REQ.read_bytes()).hexdigest()
            got = stamp.read_text().strip() if stamp.exists() else ""
            ok("stamp matches requirements hash") if got == want else bad(
                f"stamp '{got}' != '{want}'")

            before = stamp.stat().st_mtime if stamp.exists() else 0
            subprocess.run(
                [sys.executable, str(BOOTSTRAP), "mcp_chemistry"],
                input=handshake, capture_output=True, text=True,
                env=env, timeout=120,
            )
            after = stamp.stat().st_mtime if stamp.exists() else 0
            ok("second run did not reinstall (idempotent)") if before == after else bad(
                "stamp changed on second run")

    print()
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
