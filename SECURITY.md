# Security Policy

## Supported versions

This project is pre-1.0. Only the latest `0.x` release (and `master`) receives
security fixes.

| Version | Supported |
|---------|-----------|
| latest `0.x` / `master` | ✅ |
| older | ❌ |

## Reporting a vulnerability

**Do not open a public issue for security problems.**

Report privately via GitHub's **"Report a vulnerability"** button under the
repository's **Security** tab (Private Vulnerability Reporting). If that is
unavailable, contact a maintainer directly rather than filing a public issue.

Please include: affected component (launcher, a specific server, or config),
version / commit, reproduction steps, and impact. We aim to acknowledge reports
within a few days.

## Scope notes

- **First-party code**: the launcher (`bin/launch.sh`), tests, and configuration.
  Bootstrapping runs `pip install` from a pinned `requirements.txt` on first use.
- **Vendored code**: the MCP servers under `runtime/lib/` are vendored upstream
  (Claude Science bio-tools). Vulnerabilities rooted in upstream server code or
  in the public databases they query may need to be reported upstream as well;
  we will help triage.

## Credentials — do not leak them

The plugin accepts optional user configuration (NCBI contact email, NCBI API
key). These are secrets you provide locally. **Never paste an API key or other
credential into an issue, PR, log excerpt, or screenshot.** Redact them first.
