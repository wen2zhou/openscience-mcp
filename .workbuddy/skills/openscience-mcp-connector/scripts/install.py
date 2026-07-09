#!/usr/bin/env python3
"""Install openscience-mcp into WorkBuddy — zero repo changes.

This is the engine of the openscience-mcp-connector skill. It reads the Claude
`.mcp.json` template from an UNMODIFIED openscience-mcp clone, resolves the
Claude-specific variables to literal values, and merges the result into
WorkBuddy's `~/.workbuddy/mcp.json`.

Why this needs no changes to the openscience-mcp repo:
  - ${CLAUDE_PLUGIN_ROOT}        -> absolute path to the clone
  - ${user_config.contact_email} -> literal email (or "")
  - ${user_config.ncbi_api_key}   -> literal key (or "")
  - venv placement               -> inject CLAUDE_PLUGIN_DATA into each entry's
                                   env; launch.sh already reads it (with a
                                   repo-local fallback), so pointing it at a
                                   user cache dir keeps the venv out of the repo
                                   without touching launch.sh.

Existing entries in the WorkBuddy config are preserved (same-name servers are
never overwritten). The write is atomic and fail-safe: a malformed existing
config aborts without modification.

Usage:
  install.py --repo <openscience-mcp clone path> \
      [--email <NCBI email>] [--ncbi-key <key>] \
      [--servers chemistry,pubmed,...] \
      [--config <path>] [--data-dir <path>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


def load_mcp_template(plugin_root: Path) -> dict:
    path = plugin_root / ".mcp.json"
    if not path.is_file():
        sys.exit(
            f"ERROR: {path} not found. Is --repo pointing at the openscience-mcp "
            f"clone? Expected <repo>/plugins/openscience/.mcp.json"
        )
    with path.open() as fh:
        data = json.load(fh)
    servers = data.get("mcpServers")
    if not isinstance(servers, dict) or not servers:
        sys.exit(f"ERROR: {path} has no mcpServers object")
    return servers


def launchable_packages(plugin_root: Path) -> set[str]:
    lib = plugin_root / "runtime" / "lib"
    if not lib.is_dir():
        sys.exit(f"ERROR: {lib} not found (not a valid openscience-mcp clone?)")
    return {
        p.name
        for p in lib.iterdir()
        if p.name.startswith("mcp_") and (p / "server.py").is_file()
    }


def substitute(value: str, root: str, email: str, ncbi_key: str) -> str:
    return (
        value.replace("${CLAUDE_PLUGIN_ROOT}", root)
        .replace("${user_config.contact_email}", email)
        .replace("${user_config.ncbi_api_key}", ncbi_key)
    )


def resolve_entry(entry: dict, root: str, email: str, ncbi_key: str, data_dir: str) -> dict:
    out: dict = {}
    command = entry.get("command", "")
    if isinstance(command, str):
        command = substitute(command, root, email, ncbi_key)
    out["command"] = command
    out["args"] = [
        substitute(a, root, email, ncbi_key) if isinstance(a, str) else a
        for a in entry.get("args", [])
    ]
    env = entry.get("env", {}) or {}
    out["env"] = {
        k: (substitute(v, root, email, ncbi_key) if isinstance(v, str) else v)
        for k, v in env.items()
    } if isinstance(env, dict) else {}
    # Place the private venv outside the repo without modifying launch.sh:
    # launch.sh reads CLAUDE_PLUGIN_DATA (with a repo-local fallback).
    if data_dir:
        out["env"]["CLAUDE_PLUGIN_DATA"] = data_dir
    for k, v in entry.items():
        if k not in ("command", "args", "env"):
            out[k] = v
    return out


def entry_pkg(entry: dict) -> str:
    """The mcp package an entry launches. .mcp.json invokes
    `python bootstrap.py <pkg>`, so the package is the last arg."""
    args = entry.get("args") or [""]
    return args[-1]


def build_servers(servers: dict, plugin_root: Path, root: str, email: str,
                  ncbi_key: str, data_dir: str, subset: set[str] | None) -> dict:
    launchable = launchable_packages(plugin_root)
    for name, entry in servers.items():
        pkg = entry_pkg(entry)
        if pkg and pkg not in launchable:
            sys.exit(
                f"ERROR: server '{name}' references package '{pkg}' with no "
                f"server.py under runtime/lib/"
            )
    registered = {entry_pkg(e) for e in servers.values()}
    unregistered = sorted(launchable - registered)
    if unregistered:
        print(
            f"INFO: {len(unregistered)} launchable package(s) not registered in "
            f".mcp.json (skipped): {', '.join(unregistered)}",
            file=sys.stderr,
        )
    out: dict = {}
    for name, entry in servers.items():
        if subset is not None and name not in subset:
            continue
        out[name] = resolve_entry(entry, root, email, ncbi_key, data_dir)
    return out


def load_existing(path: Path) -> dict:
    if not path.exists():
        return {"mcpServers": {}}
    try:
        with path.open() as fh:
            data = json.load(fh)
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: {path} is not valid JSON ({e}); aborting to protect it.")
    if not isinstance(data, dict):
        sys.exit(f"ERROR: {path} top-level is not an object; aborting to protect it.")
    data.setdefault("mcpServers", {})
    if not isinstance(data["mcpServers"], dict):
        sys.exit(f"ERROR: {path} mcpServers is not an object; aborting to protect it.")
    return data


def atomic_merge(cfg_path: Path, new_servers: dict) -> tuple[list[str], list[str]]:
    existing = load_existing(cfg_path)
    added, skipped = [], []
    for name, entry in new_servers.items():
        if name in existing["mcpServers"]:
            skipped.append(name)
        else:
            existing["mcpServers"][name] = entry
            added.append(name)
    d = str(cfg_path.parent)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp", prefix=".openscience-")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(existing, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        with open(tmp) as fh:  # re-validate what we wrote
            json.load(fh)
        os.replace(tmp, str(cfg_path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return added, skipped


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Install openscience-mcp into WorkBuddy (zero repo changes)."
    )
    ap.add_argument("--repo", required=True, help="Path to an openscience-mcp clone.")
    ap.add_argument("--email", default="", help="NCBI contact email (optional).")
    ap.add_argument("--ncbi-key", default="", help="NCBI API key (optional).")
    ap.add_argument("--servers", default="", help="Comma-separated subset (default all).")
    ap.add_argument(
        "--config",
        default=os.path.expanduser("~/.workbuddy/mcp.json"),
        help="WorkBuddy mcp.json path.",
    )
    ap.add_argument(
        "--data-dir",
        default=os.path.expanduser("~/.cache/openscience-mcp"),
        help="Where the private venv lives (injected via CLAUDE_PLUGIN_DATA).",
    )
    args = ap.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        sys.exit(f"ERROR: --repo {repo} is not a directory")
    plugin_root = repo / "plugins" / "openscience"
    if not plugin_root.is_dir():
        sys.exit(f"ERROR: {plugin_root} not found (is --repo the openscience-mcp clone root?)")

    servers = load_mcp_template(plugin_root)

    subset = None
    if args.servers:
        wanted = {s.strip() for s in args.servers.split(",") if s.strip()}
        unknown = sorted(wanted - set(servers))
        if unknown:
            sys.exit(
                f"ERROR: --servers references unknown server(s): {', '.join(unknown)}. "
                f"valid: {', '.join(sorted(servers))}"
            )
        subset = wanted

    new_servers = build_servers(
        servers, plugin_root, str(plugin_root), args.email,
        args.ncbi_key, args.data_dir, subset
    )

    cfg = Path(args.config).expanduser()
    cfg.parent.mkdir(parents=True, exist_ok=True)
    print(f"Merging {len(new_servers)} server(s) into {cfg} ...", file=sys.stderr)
    added, skipped = atomic_merge(cfg, new_servers)
    print(f"  added {len(added)}: {', '.join(added) or '(none)'}", file=sys.stderr)
    if skipped:
        print(
            f"  skipped {len(skipped)} already-present (not overwritten): "
            f"{', '.join(skipped)}",
            file=sys.stderr,
        )
    print(f"  venv will be built at: {args.data_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
