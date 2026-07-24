# Starlight Observability (self-hosted, sovereign)

Reference stack: **OpenLLMetry** (instrument the code) → **self-hosted Langfuse**
(the sink) → **native Claude Code OTel** (`CLAUDE_CODE_ENABLE_TELEMETRY=1`) for the
CLI. All OTLP, local-first, no vendor lock-in.

## Files
| File | Purpose |
|------|---------|
| `docker-compose.langfuse.yml` | Langfuse v3 stack: web + worker + postgres + clickhouse + redis + minio |
| `otel.env.example` | Env to point Claude Code + other CLIs + OpenLLMetry at the local OTLP ingest |
| `INSTRUMENTATION.md` | How to instrument the fleet, what signals you get, dashboards/alerts to build |

## Bring-up sequence
```bash
cd observability

# 1. Create your local secrets file (never committed).
cp otel.env.example .env
#    Fill CHANGE_ME values. Generate the 32-byte secrets:
#    openssl rand -hex 32   # -> LANGFUSE_SALT, LANGFUSE_ENCRYPTION_KEY, LANGFUSE_NEXTAUTH_SECRET
#    Also set POSTGRES_PASSWORD, CLICKHOUSE_PASSWORD, REDIS_PASSWORD, MINIO_ROOT_PASSWORD.

# 2. Start the stack.
docker compose --env-file .env -f docker-compose.langfuse.yml up -d

# 3. Watch it come healthy (web waits on postgres/clickhouse/redis/minio).
docker compose -f docker-compose.langfuse.yml ps

# 4. Open the UI, create a project, copy its pk-lf-.../sk-lf-... API keys.
open http://localhost:3000            # (or set LANGFUSE_INIT_* to bootstrap headless)

# 5. Build the Basic-auth header and export the OTel env for a CLI run.
export LANGFUSE_OTEL_BASIC="$(printf '%s' 'pk-lf-...:sk-lf-...' | base64)"
set -a; . ./.env; set +a
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic%20${LANGFUSE_OTEL_BASIC}"

# 6. Launch an agent with telemetry on and watch traces land in Langfuse.
CLAUDE_CODE_ENABLE_TELEMETRY=1 claude
```

Tear down (keep data): `docker compose -f docker-compose.langfuse.yml down`
Tear down (wipe volumes): `docker compose -f docker-compose.langfuse.yml down -v`

## Ports
| Service | Host port | Notes |
|---------|-----------|-------|
| Langfuse web / OTLP ingest | 3000 | UI + `POST /api/public/otel/v1/{traces,metrics}` |
| MinIO S3 API | 9090 | remapped off 9000 to avoid the ClickHouse native-port clash |
| MinIO console | 9091 | object browser |

## Honest status
**Not deployed yet — needs Docker.** These are wired-to-run artifacts, authored
but not executed here. To go live you need Docker + Docker Compose v2 on the host,
a filled `.env` with real secrets, and the ports above free. The compose file is
YAML-validated; the OTel env and instrumentation guide are ready to source. First
real bring-up should be done interactively so you can confirm each service reaches
`healthy` and that a test trace appears in the Langfuse UI.

See `INSTRUMENTATION.md` for the app-code (OpenLLMetry) wiring, per-user audit
signals, nested agent traces, and the starter dashboards/alerts.
