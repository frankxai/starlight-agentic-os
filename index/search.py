#!/usr/bin/env python3
"""search.py — Starlight Agentic OS, Phase D.

Two-stage semantic retriever for the skill index. This is the entry point an
agent/router calls to pick which SKILL.md to load, instead of stuffing every
skill's name+description into the prompt.

Pipeline
--------
1. Embed the query locally with ``intfloat/multilingual-e5-base`` using the
   required e5 ``"query: "`` prefix.
2. **Retrieve** the top-N candidates from pgvector via the HNSW cosine index.
3. **Rerank** those candidates over their FULL skill bodies:
     * If a cross-encoder is available, score (query, body) pairs with it.
     * Otherwise fall back to the cosine similarity already returned by stage 2.
4. Return the top-k skills with scores.

Usage
-----
    # human-readable
    python search.py "convert a spreadsheet to a chart" -k 5

    # machine-readable (what a router consumes)
    python search.py "reconcile quickbooks vs stripe" -k 5 --json

Exit code is 0 on success, 2 when no candidates are found.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from typing import List, Optional, Sequence

logging.basicConfig(
    level=os.environ.get("STARLIGHT_LOG_LEVEL", "WARNING"),
    format="%(asctime)s %(levelname)s %(message)s",
)
LOG = logging.getLogger("search")

EMBED_MODEL_NAME = "intfloat/multilingual-e5-base"
CROSS_ENCODER_NAME = os.environ.get(
    "STARLIGHT_CROSS_ENCODER", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
QUERY_PREFIX = "query: "
DEFAULT_CANDIDATES = 30
DEFAULT_K = 5


# --------------------------------------------------------------------------- #
# Result type
# --------------------------------------------------------------------------- #
@dataclass
class SkillHit:
    """A ranked search result."""

    id: str
    name: str
    description: str
    pack: Optional[str]
    repo: Optional[str]
    path: Optional[str]
    origin: Optional[str]
    maturity: Optional[str]
    retriever_score: float  # cosine similarity in [-1, 1], higher = closer
    rerank_score: float  # cross-encoder logit or cosine fallback
    reranked_by: str  # "cross-encoder" | "cosine"


# --------------------------------------------------------------------------- #
# Lazy singletons (models are expensive to load)
# --------------------------------------------------------------------------- #
_QUERY_MODEL = None
_CROSS_ENCODER = "unset"  # sentinel; None means "tried and unavailable"


def _query_embedder():
    global _QUERY_MODEL
    if _QUERY_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover
            raise SystemExit(
                "sentence-transformers is required. "
                "pip install -r index/requirements.txt"
            ) from exc
        LOG.info("loading query embedder %s", EMBED_MODEL_NAME)
        _QUERY_MODEL = SentenceTransformer(EMBED_MODEL_NAME)
    return _QUERY_MODEL


def _cross_encoder():
    """Return a CrossEncoder, or None if it cannot be loaded (graceful fallback)."""
    global _CROSS_ENCODER
    if _CROSS_ENCODER == "unset":
        try:
            from sentence_transformers import CrossEncoder

            LOG.info("loading cross-encoder %s", CROSS_ENCODER_NAME)
            _CROSS_ENCODER = CrossEncoder(CROSS_ENCODER_NAME)
        except Exception as exc:  # ImportError or model download failure
            LOG.warning("cross-encoder unavailable (%s); using cosine fallback", exc)
            _CROSS_ENCODER = None
    return _CROSS_ENCODER


def embed_query(query: str) -> list:
    """Embed a query with the e5 ``query:`` prefix, L2-normalized."""
    model = _query_embedder()
    vec = model.encode(
        QUERY_PREFIX + query.strip(),
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return vec.astype("float32")


# --------------------------------------------------------------------------- #
# Database access
# --------------------------------------------------------------------------- #
def resolve_db_url(cli_url: Optional[str]) -> Optional[str]:
    return cli_url or os.environ.get("STARLIGHT_DB_URL") or os.environ.get("DATABASE_URL")


def connect(db_url: Optional[str]):
    try:
        import psycopg
        from pgvector.psycopg import register_vector
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "psycopg[binary] and pgvector are required. "
            "pip install -r index/requirements.txt"
        ) from exc
    conn = psycopg.connect(db_url) if db_url else psycopg.connect()
    register_vector(conn)
    return conn


_RETRIEVE_SQL = """
SELECT id, name, description, pack, repo, path, origin, maturity, body,
       1 - (embedding <=> %(qvec)s) AS cosine_sim
