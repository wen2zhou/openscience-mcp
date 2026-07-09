# openscience-mcp server catalog

The plugin `openscience` registers 23 MCP servers (233 tools total). Each maps
to a public life-sciences database group. All tools are read-only retrieval.

Use this catalog to map a user's data need to the right server name (the value
to pass to `--servers` for subset installs).

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

## NCBI credentials

Two optional values affect NCBI-backed servers (PubMed, dbSNP, ClinVar, GEO):

- **contact email** — NCBI E-utilities ask callers to identify themselves. A few
  tools (e.g. `pubmed` metadata) require it; leave blank to skip those calls.
- **NCBI API key** — raises the rate limit from 3 to 10 requests/second.

Both can be left blank; non-NCBI servers work regardless.

## Process / context cost

Installing all 23 servers launches 23 stdio processes and loads 233 tool
schemas into context. For lighter installs, pass a `--servers` subset — most
users need only a few (e.g. `pubmed,chemistry,variants`).
