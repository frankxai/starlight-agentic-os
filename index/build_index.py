#!/usr/bin/env python3
"""build_index.py — Starlight Agentic OS, Phase D.

Read a ``catalog.json`` of agent-skills, compute local
``intfloat/multilingual-e5-base`` (768-dim) embeddings over each skill's FULL
body, and upsert them into a PostgreSQL + pgvector ``skills`` table.

Key properties
--------------
* **Local only** — embeddings run through ``sentence-transformers`` on this
  machine. No cloud API is called.
* **e5 prefixes** — passage text is embedded with the required ``"passage: "``
  prefix (queries use ``"query: "``; see ``search.py``).
* **Incremental / idempotent** — each row is keyed by a ``content_hash`` over
  ``(name + description + body)``. Re-running the build skips any skill whose
  hash is unchanged, so embeddings are only recomputed when content changes.
* **Over-length bodies** — a body longer than the model's window is split into
  overlapping chunks; each chunk is embedded and the (normalized) chunk vectors
  are **mean-pooled** and re-normalized. Mean-pooling is preferred over hard
  truncation so that signal from the whole skill body survives (routing quality
  depends on the full body, not just its head).

Usage
-----
    python build_index.py --catalog catalog.json \
        --db-url postgresql://user@host:5432/starlight_skills

DB credentials: prefer the ``--db-url`` value; otherwise fall back to the
``STARLIGHT_DB_URL`` env var, otherwise standard libpq ``PG*`` env vars
(``PGHOST``, ``PGUSER``, ``PGPASSWORD``, ``PGDATABASE``, ``PGPORT``). No secret
is ever hardcoded or logged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

logging.basicConfig(
    level=os.environ.get("STARLIGHT_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
LOG = logging.getLogger("build_index")

EMBED_MODEL_NAME = "intfloat/multilingual-e5-base"
EMBED_DIM = 768
# e5-base has a 512-token window. We chunk on characters as a cheap, deterministic
# proxy (~4 chars/token) with overlap to preserve cross-boundary context.
CHUNK_CHARS = 1600
CHUNK_OVERLAP = 200
PASSAGE_PREFIX = "passage: "


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Skill:
    """A single catalog entry, with its resolved body text."""

    id: str
    name: str
    description: str
    pack: Optional[str]
    repo: Optional[str]
    path: Optional[str]
    origin: Optional[str]
    maturity: Optional[str]
    body: str

    def content_hash(self) -> str:
        """Deterministic hash over the semantically-relevant content."""
        h = hashlib.sha256()
        for part in (self.name, self.description, self.body):
            h.update((part or "").encode("utf-8"))
            h.update(b"\x00")
        return h.hexdigest()


# --------------------------------------------------------------------------- #
# Catalog loading
# --------------------------------------------------------------------------- #
def _resolve_body(entry: dict, catalog_dir: Path) -> str:
    """Return the body text for a catalog entry.

    Supports either an inline ``body`` field or a ``body_path`` (resolved
    relative to the catalog file's directory when not absolute).
    """
    if entry.get("body"):
        return str(entry["body"])
    body_path = entry.get("body_path") or entry.get("path")
    if not body_path:
        return ""
    p = Path(body_path)
    if not p.is_absolute():
        p = (catalog_dir / p).resolve()
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        LOG.warning("could not read body for %s at %s: %s", entry.get("id"), p, exc)
        return ""


def load_catalog(catalog_path: Path) -> List[Skill]:
    """Parse ``catalog.json`` into a deterministic, sorted list of ``Skill``."""
    if not catalog_path.is_file():
        raise FileNotFoundError(f"catalog not found: {catalog_path}")
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("catalog.json must be a JSON array of skill objects")

    catalog_dir = catalog_path.parent
    skills: List[Skill] = []
    seen: set[str] = set()
    for entry in raw:
        if not isinstance(entry, dict) or not entry.get("id"):
            LOG.warning("skipping malformed catalog entry: %r", entry)
            continue
        sid = str(entry["id"])
        if sid in seen:
            LOG.warning("duplicate id %s — skipping later occurrence", sid)
            continue
        seen.add(sid)
        skills.append(
            Skill(
                id=sid,
                name=str(entry.get("name") or sid),
                description=str(entry.get("description") or ""),
                pack=_opt(entry.get("pack")),
                repo=_opt(entry.get("repo")),
                path=_opt(entry.get("path")),
                origin=_opt(entry.get("origin")),
                maturity=_opt(entry.get("maturity")),
                body=_resolve_body(entry, catalog_dir),
            )
        )
    skills.sort(key=lambda s: s.id)  # determinism
    return skills


def _opt(value: object) -> Optional[str]:
    return None if value is None else str(value)


# --------------------------------------------------------------------------- #
# Chunking + embedding
# --------------------------------------------------------------------------- #
def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split ``text`` into overlapping character windows (deterministic)."""
    text = text.strip()
    if not text:
        return [""]
    if len(text) <= size:
        return [text]
    step = max(1, size - overlap)
    return [text[i : i + size] for i in range(0, len(text), step)]


class Embedder:
    """Thin wrapper around the local e5 SentenceTransformer model."""

    def __init__(self, model_name: str = EMBED_MODEL_NAME) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - env guard
            raise SystemExit(
                "sentence-transformers is required. Install with: "
                "pip install -r index/requirements.txt"
            ) from exc
        LOG.info("loading embedding model %s (local)...", model_name)
        self._model = SentenceTransformer(model_name)

    def embed_passages(self, bodies: Sequence[str]) -> "list":
        """Return one L2-normalized 768-dim vector per body.

        Long bodies are chunked, each chunk embedded with the e5 ``passage: ``
        prefix, and the chunk vectors mean-pooled then re-normalized.
        """
        import numpy as np

        # Flatten all chunks into a single batch for efficiency, remembering
        # which chunks belong to which body.
        all_chunks: List[str] = []
        spans: List[tuple[int, int]] = []
        for body in bodies:
            chunks = chunk_text(body)
            start = len(all_chunks)
            all_chunks.extend(PASSAGE_PREFIX + c for c in chunks)
            spans.append((start, len(all_chunks)))

        matrix = self._model.encode(
            all_chunks,
            batch_size=32,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        out = []
        for start, end in spans:
            pooled = matrix[start:end].mean(axis=0)
            norm = np.linalg.norm(pooled)
            if norm > 0:
                pooled = pooled / norm
            out.append(pooled.astype(np.float32))
        return out


# --------------------------------------------------------------------------- #
# Database access
# --------------------------------------------------------------------------- #
def resolve_db_url(cli_url: Optional[str]) -> Optional[str]:
    """Precedence: --db-url > STARLIGHT_DB_URL > DATABASE_URL > libpq PG* env."""
    return cli_url or os.environ.get("STARLIGHT_DB_URL") or os.environ.get("DATABASE_URL")


def connect(db_url: Optional[str]):
    """Open a psycopg (v3) connection with the pgvector type registered."""
    try:
        import psycopg
        from pgvector.psycopg import register_vector
    except ImportError as exc:  # pragma: no cover - env guard
        raise SystemExit(
            "psycopg[binary] and pgvector are required. Install with: "
            "pip install -r index/requirements.txt"
        ) from exc

    # If db_url is None, psycopg reads standard PG* env vars.
    conn = psycopg.connect(db_url) if db_url else psycopg.connect()
    conn.autocommit = False
    register_vector(conn)
    return conn


def existing_hashes(conn) -> dict:
    """Return ``{id: content_hash}`` for all currently-indexed skills."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, content_hash FROM skills")
        return {row[0]: row[1] for row in cur.fetchall()}


UPSERT_SQL = """
INSERT INTO skills
    (id, name, description, pack, repo, path, origin, maturity,
     content_hash, body, embedding, indexed_at)
VALUES
    (%(id)s, %(name)s, %(description)s, %(pack)s, %(repo)s, %(path)s,
     %(origin)s, %(maturity)s, %(content_hash)s, %(body)s, %(embedding)s, now())
ON CONFLICT (id) DO UPDATE SET
    name         = EXCLUDED.name,
    description  = EXCLUDED.description,
    pack         = EXCLUDED.pack,
    repo         = EXCLUDED.repo,
    path         = EXCLUDED.path,
    origin       = EXCLUDED.origin,
    maturity     = EXCLUDED.maturity,
    content_hash = EXCLUDED.content_hash,
    body         = EXCLUDED.body,
    embedding    = EXCLUDED.embedding,
    indexed_at   = now()
"""


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def build(
    catalog_path: Path,
    db_url: Optional[str],
    prune: bool = False,
) -> int:
    """Run the incremental build. Returns process exit code."""
    skills = load_catalog(catalog_path)
    LOG.info("loaded %d skills from %s", len(skills), catalog_path)
    if not skills:
        LOG.warning("catalog is empty; nothing to do")
        return 0

    conn = connect(db_url)
    try:
        prior = existing_hashes(conn)

        # Determine which skills actually changed (incremental gate).
        changed = [s for s in skills if prior.get(s.id) != s.content_hash()]
        unchanged = len(skills) - len(changed)
        LOG.info("%d unchanged, %d to (re)embed", unchanged, len(changed))

        if changed:
            embedder = Embedder()
            vectors = embedder.embed_passages([s.body for s in changed])
            with conn.cursor() as cur:
                for skill, vec in zip(changed, vectors):
                    if len(vec) != EMBED_DIM:
                        raise ValueError(
                            f"embedding dim {len(vec)} != {EMBED_DIM} for {skill.id}"
                        )
                    cur.execute(
                        UPSERT_SQL,
                        {
                            "id": skill.id,
                            "name": skill.name,
                            "description": skill.description,
                            "pack": skill.pack,
                            "repo": skill.repo,
                            "path": skill.path,
                            "origin": skill.origin,
                            "maturity": skill.maturity,
                            "content_hash": skill.content_hash(),
                            "body": skill.body,
                            "embedding": vec,
                        },
                    )

        if prune:
            catalog_ids = {s.id for s in skills}
            stale = [sid for sid in prior if sid not in catalog_ids]
            if stale:
                LOG.info("pruning %d skills no longer in catalog", len(stale))
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM skills WHERE id = ANY(%s)", (stale,))

        conn.commit()
        LOG.info("build complete: %d upserted", len(changed))
        return 0
    except Exception:
        conn.rollback()
        LOG.exception("build failed; rolled back")
        return 1
    finally:
        conn.close()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the semantic skill index.")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("catalog.json"),
        help="Path to catalog.json (default: ./catalog.json)",
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="PostgreSQL URL. Falls back to STARLIGHT_DB_URL / DATABASE_URL / PG* env.",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Delete indexed skills that are no longer present in the catalog.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    db_url = resolve_db_url(args.db_url)
    return build(args.catalog, db_url, prune=args.prune)


if __name__ == "__main__":
    sys.exit(main())
