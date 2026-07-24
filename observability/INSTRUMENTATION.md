# Instrumenting the Starlight fleet (OpenLLMetry → Langfuse + native Claude Code OTel)

Reference observability stack (locked): **OpenLLMetry** instruments the code →
**self-hosted Langfuse** is the sink → **native Claude Code OTel**
(`CLAUDE_CODE_ENABLE_TELEMETRY=1`) covers the CLI itself. Everything speaks OTLP,
so no vendor lock-in: repoint the endpoint and the same telemetry flows anywhere.

```
                         OTLP (http/protobuf)
  Claude Code ───────────────┐
  Codex / Gemini / Grok ─────┤
  Python agent code ─────────┤──►  [OTel Collector*]  ──►  Langfuse  ──► ClickHouse
   (OpenLLMetry SDK)         │        (optional)          (web+worker)   (traces/scores)
                             │                                │
                       resource attrs                    Postgres / Redis / MinIO
              service.name=starlight.<cli>.<agent>
  * Collector is optional but recommended once you have >1 sink or want to keep
    credentials out of individual shells (fan-in).
```

---

## 1. Native Claude Code OTel (the CLI layer)

Set the env (see `otel.env.example`) before launching Claude Code:

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:3000/api/public/otel
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic%20$(printf '%s' 'pk-lf-...:sk-lf-...' | base64)"
export OTEL_SERVICE_NAME=starlight.claude-code
export OTEL_RESOURCE_ATTRIBUTES="service.namespace=starlight,deployment.environment=local,starlight.pack=acos-meta,enduser.id=frank"
```

### What you get out of the box (metrics + events)
Claude Code emits structured **metrics** and **events/logs**. The ones an AI-ops
team actually watches:

| Signal                       | Type   | Use it for |
|------------------------------|--------|------------|
| `tool_decision`              | event  | which tool the agent chose + whether it was auto-approved |
| `tool_result`               | event  | success/error + duration per tool call → tool-error rate |
| permission / `tool_permission` | event | allow vs **deny** decisions → per-user audit trail |
| token usage (input/output/cache) | metric | **cost per session** (× model price) |
| `api_request` / cost         | metric | latency + spend per model call |
| session / lines-of-code / commit | metric | activity + throughput |

Attach `enduser.id` (via `OTEL_RESOURCE_ATTRIBUTES`) and every `tool_decision`,
`tool_result`, and permission event becomes a **per-user audit record**: who ran
what tool, with what decision, at what cost.

---

## 2. OpenLLMetry for the Python / agent code (the app layer)

Native CLI telemetry covers CLI-driven work; your own agent/orchestration code
needs OpenLLMetry (Traceloop SDK) to emit **traces** with nested spans.

```bash
pip install traceloop-sdk    # OpenLLMetry
```

```python
# top of your agent entrypoint — initialize ONCE
from traceloop.sdk import Traceloop

Traceloop.init(
    app_name="starlight.orchestrator",
    disable_batch=False,
    # endpoint + headers come from env (TRACELOOP_BASE_URL / TRACELOOP_HEADERS),
    # so nothing secret lives in code. See otel.env.example.
)
```

Auto-instrumentation covers the common LLM SDKs and agent frameworks
(OpenAI/Anthropic clients, LangChain, LlamaIndex, CrewAI, etc.). For your own
units of work, annotate:

```python
from traceloop.sdk.decorators import workflow, task

@workflow(name="daily_execution")          # a top-level app trace
def run_daily_execution(brief):
    return dispatch_agent(brief)

@task(name="skill_dispatch")                # a child span → skill-dispatch latency
def dispatch_agent(brief):
    ...
```

### Nesting agent runs inside app traces
Because both the app code and any sub-agents export to the **same OTLP endpoint**
with a shared trace context, a Langfuse trace shows the app `workflow` at the root
with each agent/tool call as nested `observation` spans — one waterfall from user
intent → orchestrator → agent → individual tool call → model request. To preserve
nesting across a subprocess boundary (e.g. shelling out to a CLI), propagate
`traceparent` via env (`OTEL_PROPAGATORS=tracecontext` + pass the header through).

---

## 3. Optional: OpenTelemetry Collector (fan-in)

Once more than one sink or shell is involved, drop a collector in front so
credentials + routing live in one place. Minimal `otel-collector-config.yaml`:

```yaml
receivers:
  otlp:
    protocols:
      http: { endpoint: 0.0.0.0:4318 }
      grpc: { endpoint: 0.0.0.0:4317 }
processors:
  batch: {}
exporters:
  otlphttp/langfuse:
    endpoint: http://langfuse-web:3000/api/public/otel
    headers:
      Authorization: "Basic ${env:LANGFUSE_OTEL_BASIC}"   # base64(pk:sk)
service:
  pipelines:
    traces:  { receivers: [otlp], processors: [batch], exporters: [otlphttp/langfuse] }
    metrics: { receivers: [otlp], processors: [batch], exporters: [otlphttp/langfuse] }
    logs:    { receivers: [otlp], processors: [batch], exporters: [otlphttp/langfuse] }
```

Then point every CLI/app at `http://localhost:4318` (Option B in `otel.env.example`).

---

## 4. Dashboards & alerts an AI-ops team wants (starter set)

Build these in Langfuse (dashboards/metrics) or your metrics backend:

| # | Panel / alert | Source signal | Why |
|---|---------------|---------------|-----|
| 1 | **Cost per session** (and per user, per pack) | token metrics × model price | budget + runaway-loop detection |
| 2 | **Tool-error rate** = errored `tool_result` / total, by tool | tool_result events | reliability regressions per tool |
| 3 | **Permission-denials** count + rate, by user + tool | permission events | security/audit; spikes = misconfigured agent |
| 4 | **Skill-dispatch latency** p50/p95 | `skill_dispatch` task span duration | UX + where to optimize |
| 5 | Model-request latency p95 + timeout rate | api_request metric | provider health |
| 6 | Traces-per-session / agent depth | trace span counts | detect over-orchestration |
| 7 | Token burn rate (tokens/min) | token metrics | early cost alarm |

Suggested **alerts**: tool-error rate > 5% over 15 min; any permission-deny on a
write/exec tool; cost-per-session > $X; skill-dispatch p95 > N s; model timeout
rate > 2%.

---

## 5. Sovereignty note
Every signal above is plain OTLP. Langfuse is just the first sink. Swap the
endpoint (Option B collector → any OTLP-compatible backend) and the exact same
instrumentation keeps working — that is why OpenLLMetry + native OTel keep the
fleet **vendor-portable** while staying **local-first**.
