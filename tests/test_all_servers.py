#!/usr/bin/env python3
"""test_all_servers.py — integration test harness for the openscience plugin.

For every vendored MCP server it:
  1. launches the server through bin/bootstrap.py (the real plugin path),
  2. performs the MCP handshake (initialize -> initialized -> tools/list),
     enumerating 100% of the server's tools and capturing their schemas,
  3. optionally issues representative live tool calls defined in
     tests/representative_calls.json and records pass/fail.

Artifacts:
  tests/results/<server>.json   per-server tool inventory + call results
  tests/results/SUMMARY.md      human-readable roll-up

All 24 servers share a single bootstrapped venv (CLAUDE_PLUGIN_DATA), so the
pip install happens once. Newline-delimited JSON-RPC over stdio.
"""
from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugins" / "openscience"
BOOTSTRAP = PLUGIN / "bin" / "bootstrap.py"
MCP_JSON = PLUGIN / ".mcp.json"
RESULTS = REPO / "tests" / "results"
CALLS_FILE = REPO / "tests" / "representative_calls.json"
# Shared venv so bootstrap runs once for the whole suite.
DATA_DIR = os.environ.get("OSPC_TEST_DATA", str(REPO / "tests" / ".venv-data"))


def server_roster() -> list[tuple[str, str]]:
    """Return [(friendly_key, pkg)] from .mcp.json."""
    cfg = json.loads(MCP_JSON.read_text())["mcpServers"]
    return [(k, v["args"][-1]) for k, v in cfg.items()]


class MCPClient:
    """Minimal newline-delimited JSON-RPC stdio client for one server."""

    def __init__(self, pkg: str, boot_timeout: float):
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=DATA_DIR)
        self.proc = subprocess.Popen(
            [sys.executable, str(BOOTSTRAP), pkg],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, text=True, bufsize=1,
        )
        self.boot_timeout = boot_timeout

    def _send(self, obj: dict) -> None:
        assert self.proc.stdin
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def _read_id(self, want_id: int, timeout: float) -> dict:
        """Read newline JSON lines until one carries id == want_id."""
        assert self.proc.stdout
        deadline = time.time() + timeout
        while time.time() < deadline:
            r, _, _ = select.select([self.proc.stdout], [], [], deadline - time.time())
            if not r:
                continue
            line = self.proc.stdout.readline()
            if line == "":
                raise EOFError("server closed stdout")
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == want_id:
                return msg
        raise TimeoutError(f"no response id={want_id} within {timeout}s")

    def handshake(self) -> dict:
        self._send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                               "clientInfo": {"name": "harness", "version": "1"}}})
        init = self._read_id(1, self.boot_timeout)
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return init.get("result", {}).get("serverInfo", {})

    def list_tools(self, timeout: float) -> list[dict]:
        self._send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        return self._read_id(2, timeout).get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict, timeout: float) -> dict:
        self._send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                    "params": {"name": name, "arguments": arguments}})
        return self._read_id(3, timeout)

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def run() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    calls = json.loads(CALLS_FILE.read_text()) if CALLS_FILE.exists() else {}
    boot_timeout = float(os.environ.get("OSPC_BOOT_TIMEOUT", "240"))  # first run builds venv
    list_timeout = float(os.environ.get("OSPC_LIST_TIMEOUT", "60"))
    call_timeout = float(os.environ.get("OSPC_CALL_TIMEOUT", "60"))
    only = set(a for a in sys.argv[1:] if not a.startswith("-"))

    summary = []
    total_tools = 0
    for key, pkg in server_roster():
        if only and key not in only and pkg not in only:
            continue
        rec: dict = {"server": key, "pkg": pkg, "booted": False,
                     "serverInfo": {}, "n_tools": 0, "tools": [], "calls": []}
        cli = None
        try:
            cli = MCPClient(pkg, boot_timeout)
            rec["serverInfo"] = cli.handshake()
            rec["booted"] = True
            tools = cli.list_tools(list_timeout)
            rec["n_tools"] = len(tools)
            rec["tools"] = [{"name": t["name"],
                             "description": (t.get("description") or "").split("\n")[0][:120],
                             "schema": t.get("inputSchema", {})} for t in tools]
            total_tools += len(tools)
            boot_timeout = 60  # venv is built after the first server
            for spec in calls.get(key, []):
                res = {"tool": spec["tool"], "arguments": spec.get("arguments", {})}
                try:
                    r = cli.call_tool(spec["tool"], spec.get("arguments", {}), call_timeout)
                    err = r.get("result", {}).get("isError") or ("error" in r)
                    res["ok"] = not err
                    res["preview"] = json.dumps(r.get("result", r))[:200]
                except Exception as e:  # noqa: BLE001
                    res["ok"] = False
                    res["error"] = f"{type(e).__name__}: {e}"
                rec["calls"].append(res)
        except Exception as e:  # noqa: BLE001
            rec["error"] = f"{type(e).__name__}: {e}"
        finally:
            if cli:
                cli.close()
        (RESULTS / f"{key}.json").write_text(json.dumps(rec, indent=2))
        n_live = sum(1 for c in rec["calls"] if c.get("ok"))
        n_call = len(rec["calls"])
        status = "OK" if rec["booted"] else "FAIL"
        summary.append((key, pkg, status, rec["n_tools"], f"{n_live}/{n_call}", rec.get("error", "")))
        print(f"[{status}] {key:24s} tools={rec['n_tools']:<3} live={n_live}/{n_call} {rec.get('error','')}")

    # SUMMARY.md
    booted = sum(1 for s in summary if s[2] == "OK")
    lines = ["# Integration Test Summary", "",
             f"- Servers booted: **{booted}/{len(summary)}**",
             f"- Total tools enumerated: **{total_tools}**",
             f"- Data dir (shared venv): `{DATA_DIR}`", "",
             "| Server | Package | Boot | Tools | Live calls | Error |",
             "|--------|---------|------|-------|-----------|-------|"]
    for key, pkg, status, n, live, err in summary:
        lines.append(f"| {key} | {pkg} | {status} | {n} | {live} | {err} |")
    (RESULTS / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    print(f"\nBooted {booted}/{len(summary)} servers, {total_tools} tools. See {RESULTS}/SUMMARY.md")
    return 0 if booted == len(summary) else 1


if __name__ == "__main__":
    raise SystemExit(run())
