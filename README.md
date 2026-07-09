# aipoch-openscience-mcp

One-install access to **23 life-sciences MCP servers** — PubChem, ChEMBL, Ensembl, UniProt, PDB,
AlphaFold, GEO, ArrayExpress, gnomAD, ClinVar, GWAS Catalog, GTEx, OpenAlex, PubMed,
ClinicalTrials.gov, and more.

The servers are vendored from Claude Science and **fully self-contained**: the plugin bootstraps
its own Python virtualenv on first run, so **no Claude Science installation is required**.

## What you get

A single plugin, `openscience`, that registers 23 MCP servers (233 tools total). Each server maps
to a public life-sciences database group:

| Server | Sources | Server | Sources |
|--------|---------|--------|---------|
| `chemistry` | PubChem, ChEBI, Rhea, BindingDB | `genomes` | Ensembl (incl. VEP), UCSC |
| `chembl` | ChEMBL | `genes-ontologies` | MyGene, UniProt, GO, Reactome, OLS |
| `zinc` | ZINC | `variants` | gnomAD, ClinVar, dbSNP |
| `pubmed` | PubMed / NCBI E-utilities | `human-genetics` | GWAS Catalog, eQTL, FinnGen |
| `literature` | OpenAlex, arXiv | `clinical-genomics` | ClinGen, CIViC, Open Targets |
| `biorxiv` | bioRxiv | `expression` | GTEx |
| `clinical-trials` | ClinicalTrials.gov | `regulation` | ENCODE, JASPAR, UniBind |
| `drug-regulatory` | openFDA | `protein-annotation` | InterPro, Pfam, HPA, STRING |
| `structures-interactions` | PDB, AlphaFold, EMDB, Complex Portal, IntAct | `rna` | Rfam |
| `omics-archives` | GEO, ArrayExpress, PRIDE, MGnify, MetaboLights | `cancer-models` | cBioPortal |
| `cellguide` | CELLxGENE cell types | `biomart` | BioMart |
| `research-resources` | Grants.gov, Antibody Registry | | |

All tools are read-only retrieval against public databases.

## Requirements

- **Claude Code** (recent version with plugin support).
- **Python ≥ 3.11** on your `PATH` (used once to build the plugin's private virtualenv).
- Network access on first run (to `pip install` the pinned dependencies).

## Install

Installation depends on your agent host. Currently supported:

### Claude Code

```shell
/plugin marketplace add aipoch/openscience-mcp
/plugin install openscience@aipoch-openscience
```

Restart Claude Code when prompted. On the first tool call, the plugin builds its virtualenv and
installs dependencies (about a minute, one time). Subsequent starts are instant.

_More agent frameworks and MCP hosts are on the [roadmap](ROADMAP.md)._

## Configuration (optional)

When you enable the plugin, Claude Code prompts for two optional values:

- **Contact email (NCBI etiquette)** — NCBI E-utilities (PubMed, dbSNP, ClinVar, GEO) ask callers
  to identify themselves. A few tools (e.g. `pubmed` metadata) require it; set this to use them.
- **NCBI API key** — optional, raises the NCBI rate limit from 3 to 10 requests/second.

Both can be left blank; servers that don't need them work regardless.

## Usage

Just describe what you need, or name a source. Examples:

- "Look up the PubChem properties of aspirin." → `chemistry`
- "Find GWAS associations for height." → `human-genetics`
- "Get the AlphaFold structure for UniProt P04637." → `structures-interactions`
- "Search OpenAlex for CRISPR review authors." → `literature`

## Verification

Every server is covered by an integration test harness. The launcher's own unit + integration
tests run standalone:

```shell
bash tests/launch_smoke.sh   # unit + integration tests for the plugin launcher
```

Per-server results — every server booted, all 233 tools enumerated, and a representative live call
per server — come from the integration harness (needs network; upstream databases may rate-limit):

```shell
python tests/test_all_servers.py   # boots each server, enumerates tools, runs representative calls
```

## How it works

- `plugins/openscience/runtime/lib/` — the vendored MCP server packages (Python).
- `plugins/openscience/bin/launch.sh` — bootstraps a private virtualenv in the plugin's data
  directory and launches a server over stdio. No Claude Science dependency.
- `plugins/openscience/.mcp.json` — registers the 23 servers with Claude Code.

## Roadmap

Phase 1 (this release) ships the 23 servers over stdio. Phase 2 introduces a gateway with dynamic
tool discovery to cut process count and context cost. See [ROADMAP.md](ROADMAP.md).

## License

The vendored server code originates from the Claude Science bundled `bio-tools` MCP servers; see
[`plugins/openscience/runtime/VENDOR_SOURCE.txt`](plugins/openscience/runtime/VENDOR_SOURCE.txt)
for provenance. Each upstream database has its own terms of use — review the individual source
licenses for your use case.