FROM skills
{where}
ORDER BY embedding <=> %(qvec)s
LIMIT %(limit)s
"""


def _retrieve(
    conn,
    qvec,
    candidates: int,
    pack: Optional[str],
    maturity: Optional[str],
) -> List[dict]:
    """Stage 1: ANN retrieval of ``candidates`` nearest skills (with metadata filter)."""
    filters = []
    params = {"qvec": qvec, "limit": candidates}
    if pack:
        filters.append("pack = %(pack)s")
        params["pack"] = pack
    if maturity:
        filters.append("maturity = %(maturity)s")
        params["maturity"] = maturity
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = _RETRIEVE_SQL.format(where=where)

    # Ask HNSW for good recall on the candidate set.
    with conn.cursor() as cur:
        cur.execute("SET LOCAL hnsw.ef_search = %s", (max(candidates * 2, 40),))
        cur.execute(sql, params)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


# --------------------------------------------------------------------------- #
# Rerank
# --------------------------------------------------------------------------- #
def _rerank(query: str, rows: List[dict], k: int) -> List[SkillHit]:
    """Stage 2: rerank candidates over full bodies; return top-k SkillHits."""
    ce = _cross_encoder()
    if ce is not None and rows:
        pairs = [(query, r["body"] or f"{r['name']}. {r['description']}") for r in rows]
        scores = ce.predict(pairs, show_progress_bar=False)
        reranked_by = "cross-encoder"
        for r, s in zip(rows, scores):
            r["_rerank"] = float(s)
    else:
        reranked_by = "cosine"
        for r in rows:
            r["_rerank"] = float(r["cosine_sim"])

    rows_sorted = sorted(rows, key=lambda r: r["_rerank"], reverse=True)[:k]
    return [
        SkillHit(
            id=r["id"],
            name=r["name"],
            description=r["description"],
            pack=r["pack"],
            repo=r["repo"],
            path=r["path"],
            origin=r["origin"],
            maturity=r["maturity"],
            retriever_score=round(float(r["cosine_sim"]), 6),
            rerank_score=round(float(r["_rerank"]), 6),
            reranked_by=reranked_by,
        )
        for r in rows_sorted
    ]


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def search(
    query: str,
    k: int = DEFAULT_K,
    *,
    db_url: Optional[str] = None,
    candidates: int = DEFAULT_CANDIDATES,
    pack: Optional[str] = None,
    maturity: Optional[str] = None,
) -> List[SkillHit]:
    """Retrieve → rerank and return the top-``k`` skills for ``query``.

    This is the function a router should import and call:

        from search import search
        hits = search("draft a teaser for a sell-side deal", k=3)
        chosen = hits[0].id if hits else None
    """
    if not query or not query.strip():
        raise ValueError("query must be non-empty")
    candidates = max(candidates, k)
    qvec = embed_query(query)
    conn = connect(resolve_db_url(db_url))
    try:
        rows = _retrieve(conn, qvec, candidates, pack, maturity)
    finally:
        conn.close()
    if not rows:
        return []
    return _rerank(query, rows, k)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _print_human(query: str, hits: Sequence[SkillHit]) -> None:
    if not hits:
        print(f'No skills matched "{query}".')
        return
    print(f'Top {len(hits)} skills for "{query}"  (rerank: {hits[0].reranked_by})\n')
    for i, h in enumerate(hits, 1):
        meta = " · ".join(x for x in (h.pack, h.maturity, h.origin) if x)
        print(f"{i}. {h.name}  [{h.id}]")
        if meta:
            print(f"   {meta}")
        if h.description:
            print(f"   {h.description.strip()[:200]}")
        print(
            f"   rerank={h.rerank_score:.4f}  retriever_cos={h.retriever_score:.4f}"
        )
        if h.path:
            print(f"   -> {h.path}")
        print()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Semantic skill retriever (retrieve→rerank).")
    p.add_argument("query", help="Natural-language task / routing query.")
    p.add_argument("-k", type=int, default=DEFAULT_K, help="Number of skills to return.")
    p.add_argument(
        "--candidates",
        type=int,
        default=DEFAULT_CANDIDATES,
        help="ANN candidate pool size before reranking.",
    )
    p.add_argument("--pack", default=None, help="Restrict to a skill pack.")
    p.add_argument("--maturity", default=None, help="Restrict to a maturity level.")
    p.add_argument("--db-url", default=None, help="PostgreSQL URL (else env).")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        hits = search(
            args.query,
            k=args.k,
            db_url=args.db_url,
            candidates=args.candidates,
            pack=args.pack,
            maturity=args.maturity,
        )
    except Exception as exc:
        LOG.error("search failed: %s", exc)
        if args.json:
            print(json.dumps({"query": args.query, "error": str(exc), "results": []}))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {"query": args.query, "k": args.k, "results": [asdict(h) for h in hits]},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        _print_human(args.query, hits)

    return 0 if hits else 2


if __name__ == "__main__":
    sys.exit(main())
