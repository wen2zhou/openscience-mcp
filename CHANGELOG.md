# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Because most of the shipped code is vendored upstream, each release records
three things: the vendored upstream build, any servers added or removed, and
changes to the first-party launcher/tests.

## [Unreleased]

## [0.1.0] - 2026-07-09

### Added

- Initial `openscience` Claude Code plugin: one install registers 23
  life-sciences MCP servers (233 tools) over stdio.
- Self-contained launcher (`bin/launch.sh`): bootstraps a private virtualenv in
  the plugin's data directory and pip-installs pinned dependencies on first run.
  No dependency on a Claude Science installation at runtime.
- Vendored MCP server packages under `plugins/openscience/runtime/lib/`
  (see `runtime/VENDOR_SOURCE.txt` for the upstream build).
- Optional user configuration: NCBI contact email and NCBI API key.
- Integration harness (`tests/test_all_servers.py`) and launcher tests
  (`tests/launch_smoke.sh`).

[Unreleased]: https://github.com/aipoch/openscience-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/aipoch/openscience-mcp/releases/tag/v0.1.0
