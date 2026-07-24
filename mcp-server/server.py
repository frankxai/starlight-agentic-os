#!/usr/bin/env python3
"""starlight-skill-index — an MCP server that makes a large SKILL.md library routable.

This server turns Frank's semantic skill index (the ``index/`` package: a
retriever→reranker over a pgvector store of e5 embeddings, plus a ``catalog.json``
of every skill and a frontmatter security scanner) into a set of tools any
MCP-speaking AI CLI can call — Claude Code, Codex, Gemini, and friends.

Why it exists (the token-economics pitch)
-----------------------------------------
A skill library grows without bound. Naively, a router must read *every* skill's
name+description to decide which one to load — that is O(N) tokens on every turn
and it does not scale past a few dozen skills. This server flips that: the agent
calls ``search_skills(task)`` and gets back only the handful of best-matching
skills. It then loads *one* skill body. The router pays for a short query and a
short ranked list instead of the entire catalog, and only the chosen skill's
body ever enters the context window.

Graceful degradation
---------------------
The best routing uses the vector path (``index/search.py`` over PostgreSQL +
pgvector + e5 embeddings). That requires infrastructure that may not be built
yet. So every search transparently DEGRADES to a pure-stdlib catalog fallback
(TF-IDF cosine over skill name+description+pack, with a keyword-overlap boost).
The fallback needs nothing but ``catalog.json`` and the standard library, so the
server is useful the moment the catalog exists — before any embeddings are built.
Each result reports which ``mode`` produced it, so callers are never misled.

Configuration (all via environment, no secrets in code)
-------------------------------------------------------
* ``STARLIGHT_CATALOG``     — path to ``catalog.json`` (else auto-discovered).
* ``STARLIGHT_INDEX_DIR``   — dir containing ``search.py`` / ``scan_skill_frontmatter.py``
                              (else auto-discovered next to this file).
* ``STARLIGHT_DB_URL`` / ``DATABASE_URL`` — PostgreSQL URL. Its presence is what
                              enables the vector path; without it we go straight
                              to the catalog fallback.
* ``STARLIGHT_SCAN_REPORT`` — path to a cached ``scan_report.json`` from
                              ``scan_skill_frontmatter.py``; if unset the scan is
                              computed live from the catalog.
* ``STARLIGHT_SKILLS_ROOT`` — base dir used to resolve a skill's relative ``path``
                              to an on-disk body when ``body_path`` is absent.

Run
---
    python server.py            # stdio transport (what MCP clients spawn)
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# FastMCP import — support both the official SDK path and the standalone pkg.
# If neither is installed we fall back to a minimal shim so that the pure-Python
# core (search/get_skill/list_packs/security_report) stays importable and
# testable with only the standard library. The shim's .run() explains how to
# install the real SDK; the tool decorator is a transparent pass-through.
# --------------------------------------------------------------------------- #
_MCP_AVAILABLE = True
try:  # official MCP Python SDK
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - fall back to the standalone distribution
    try:
        from fastmcp import FastMCP  # type: ignore
    except ImportError:  # pragma: no cover
        _MCP_AVAILABLE = False

        class FastMCP:  # type: ignore
            """Minimal stand-in used only when the MCP SDK is not installed."""

            def __init__(self, name: str):
                self.name = name

            def tool(self, *dargs, **dkwargs):
                def _decorator(func):
                    return func

                return _decorator

            def run(self, *args, **kwargs):
                raise SystemExit(
                    "The MCP SDK is not installed. Install it with:\n"
                    "    pip install -r requirements.txt\n"
                    "(provides the 'mcp' package with mcp.server.fastmcp.FastMCP).\n"
                    "The core functions are importable without it, but serving over "
                    "MCP requires the SDK."
                )

logging.basicConfig(
    level=os.environ.get("STARLIGHT_LOG_LEVEL", "WARNING"),
    format="%(asctime)s %(levelname)s [starlight] %(message)s",
)
LOG = logging.getLogger("starlight-skill-index")

SERVER_NAME = "starlight-skill-index"
SERVER_VERSION = "0.1.0"
BODY_PREVIEW_CHARS = 1200
_TOKEN_RE = re.compile(r"[a-z0-9]+")


# --------------------------------------------------------------------------- #
# Path / config resolution (cross-platform, env-first, no hardcoded secrets)
# --------------------------------------------------------------------------- #
def _here() -> Path:
    return Path(__file__).resolve().parent


def resolve_index_dir() -> Optional[Path]:
    """Locate the ``index/`` package that holds search.py / scan_skill_frontmatter.py."""
    env = os.environ.get("STARLIGHT_INDEX_DIR")
    if env:
        p = Path(env).expanduser()
        return p if p.exists() else None
    here = _here()
    for cand in (here.parent / "index", here / "index", here.parent):
        if (cand / "search.py").exists() or (cand / "scan_skill_frontmatter.py").exists():
            return cand
    return None


def resolve_catalog_path() -> Optional[Path]:
    """Locate ``catalog.json`` via env override, then a set of sensible defaults."""
    env = os.environ.get("STARLIGHT_CATALOG")
    if env:
        p = Path(env).expanduser()
        return p if p.exists() else None
    here = _here()
    candidates = [
        here.parent / "index" / "catalog.json",
        here / "catalog.json",
        here.parent / "catalog.json",
        Path.cwd() / "catalog.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def db_url() -> Optional[str]:
    """The DB URL whose presence enables the vector path. Never logged in full."""
    return os.environ.get("STARLIGHT_DB_URL") or os.environ.get("DATABASE_URL")


# --------------------------------------------------------------------------- #
# Catalog loading (cached; invalidated by mtime so edits are picked up)
# --------------------------------------------------------------------------- #
def _catalog_signature() -> Tuple[Optional[str], float]:
    p = resolve_catalog_path()
    if not p:
        return (None, 0.0)
    try:
        return (str(p), p.stat().st_mtime)
    except OSError:
        return (str(p), 0.0)


@lru_cache(maxsize=8)
def _load_catalog_cached(path_str: Optional[str], _mtime: float) -> Tuple[Dict[str, Any], ...]:
    if not path_str:
        return tuple()
    try:
        raw = json.loads(Path(path_str).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        LOG.warning("could not read catalog %s: %s", path_str, exc)
        return tuple()
    if not isinstance(raw, list):
        LOG.warning("catalog is not a JSON array: %s", path_str)
        return tuple()
    return tuple(e for e in raw if isinstance(e, dict))


def load_catalog() -> List[Dict[str, Any]]:
    """Return the catalog entries as a list of dicts (empty if unavailable)."""
    path_str, mtime = _catalog_signature()
    return list(_load_catalog_cached(path_str, mtime))


# --------------------------------------------------------------------------- #
# Fallback search: stdlib TF-IDF cosine over name+description+pack, + keyword boost
# --------------------------------------------------------------------------- #
def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _entry_text(entry: Dict[str, Any]) -> str:
    return " ".join(
        str(entry.get(f, "") or "")
        for f in ("name", "description", "pack")
    )


class CatalogSearcher:
    """A pure-stdlib TF-IDF cosine ranker over catalog descriptions.

    This is the graceful-degradation path: it needs only ``catalog.json`` and the
    standard library, so routing works before any embeddings/DB exist. Ranking is
    TF-IDF cosine similarity between the query and each skill's
    ``name + description + pack`` text, blended with the fraction of query terms
    that appear at all (a keyword-overlap boost that helps very short queries).
    """

    def __init__(self, entries: List[Dict[str, Any]]):
        self.entries = entries
        self._doc_tokens: List[Counter] = []
        self._idf: Dict[str, float] = {}
        self._doc_norm: List[float] = []
        self._build()

    def _build(self) -> None:
        n = len(self.entries)
        df: Counter = Counter()
        for entry in self.entries:
            counts = Counter(_tokenize(_entry_text(entry)))
            self._doc_tokens.append(counts)
            for term in counts:
                df[term] += 1
        # Smoothed idf so common terms are down-weighted but never zeroed out.
        self._idf = {t: math.log((n + 1) / (freq + 1)) + 1.0 for t, freq in df.items()}
        for counts in self._doc_tokens:
            norm = math.sqrt(
                sum((tf * self._idf.get(t, 0.0)) ** 2 for t, tf in counts.items())
            )
            self._doc_norm.append(norm or 1.0)

    def search(self, query: str, k: int) -> List[Dict[str, Any]]:
        q_tokens = _tokenize(query)
        if not q_tokens or not self.entries:
            return []
        q_counts = Counter(q_tokens)
        q_weights = {t: tf * self._idf.get(t, math.log(len(self.entries) + 1) + 1.0)
                     for t, tf in q_counts.items()}
        q_norm = math.sqrt(sum(w * w for w in q_weights.values())) or 1.0
        q_unique = set(q_tokens)

        scored: List[Tuple[float, int]] = []
        for i, counts in enumerate(self._doc_tokens):
            dot = 0.0
            for t, qw in q_weights.items():
                tf = counts.get(t)
                if tf:
                    dot += qw * tf * self._idf.get(t, 0.0)
            if dot <= 0.0:
                continue
            cosine = dot / (q_norm * self._doc_norm[i])
            overlap = sum(1 for t in q_unique if counts.get(t)) / len(q_unique)
            # Blend: cosine carries the ranking, overlap rewards literal coverage.
            score = 0.8 * cosine + 0.2 * overlap
            scored.append((score, i))

        scored.sort(key=lambda x: x[0], reverse=True)
        results: List[Dict[str, Any]] = []
        for score, i in scored[:k]:
            e = self.entries[i]
            results.append(
                {
                    "id": e.get("id"),
                    "name": e.get("name"),
                    "pack": e.get("pack"),
                    "score": round(float(score), 6),
                    "description": (str(e.get("description") or "")).strip(),
                    "mode": "catalog-fallback",
                }
            )
        return results


@lru_cache(maxsize=8)
def _searcher_cached(path_str: Optional[str], _mtime: float) -> CatalogSearcher:
    return CatalogSearcher(list(_load_catalog_cached(path_str, _mtime)))


def get_searcher() -> CatalogSearcher:
    path_str, mtime = _catalog_signature()
    return _searcher_cached(path_str, mtime)


# --------------------------------------------------------------------------- #
# Vector path: import index/search.py lazily and only when a DB is configured
# --------------------------------------------------------------------------- #
def _import_index_module(module_name: str):
    """Import a standalone module from the index dir (adds it to sys.path once)."""
    index_dir = resolve_index_dir()
    if not index_dir:
        raise ModuleNotFoundError("index dir not found (set STARLIGHT_INDEX_DIR)")
    idx = str(index_dir)
    if idx not in sys.path:
        sys.path.insert(0, idx)
    return __import__(module_name)


def _vector_search(query: str, k: int) -> List[Dict[str, Any]]:
    """Run the real retriever→reranker. Raises on any unavailability so the caller
    can fall back to the catalog path."""
    search_mod = _import_index_module("search")
    hits = search_mod.search(query, k=k, db_url=db_url())
    results: List[Dict[str, Any]] = []
    for h in hits:
        results.append(
            {
                "id": h.id,
                "name": h.name,
                "pack": h.pack,
                "score": round(float(h.rerank_score), 6),
                "description": (h.description or "").strip(),
                "retriever_score": round(float(h.retriever_score), 6),
                "reranked_by": h.reranked_by,
                "mode": "vector",
            }
        )
    return results


# --------------------------------------------------------------------------- #
# Core operations (plain functions — unit-testable without an MCP client)
# --------------------------------------------------------------------------- #
def run_search_skills(query: str, k: int = 5) -> Dict[str, Any]:
    if not query or not query.strip():
        return {"mode": "error", "error": "query must be a non-empty string", "results": []}
    k = max(1, min(int(k), 50))

    catalog_path = resolve_catalog_path()
    if not catalog_path:
        return {
            "mode": "error",
            "error": "No catalog.json found. Set STARLIGHT_CATALOG or generate it "
            "with index/gen_catalog.py.",
            "results": [],
        }

    # Prefer the vector path when a database is configured; degrade on any failure.
    if db_url():
        try:
            results = _vector_search(query, k)
            return {"mode": "vector", "query": query, "k": k, "results": results}
        except Exception as exc:  # DB down, deps missing, import error, empty store…
            LOG.warning("vector path unavailable (%s); using catalog fallback", exc)
            fallback_reason = f"vector path unavailable: {exc}"
    else:
        fallback_reason = "no database configured (STARLIGHT_DB_URL/DATABASE_URL unset)"

    results = get_searcher().search(query, k)
    return {
        "mode": "catalog-fallback",
        "query": query,
        "k": k,
        "fallback_reason": fallback_reason,
        "results": results,
    }


def _resolve_body_path(entry: Dict[str, Any]) -> Optional[Path]:
    body_path = entry.get("body_path")
    if body_path:
        p = Path(str(body_path))
        if p.exists():
            return p
    rel = entry.get("path")
    if rel:
        root = os.environ.get("STARLIGHT_SKILLS_ROOT")
        bases = []
        if root:
            bases.append(Path(root).expanduser())
        cat = resolve_catalog_path()
        if cat:
            bases.append(cat.parent)
        for base in bases:
            p = base / str(rel)
            if p.exists():
                return p
    return None


def run_get_skill(skill_id: str) -> Dict[str, Any]:
    if not skill_id or not skill_id.strip():
        return {"found": False, "error": "skill_id must be a non-empty string"}
    catalog = load_catalog()
    if not catalog:
        return {"found": False, "error": "catalog unavailable", "skill_id": skill_id}

    entry = next((e for e in catalog if str(e.get("id")) == skill_id), None)
    if entry is None:  # tolerate lookups by name as a convenience
        matches = [e for e in catalog if str(e.get("name")) == skill_id]
        if len(matches) == 1:
            entry = matches[0]
        elif len(matches) > 1:
            return {
                "found": False,
                "skill_id": skill_id,
                "error": f"'{skill_id}' is ambiguous by name; use one of these ids",
                "candidates": [e.get("id") for e in matches],
            }
    if entry is None:
        return {"found": False, "skill_id": skill_id, "error": "no skill with that id"}

    out: Dict[str, Any] = {
        "found": True,
        "id": entry.get("id"),
        "name": entry.get("name"),
        "description": (str(entry.get("description") or "")).strip(),
        "pack": entry.get("pack"),
        "repo": entry.get("repo"),
        "path": entry.get("path"),
        "origin": entry.get("origin"),
        "maturity": entry.get("maturity"),
    }
    body = _resolve_body_path(entry)
    if body is not None:
        out["body_path"] = str(body)
        try:
            text = body.read_text(encoding="utf-8", errors="replace")
            out["body_chars"] = len(text)
            out["body_preview"] = text[:BODY_PREVIEW_CHARS]
            out["body_truncated"] = len(text) > BODY_PREVIEW_CHARS
        except OSError as exc:
            out["body_error"] = f"could not read body: {exc}"
    else:
        out["body_path"] = None
        out["body_note"] = (
            "Body not resolvable on this host. Load it from the skill's 'path' in "
            "the source repo, or set STARLIGHT_SKILLS_ROOT."
        )
    return out


def run_list_packs() -> Dict[str, Any]:
    catalog = load_catalog()
    if not catalog:
        return {"total_skills": 0, "total_packs": 0, "packs": []}
    counts: Counter = Counter()
    unpacked = 0
    for e in catalog:
        pack = e.get("pack")
        if pack:
            counts[str(pack)] += 1
        else:
            unpacked += 1
    packs = [{"pack": p, "skill_count": c} for p, c in counts.most_common()]
    if unpacked:
        packs.append({"pack": None, "skill_count": unpacked})
    return {
        "total_skills": len(catalog),
        "total_packs": len(counts),
        "packs": packs,
    }


def run_security_report() -> Dict[str, Any]:
    # 1) Prefer a cached report produced by scan_skill_frontmatter.py --json.
    cached = os.environ.get("STARLIGHT_SCAN_REPORT")
    if cached:
        p = Path(cached).expanduser()
        if p.exists():
            try:
                report = json.loads(p.read_text(encoding="utf-8"))
                return _summarize_scan(report, source=f"cached-report:{p}")
            except (OSError, json.JSONDecodeError) as exc:
                LOG.warning("could not read cached scan report %s: %s", p, exc)

    # 2) Otherwise, run the scanner live over the catalog (stdlib-only, no DB).
    catalog = load_catalog()
    if not catalog:
        return {"available": False, "error": "catalog unavailable; cannot scan"}
    try:
        scan_mod = _import_index_module("scan_skill_frontmatter")
    except Exception as exc:
        return {
            "available": False,
            "error": f"scan_skill_frontmatter.py not importable: {exc}",
        }
    reports = [scan_mod.scan_skill(e) for e in catalog]
    report = scan_mod.build_report(reports)
    return _summarize_scan(report, source="live-scan")


def _summarize_scan(report: Dict[str, Any], source: str) -> Dict[str, Any]:
    counts = report.get("severity_counts", {}) or {}
    skills = report.get("skills", []) or []
    flagged_ids = [s.get("id") for s in skills]
    high = [s.get("id") for s in skills if s.get("max_severity") == "high"]
    by_severity = {"high": high,
                   "medium": [s.get("id") for s in skills if s.get("max_severity") == "medium"],
                   "low": [s.get("id") for s in skills if s.get("max_severity") == "low"]}
    return {
        "available": True,
        "source": source,
        "scanned": report.get("scanned", 0),
        "flagged": report.get("flagged", len(skills)),
        "severity_counts": {
            "high": counts.get("high", 0),
            "medium": counts.get("medium", 0),
            "low": counts.get("low", 0),
        },
        "flagged_skill_ids": flagged_ids,
        "high_severity_skill_ids": high,
        "flagged_ids_by_severity": by_severity,
        "note": "A skill's routing-visible text (name/description) is an attack "
        "surface — this flags prompt-injection, router-hijack, exfiltration, and "
        "unicode-obfuscation patterns before a skill can influence routing.",
    }


# --------------------------------------------------------------------------- #
# MCP server + tool definitions (docstrings are the agent-facing contract)
# --------------------------------------------------------------------------- #
mcp = FastMCP(SERVER_NAME)


@mcp.tool()
def search_skills(query: str, k: int = 5) -> Dict[str, Any]:
    """Find the most relevant skills for a task — CALL THIS BEFORE grepping or guessing.

    This is the front door to a large, curated skill library. Given a
    natural-language description of what you are trying to do, it returns a short,
    ranked list of the skills most likely to help, so you can load exactly one
    skill body instead of scanning the whole catalog. Prefer this over manually
    reading skill files or searching the repo: it is faster, ranks by meaning
    (not just keywords), and keeps your context window small.

    When to call:
      * The user asks for something and you suspect a specialized skill exists
        ("reconcile QuickBooks vs Stripe", "draft a sell-side teaser",
        "review a contract's risky clauses", "build a merger model").
      * Before writing bespoke code for a task that might already be a skill.
      * To discover capabilities you don't know the exact name of.

    Args:
        query: A natural-language task or intent. Full sentences work best —
            describe the goal, not a single keyword ("turn a spreadsheet into a
            chart" beats "chart").
        k: How many skills to return (1-50, default 5). Use 3-5 to route, more to
            browse.

    Returns:
        A dict with:
          * ``mode`` — "vector" (semantic retriever→reranker over the pgvector
            store) or "catalog-fallback" (stdlib TF-IDF cosine over descriptions
            when no database is built yet). Always check this; fallback is a good
            keyword-aware ranker but not as strong as the vector path.
          * ``results`` — ranked best-first, each: ``{id, name, pack, score,
            description, mode}``. Take ``results[0].id`` and pass it to
            ``get_skill`` to load that skill.
          * ``fallback_reason`` — present only in fallback mode, explaining why.

    Notes:
        ``score`` is comparable within a single response, not across modes. Higher
        is better. An empty ``results`` list means nothing matched — broaden the
        query rather than assuming the capability is missing.
    """
    return run_search_skills(query, k)


@mcp.tool()
def get_skill(skill_id: str) -> Dict[str, Any]:
    """Fetch the full metadata (and a body preview) for one skill by its id.

    Call this after ``search_skills`` to inspect a candidate before committing to
    it: you get the skill's pack, repo, on-disk path, origin, maturity, and — when
    the body is resolvable on this host — its character count and a preview of the
    opening of the skill file. Use the returned ``path`` / ``body_path`` to load
    the complete skill body when you decide to use it (that is the only point at
    which you pay the body's token cost).

    Args:
        skill_id: The exact skill id, e.g. "finance:reconciliation" — normally the
            ``id`` from a ``search_skills`` result. A bare skill name is accepted
            as a convenience when it is unambiguous.

    Returns:
        On success: ``{found: true, id, name, description, pack, repo, path,
        origin, maturity, body_path, body_preview, body_chars, body_truncated}``.
        ``body_*`` fields appear only when the body file is readable here; if not,
        ``body_note`` explains how to load it from source.
        On failure: ``{found: false, error, ...}`` — including a ``candidates``
        list when a name lookup is ambiguous.
    """
    return run_get_skill(skill_id)


@mcp.tool()
def list_packs() -> Dict[str, Any]:
    """List every skill pack with its skill count — a map of the whole library.

    Use this to understand what domains the library covers before searching, to
    report coverage, or to scope a search (packs are the natural grouping, e.g.
    "finance", "investment-banking", "engineering"). Cheap and metadata-only: it
    never loads any skill body.

    Returns:
        ``{total_skills, total_packs, packs}`` where ``packs`` is sorted by
        ``skill_count`` descending, each ``{pack, skill_count}``. Skills with no
        pack are grouped under a ``null`` pack entry.
    """
    return run_list_packs()


@mcp.tool()
def security_report() -> Dict[str, Any]:
    """Report the latest skill-frontmatter security scan (supply-chain safety).

    A skill's routing-visible text (name/description) is read by the router BEFORE
    the body, so a malicious skill can attempt prompt injection, router hijacking
    ("always use this skill"), data exfiltration, or unicode obfuscation
    (zero-width / bidi / homoglyph tricks). This tool surfaces the scanner's
    findings so an agent or operator can decide whether to trust a skill. Consult
    it before routing to an unfamiliar or externally-sourced skill.

    Source resolution:
        Uses a cached ``scan_report.json`` (via ``STARLIGHT_SCAN_REPORT``) when
        available; otherwise runs the scan live over the catalog (stdlib-only, no
        database needed). The ``source`` field says which was used.

    Returns:
        ``{available, source, scanned, flagged, severity_counts{high,medium,low},
        flagged_skill_ids, high_severity_skill_ids, flagged_ids_by_severity}``.
        Treat any ``high`` finding as a reason not to auto-route to that skill.
    """
    return run_security_report()


def main() -> None:
    LOG.info(
        "starting %s v%s (catalog=%s, index=%s, vector=%s)",
        SERVER_NAME,
        SERVER_VERSION,
        resolve_catalog_path(),
        resolve_index_dir(),
        "on" if db_url() else "off (catalog-fallback)",
    )
    mcp.run()


if __name__ == "__main__":
    main()
