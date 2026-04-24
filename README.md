# nasa-ads-mcp

MCP server for the [NASA ADS](https://ui.adsabs.harvard.edu/) Astrophysics Data System.

## Setup

1. Get an API token: https://ui.adsabs.harvard.edu/user/settings/token
2. `export ADS_API_TOKEN=...`
3. Install: `uv sync` (or `pip install -e .`)

## Run

```bash
# HTTP (default, binds to :8766)
nasa-ads-mcp

# stdio (for local MCP clients like Claude Desktop)
NASA_ADS_MCP_TRANSPORT=stdio nasa-ads-mcp
```

Env vars: `NASA_ADS_MCP_HOST`, `NASA_ADS_MCP_PORT`, `NASA_ADS_MCP_TRANSPORT`, `ADS_API_TOKEN`.

## Tools

| Tool | Purpose |
|------|---------|
| `search` | ADS query syntax — `author:"^einstein" year:1915`, `property:refereed`, etc. |
| `get_paper` / `get_abstract` | Full record / abstract by bibcode |
| `get_references` / `get_citations` | Outbound / inbound citation lists |
| `bigquery` | Batch fetch up to ~2000 bibcodes |
| `metrics` | h-index, reads, tori, i10 for a set |
| `export_bibtex` / `export_refs` | BibTeX (or endnote/ris/aastex/…) |
| `resolve_links` | arXiv, PDF, DOI, data product links |
| `author_network` / `paper_network` | Visualization graphs |

## Prompts

- `lit_review(topic, years)` — themed literature review
- `citation_chase(bibcode, depth)` — walk the citation graph
- `bib_export(query, n, format)` — ADS query → bibliography file
