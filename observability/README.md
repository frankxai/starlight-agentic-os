# Starlight Observability (local-first, no Docker required)

Two tiers. **Default is Phoenix — one `pip install`, one process, no Docker.**
Langfuse is kept as the optional heavy/team tier.

| Tier | Sink | What it needs | Use it when |
|---|---|---|---|
| **Default** | **Arize Phoenix** | `pip install arize-phoenix` + `phoenix serve` — one process, local SQLite/DuckDB | Solo/dev, "just show me the traces", no Docker |
| Optional (heavy) | Self-hosted Langfuse | Docker Compose: web+worker+postgres+clickhouse+redis+minio | Team, long retention, multi-user, prompt mgmt |

Instrumentation is the **same** for both: **OpenLLMetry** (vendor-neutral OTel) +
**native Claude Code OTel** (`CLAUDE_CODE_ENABLE_TELEMETRY=1`). Only the OTLP endpoint
differs — so you can start on Phoenix today and point at Langfuse later without
re-instrumenting. That is the whole reason the sink is swappable.

---

## Default: Phoenix in 30 seconds (no Docker)

```bash
pip install arize-phoenix          # single dependency
phoenix serve                      # UI + OTLP ingest at http://localhost:6006

# In another shell: point the fleet at Phoenix and launch an agent.
set -a; . ./otel.env.example; set +a      # OTLP endpoint already defaults to Phoenix
CLAUDE_CODE_ENABLE_TELEMETRY=1 claude
# Open http://localhost:6006 — traces/metrics land live.
```

Full walkthrough (backends, ports, offline, eval-time tracing):
[`phoenix-quickstart.md`](phoenix-quickstart.md).

Phoenix ingests OTLP on **:6006** (HTTP) and **:4317** (gRPC), stores to local
SQLite/DuckDB, and needs no ClickHouse/Redis/Postgres/MinIO. This is the direct
answer to *"do better than Langfuse so we don't need extra Docker."*

---

## Optional heavy tier: self-hosted Langfuse (Docker)

Only when you need multi-user, long retention, or prompt management. Everything below
is authored-but-not-run; it needs Docker + Docker Compose v2.

```bash
cd observability
cp otel.env.example .env
#   Uncomment the LANGFUSE_* block + fill CHANGE_ME values.
#   openssl rand -hex 32   -> LANGFUSE_SALT, LANGFUSE_ENCRYPTION_KEY, LANGFUSE_NEXTAUTH_SECRET
#   Also set POSTGRES_PASSWORD, CLICKHOUSE_PASSWORD, REDIS_PASSWORD, MINIO_ROOT_PASSWORD.
docker compose --env-file .env -f docker-compose.langfuse.yml up -d
docker compose -f docker-compose.langfuse.yml ps      # wait for healthy
# UI/OTLP at http://localhost:3000 ; switch the OTEL endpoint (see otel.env.example Option C).
```
Tear down: `docker compose -f docker-compose.langfuse.yml down` (`-v` to wipe volumes).

### Langfuse ports (heavy tier only)
| Service | Host port | Notes |
|---------|-----------|-------|
| Langfuse web / OTLP ingest | 3000 | UI + `POST /api/public/otel/v1/{traces,metrics}` |
| MinIO S3 API | 9090 | remapped off 9000 to avoid the ClickHouse native-port clash |
| MinIO console | 9091 | object browser |

---

## Files
| File | Purpose |
|------|---------|
| `phoenix-quickstart.md` | **Default tier** — Phoenix no-Docker setup, backends, offline, evals |
| `otel.env.example` | OTLP env; **defaults to Phoenix (localhost:6006)**, Langfuse as an option |
| `INSTRUMENTATION.md` | OpenLLMetry app-code wiring, fleet signals, dashboards/alerts (sink-agnostic) |
| `docker-compose.langfuse.yml` | Optional heavy tier: full Langfuse v3 stack |

## Honest status
**Phoenix path is a real one-liner** (`pip install arize-phoenix` — not run here, but a
single dependency, no Docker). **Langfuse path is authored, not run** (needs Docker). The
OTel env + instrumentation guide are sink-agnostic and ready to source either way.
