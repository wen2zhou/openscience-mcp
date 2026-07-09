#!/usr/bin/env python3
"""bootstrap.py — cross-platform launcher for a vendored bio-tools MCP server.

Usage: bootstrap.py <mcp_package>   e.g. bootstrap.py mcp_chemistry

Wired from .mcp.json as:
  "command": "python",
  "args": ["${CLAUDE_PLUGIN_ROOT}/bin/bootstrap.py", "mcp_chemistry"]

This is the Python port of the original bin/launch.sh: it runs unchanged on
macOS, Linux, and Windows (bash is not available there, and .mcp.json is static
JSON that cannot branch the command per-OS). On first run it bootstraps a
private virtualenv (in ${CLAUDE_PLUGIN_DATA}, which survives plugin-cache
copies) and pip-installs the pinned deps from runtime/requirements.txt.
Subsequent runs skip install when the requirements hash is unchanged, then run
the stdio MCP server. No dependency on any claude-science installation.

All diagnostics go to stderr so the stdio MCP channel (stdout) stays clean.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path


# Plugin root: the dir containing bin/ and runtime/. Prefer the env Claude Code
# sets; fall back to this script's parent so tests and manual runs work too.
ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or Path(__file__).resolve().parent.parent)
RUNTIME = ROOT / "runtime"
REQ = RUNTIME / "requirements.txt"


def valid_servers() -> list[str]:
    """Launchable servers: vendored lib packages that ship a server.py. Derived
    from disk so it stays in lockstep with vendor-sync (mirrors run_server.py)."""
    lib = RUNTIME / "lib"
    return sorted(
        p.name for p in lib.iterdir()
        if p.name.startswith("mcp_") and (p / "server.py").is_file()
    )


def venv_dir() -> Path:
    """Where the private venv lives. CLAUDE_PLUGIN_DATA is a stable, writable,
    per-plugin dir that is NOT copied into the plugin cache; fall back to a
    repo-local dir for tests/manual use."""
    base = os.environ.get("CLAUDE_PLUGIN_DATA") or str(ROOT / ".venv-local")
    return Path(base) / "venv"


def venv_python(venv: Path) -> Path:
    """The venv interpreter path. Windows lays out venvs under Scripts/ with a
    .exe suffix; POSIX uses bin/."""
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def req_hash() -> str:
    return hashlib.sha256(REQ.read_bytes()).hexdigest()


def resolve_python() -> str:
    """Find a base python >= 3.11 on PATH. Returns the interpreter path/name, or
    raises RuntimeError. On Windows also probes the `py` launcher, since the
    versioned pythonX.Y names are absent there."""
    check = "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,11) else 1)"
    candidates: list[list[str]] = [
        [c] for c in ("python3.13", "python3.12", "python3.11", "python3", "python")
    ]
    if os.name == "nt":
        candidates += [["py", f"-3.{m}"] for m in (13, 12, 11)] + [["py"]]
    for cand in candidates:
        try:
            subprocess.run(
                cand + ["-c", check],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
            )
        except (OSError, subprocess.CalledProcessError):
            continue
        return " ".join(cand) if len(cand) > 1 else cand[0]
    raise RuntimeError("need python3 >= 3.11 on PATH to bootstrap the MCP servers.")


def ensure_venv() -> Path:
    """Create the venv and install deps if the requirements hash changed.
    Idempotent: a matching .requirements.sha256 stamp short-circuits."""
    venv = venv_dir()
    py = venv_python(venv)
    stamp = venv / ".requirements.sha256"
    want = req_hash()
    if py.exists() and stamp.exists() and stamp.read_text().strip() == want:
        return venv
    try:
        base = resolve_python().split()
    except RuntimeError as e:
        sys.exit(f"ERROR: {e}")
    print(f"[openscience] bootstrapping venv at {venv} (first run may take a minute)...",
          file=sys.stderr)
    venv.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(base + ["-m", "venv", str(venv)], check=True, stderr=sys.stderr)
    subprocess.run([str(py), "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
                   check=True, stderr=sys.stderr)
    subprocess.run([str(py), "-m", "pip", "install", "--quiet", "-r", str(REQ)],
                   check=True, stderr=sys.stderr)
    stamp.write_text(want)
    return venv


def main() -> None:
    server = sys.argv[1] if len(sys.argv) > 1 else ""
    servers = valid_servers()
    if not server or server not in servers:
        print("usage: bootstrap.py <server package>", file=sys.stderr)
        print(f"valid: {', '.join(servers)}", file=sys.stderr)
        raise SystemExit(2)
    venv = ensure_venv()
    # POSIX exec has no portable Windows equivalent; run as a subprocess and
    # propagate the child's exit code.
    proc = subprocess.run(
        [str(venv_python(venv)), str(RUNTIME / "run_server.py"), server]
    )
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
