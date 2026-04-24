"""Thin async client for the NASA ADS REST API.

Docs: https://ui.adsabs.harvard.edu/help/api/api-docs.html
All requests need `Authorization: Bearer $ADS_API_TOKEN`.
"""

from __future__ import annotations

import os
from typing import Any, Iterable

import httpx

BASE = "https://api.adsabs.harvard.edu/v1"
DEFAULT_TIMEOUT = 30.0
DEFAULT_FIELDS = (
    "bibcode,title,author,year,pub,abstract,doi,citation_count,read_count,bibstem"
)


class ADSError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, remaining: str | None = None):
        super().__init__(message)
        self.status = status
        self.remaining = remaining


def _token() -> str:
    tok = os.getenv("ADS_API_TOKEN")
    if not tok:
        raise ADSError(
            "ADS_API_TOKEN is not set. Create a token at "
            "https://ui.adsabs.harvard.edu/user/settings/token and export it."
        )
    return tok


def _auth_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    h = {"Authorization": f"Bearer {_token()}"}
    if extra:
        h.update(extra)
    return h


def _check(r: httpx.Response) -> None:
    if r.status_code == 429:
        raise ADSError(
            f"ADS rate limit hit (reset={r.headers.get('X-RateLimit-Reset')})",
            status=429,
            remaining=r.headers.get("X-RateLimit-Remaining"),
        )
    if r.status_code >= 400:
        raise ADSError(
            f"ADS {r.status_code}: {r.text[:300]}",
            status=r.status_code,
            remaining=r.headers.get("X-RateLimit-Remaining"),
        )


def _trim_authors(doc: dict[str, Any], keep: int = 5) -> dict[str, Any]:
    authors = doc.get("author")
    if isinstance(authors, list) and len(authors) > keep:
        doc = {**doc, "author": authors[:keep] + [f"... +{len(authors) - keep} more"]}
    return doc


async def _query(
    client: httpx.AsyncClient,
    q: str,
    fl: str | None,
    rows: int,
    sort: str,
    start: int,
) -> dict[str, Any]:
    params = {
        "q": q,
        "fl": fl or DEFAULT_FIELDS,
        "rows": str(rows),
        "sort": sort,
        "start": str(start),
    }
    r = await client.get(f"{BASE}/search/query", params=params, headers=_auth_headers())
    _check(r)
    return r.json()


async def search(
    q: str,
    *,
    fl: str | None = None,
    rows: int = 10,
    sort: str = "date desc",
    start: int = 0,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        data = await _query(client, q, fl, rows, sort, start)
    resp = data.get("response", {})
    docs = [_trim_authors(d) for d in resp.get("docs", [])]
    return {
        "numFound": resp.get("numFound"),
        "start": resp.get("start"),
        "query": q,
        "docs": docs,
    }


async def get_paper(bibcode: str, *, fl: str | None = None) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        data = await _query(client, f"bibcode:{bibcode}", fl, 1, "date desc", 0)
    docs = data.get("response", {}).get("docs", [])
    return docs[0] if docs else {}


async def get_abstract(bibcode: str) -> dict[str, Any]:
    return await get_paper(
        bibcode, fl="bibcode,title,author,year,pub,abstract,doi,citation_count"
    )


async def get_references(bibcode: str, *, rows: int = 50) -> dict[str, Any]:
    return await search(f"references(bibcode:{bibcode})", rows=rows, sort="date desc")


async def get_citations(bibcode: str, *, rows: int = 50) -> dict[str, Any]:
    return await search(
        f"citations(bibcode:{bibcode})", rows=rows, sort="citation_count desc"
    )


async def bigquery(
    bibcodes: Iterable[str],
    *,
    fl: str | None = None,
    rows: int = 200,
) -> dict[str, Any]:
    body = "bibcode\n" + "\n".join(bibcodes)
    params = {"q": "*:*", "fl": fl or DEFAULT_FIELDS, "rows": str(rows)}
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        r = await client.post(
            f"{BASE}/search/bigquery",
            params=params,
            content=body.encode(),
            headers=_auth_headers({"Content-Type": "big-query/csv"}),
        )
        _check(r)
        data = r.json()
    resp = data.get("response", {})
    return {
        "numFound": resp.get("numFound"),
        "docs": [_trim_authors(d) for d in resp.get("docs", [])],
    }


async def metrics(bibcodes: list[str]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        r = await client.post(
            f"{BASE}/metrics",
            json={"bibcodes": bibcodes},
            headers=_auth_headers({"Content-Type": "application/json"}),
        )
        _check(r)
        return r.json()


async def export_refs(bibcodes: list[str], fmt: str = "bibtex") -> str:
    fmt = fmt.lower()
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        r = await client.post(
            f"{BASE}/export/{fmt}",
            json={"bibcode": bibcodes},
            headers=_auth_headers({"Content-Type": "application/json"}),
        )
        _check(r)
        data = r.json()
    return data.get("export", "")


async def resolve_links(bibcode: str, link_type: str | None = None) -> dict[str, Any]:
    url = f"{BASE}/resolver/{bibcode}"
    if link_type:
        url += f"/{link_type}"
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=False) as client:
        r = await client.get(url, headers=_auth_headers())
        _check(r)
        return r.json()


async def _vis(endpoint: str, bibcodes: list[str]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{BASE}/vis/{endpoint}",
            json={"bibcodes": bibcodes},
            headers=_auth_headers({"Content-Type": "application/json"}),
        )
        _check(r)
        return r.json()


async def author_network(bibcodes: list[str]) -> dict[str, Any]:
    return await _vis("author-network", bibcodes)


async def paper_network(bibcodes: list[str]) -> dict[str, Any]:
    return await _vis("paper-network", bibcodes)
