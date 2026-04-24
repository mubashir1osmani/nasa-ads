"""NASA ADS MCP server.

Wraps the ADS REST API (search, citations, references, exports, metrics,
resolver, visualizations) as MCP tools.
"""

from __future__ import annotations

import json
import os
from urllib.parse import unquote

from mcp.server.fastmcp import FastMCP

from . import client as ads

_HOST = os.getenv("NASA_ADS_MCP_HOST", "0.0.0.0")
_PORT = int(os.getenv("NASA_ADS_MCP_PORT", "8766"))

mcp = FastMCP("nasa-ads", host=_HOST, port=_PORT)


def _j(obj) -> str:
    return json.dumps(obj, indent=2, default=str)


@mcp.tool()
async def search(
    q: str,
    fl: str | None = None,
    rows: int = 10,
    sort: str = "date desc",
    start: int = 0,
) -> str:
    """Search NASA ADS with the full ADS query syntax.

    Examples:
      - `author:"^einstein" year:1915`
      - `title:"dark matter" property:refereed year:2020-2024`
      - `full:"gravitational waves" database:astronomy`

    Args:
        q: ADS query string.
        fl: Comma-separated fields to return. Default: bibcode,title,author,year,pub,abstract,doi,citation_count,read_count,bibstem.
        rows: Max results (default 10, max 2000).
        sort: ADS sort expr, e.g. `date desc`, `citation_count desc`, `score desc`.
        start: Offset for pagination.
    """
    return _j(await ads.search(q, fl=fl, rows=rows, sort=sort, start=start))


@mcp.tool()
async def get_paper(bibcode: str, fl: str | None = None) -> str:
    """Full record for a single paper by bibcode (e.g. `1974Natur.248...30H`)."""
    return _j(await ads.get_paper(bibcode, fl=fl))


@mcp.tool()
async def get_abstract(bibcode: str) -> str:
    """Abstract + basic metadata for a paper by bibcode."""
    return _j(await ads.get_abstract(bibcode))


@mcp.tool()
async def get_references(bibcode: str, rows: int = 50) -> str:
    """Papers cited BY the given bibcode (its reference list)."""
    return _j(await ads.get_references(bibcode, rows=rows))


@mcp.tool()
async def get_citations(bibcode: str, rows: int = 50) -> str:
    """Papers that cite the given bibcode, sorted by citation count."""
    return _j(await ads.get_citations(bibcode, rows=rows))


@mcp.tool()
async def bigquery(bibcodes: list[str], fl: str | None = None, rows: int = 200) -> str:
    """Batch-fetch records for up to ~2000 bibcodes in one call."""
    return _j(await ads.bigquery(bibcodes, fl=fl, rows=rows))


@mcp.tool()
async def metrics(bibcodes: list[str]) -> str:
    """Citation metrics (h-index, reads, tori, i10, etc.) for a set of bibcodes."""
    return _j(await ads.metrics(bibcodes))


@mcp.tool()
async def export_bibtex(bibcodes: list[str]) -> str:
    """BibTeX for the given bibcodes. Returns raw BibTeX string."""
    return await ads.export_refs(bibcodes, "bibtex")


@mcp.tool()
async def export_refs(bibcodes: list[str], format: str = "bibtex") -> str:
    """Export citations in an arbitrary ADS format.

    Common formats: `bibtex`, `bibtexabs`, `ads`, `endnote`, `ris`, `aastex`,
    `icarus`, `mnras`, `soph`, `dcxml`, `refxml`, `refabsxml`, `rss`.
    """
    return await ads.export_refs(bibcodes, format)


@mcp.tool()
async def resolve_links(bibcode: str, link_type: str | None = None) -> str:
    """Resolver links for a bibcode (arxiv, PDF, DOI, data products, etc.).

    If `link_type` is given (e.g. `esource`, `eprint_html`, `data`,
    `associated`), returns only that subset.
    """
    return _j(await ads.resolve_links(bibcode, link_type))


@mcp.tool()
async def author_network(bibcodes: list[str]) -> str:
    """Coauthor network graph for a set of bibcodes."""
    return _j(await ads.author_network(bibcodes))


@mcp.tool()
async def paper_network(bibcodes: list[str]) -> str:
    """Citation/reference network graph for a set of bibcodes."""
    return _j(await ads.paper_network(bibcodes))


# ---------- Resources ----------

@mcp.resource("ads://query/{encoded_q}")
async def query_resource(encoded_q: str) -> str:
    """Attach a saved ADS query as a resource. URL-encode the ADS query string."""
    q = unquote(encoded_q)
    return _j(await ads.search(q, rows=25))


# ---------- Prompts ----------

@mcp.prompt()
def lit_review(topic: str, years: str = "2015-") -> str:
    """Draft a literature review on a topic using ADS."""
    return (
        f"Run a NASA ADS literature review on '{topic}' restricted to year:{years}.\n"
        "  1. `search` with a focused query — include `property:refereed` and sort by "
        "`citation_count desc`. Ask for rows=25.\n"
        "  2. Pick the top ~10 bibcodes and pass them to `bigquery` to pull abstracts.\n"
        "  3. Cluster the results by theme. For each cluster, cite 2-3 bibcodes and "
        "summarize what they collectively established.\n"
        "  4. End with open problems — papers from the last 2 years whose abstracts "
        "explicitly flag unresolved questions."
    )


@mcp.prompt()
def citation_chase(bibcode: str, depth: int = 1) -> str:
    """Walk the citation graph outward from a seed paper."""
    return (
        f"Starting from {bibcode}, chase the citation graph to depth {depth}.\n"
        "  1. `get_abstract` the seed so we know what it's about.\n"
        "  2. `get_references` (what it builds on) and `get_citations` "
        "(what built on it), sorted by citation_count.\n"
        "  3. Keep the top 5 of each that look thematically closest — briefly "
        "justify each pick.\n"
        f"  4. If depth > 1, recurse on each kept bibcode up to depth {depth}.\n"
        "  5. Report a small bulleted tree with bibcode, 1-line summary, and why "
        "it matters for the seed paper."
    )


@mcp.prompt()
def bib_export(query: str, n: int = 10, format: str = "bibtex") -> str:
    """Turn an ADS query into a bibliography file."""
    return (
        f"Search ADS for '{query}', take the top {n} refereed results sorted by "
        f"citation_count, then call `export_refs` with format='{format}' on those "
        "bibcodes. Return the exported string verbatim in a fenced block so I "
        "can paste it into my .bib file."
    )


def main() -> None:
    transport = os.getenv("NASA_ADS_MCP_TRANSPORT", "streamable-http")
    if transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()
