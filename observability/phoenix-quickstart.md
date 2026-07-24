# Phoenix Quickstart — the no-Docker default sink

Arize Phoenix is the **default** Starlight observability sink: a single `pip install`,
a single process, a local file-backed store. No ClickHouse, Redis, Postgres, or MinIO —
the exact opposite of the Langfuse heavy tier. Same OpenLLMetry/OTel instrumentation
feeds it, so nothing about your app code changes when you pick Phoenix.

> Not executed on this box (memory-tight, no installs). Phoenix is a single pip
> dependency; this is the ready-to-run recipe.

---

## 1. Install + serve (one process)

```bash
pip install arize-phoenix
phoenix serve
```

That's it. Phoenix now runs at **http://localhost:6006**:
- **UI**: http://localhost:6006 (traces, spans, latency, token cost, evals)
- **OTLP ingest**: `:6006` (HTTP, `POST /v1/traces`) and `:4317` (gRPC)
- **Store**: local SQLite/DuckDB under `~/.phoenix/` — file-backed, survives restarts.

Persist to a chosen dir: `export PHOENIX_WORKING_DIR=~/starlight/phoenix` before `serve`.

---

## 2. Point the fleet at it

`otel.env.example` already defaults the OTLP endpoint to Phoenix, so:

```bash
set -a; . ./otel.env.example; set +a
CLAUDE_CODE_ENABLE_TELEMETRY=1 claude          # native Claude Code OTel -> Phoenix
```

The relevant defaults (already set in `otel.env.example`):

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:6006          # Phoenix OTLP (HTTP)
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:6006/v1/traces
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
# no auth header needed for a local Phoenix (unlike Langfuse's Basic pk:sk)
```

For app code, OpenLLMetry can target Phoenix directly:

```python
from phoenix.otel import register
register(project_name="starlight", endpoint="http://localhost:6006/v1/traces")
# ...or vendor-neutral OpenLLMetry:
# from traceloop.sdk import Traceloop
# Traceloop.init(app_name="starlight", api_endpoint="http://localhost:6006/v1/traces")
```

---

## 3. What you get

- **Traces**: every agent turn, tool call, and nested subagent span.
- **LLM spans**: prompts, completions, token counts, latency, cost — auto-captured by
  OpenLLMetry's framework instrumentors.
- **Evals at trace time**: Phoenix runs LLM-as-judge/eval scorers over captured spans —
  useful alongside the promptfoo CI gate (offline) for online quality signals.

---

## 4. Offline / air-gapped

Phoenix runs fully local; no phone-home is required. Keep the fleet sovereign:

```bash
export PHOENIX_ENABLE_TELEMETRY=false      # disable Phoenix's own usage analytics
```

---

## 5. When to graduate to Langfuse (heavy tier)

Stay on Phoenix for solo/dev and single-box fleets. Move to the Langfuse Docker tier
(`README.md` → optional heavy tier) only when you need: multi-user auth, long-term
retention across restarts at team scale, prompt management/versioning, or a shared
team dashboard. Because instrumentation is OTel-standard, switching is just changing
`OTEL_EXPORTER_OTLP_ENDPOINT` — no code changes.
