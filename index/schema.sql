-- index/schema.sql
-- Starlight Agentic OS — Phase D: semantic skill index schema (PostgreSQL + pgvector).
--
-- Run once against a fresh database, e.g.:
--   createdb starlight_skills
--   psql "$DB_URL" -f index/schema.sql
--
-- Idempotent: safe to re-run. Uses IF NOT EXISTS everywhere.

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
-- pgvector supplies the `vector` type and the ANN index access methods.
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- skills table
-- ---------------------------------------------------------------------------
-- One row per SKILL.md. The `embedding` column holds the 768-dim
-- intfloat/multilingual-e5-base vector computed from the FULL skill body
-- (encoded with the required e5 "passage: " prefix, mean-pooled over chunks
-- for over-length bodies — see build_index.py).
--
-- `body` is stored so that search.py can rerank over the full skill text
-- (cross-encoder) without needing access to the original repo checkout at
-- query time; this keeps the retriever self-contained. It is intentionally
-- NOT part of the ANN index.
--
-- `content_hash` is the incremental-upsert key: build_index.py only recomputes
-- an embedding when the hash of (name + description + body) changes.
CREATE TABLE IF NOT EXISTS skills (
    id            TEXT PRIMARY KEY,           -- stable catalog id (e.g. "pack:name")
    name          TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    pack          TEXT,                        -- skill pack / plugin it belongs to
    repo          TEXT,                        -- source repository
    path          TEXT,                        -- path to SKILL.md within the repo
    origin        TEXT,                        -- provenance: "official" | "community" | ...
    maturity      TEXT,                        -- "stable" | "beta" | "experimental" | ...
    content_hash  TEXT NOT NULL,               -- sha256 over embedded content
    body          TEXT NOT NULL DEFAULT '',    -- full skill body (used for reranking)
    embedding     vector(768) NOT NULL,        -- e5-base passage embedding, L2-normalized
    indexed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- ANN index: HNSW (chosen over IVFFlat)
-- ---------------------------------------------------------------------------
-- Rationale:
--   * A skill library is in the 10^2–10^4 range and is READ-heavy (every agent
--     routing decision queries it) but WRITE-light (rebuilt incrementally).
--   * HNSW gives markedly better recall/latency at low-to-mid corpus sizes and,
--     unlike IVFFlat, needs NO training step and NO "lists" tuning — it is
--     queryable immediately after the first insert, which matters for an
--     incrementally-built index that may start nearly empty.
--   * IVFFlat only pays off at very large N and requires ANALYZE/lists tuning
--     to avoid poor recall; not worth it here.
--
-- We embed with cosine semantics (vectors are L2-normalized at build time), so
-- we index with vector_cosine_ops and query with the `<=>` (cosine) operator.
CREATE INDEX IF NOT EXISTS skills_embedding_hnsw
    ON skills
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Secondary btree indexes for metadata filtering (optional pushdown).
CREATE INDEX IF NOT EXISTS skills_pack_idx     ON skills (pack);
CREATE INDEX IF NOT EXISTS skills_maturity_idx ON skills (maturity);
CREATE INDEX IF NOT EXISTS skills_origin_idx   ON skills (origin);

-- Set a sensible default search quality for the session-less case.
-- (Callers may override per-connection: SET hnsw.ef_search = 100;)
