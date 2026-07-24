# Deploy `starlight-skill-index` as ONE shared always-on service

The point: **one** long-running server on `http://127.0.0.1:8631/mcp` that every CLI
and subagent connects to — instead of each spawning its own stdio process and loading
its own catalog/model. One process, one catalog, one model, many clients.

Endpoint after start: **`http://127.0.0.1:8631/mcp`** (streamable-HTTP).
Configure every CLI with that URL (see [`../README.md`](../README.md) → *Add it to your AI CLI*).

Env the service honors: `STARLIGHT_HTTP_HOST` (default `127.0.0.1`),
`STARLIGHT_HTTP_PORT` (default `8631`), `STARLIGHT_CATALOG`, `STARLIGHT_DB_URL`
(enables the vector path), `STARLIGHT_SCAN_REPORT`.

> Bind to `127.0.0.1` (localhost only). Do **not** expose this port off-host without
> an auth proxy — it serves your whole skill catalog.

---

## Windows (Task Scheduler)

`starlight-skill-index.xml` is an importable task that runs the server at logon,
bound to localhost, restarting on failure. Edit the two `<!-- EDIT -->` paths
(python exe + repo path) first, then:

```powershell
# Import (adjust path). Runs `python server.py --http` at logon.
schtasks /Create /TN "starlight-skill-index" /XML ".\starlight-skill-index.xml"

# Start now / stop / remove:
schtasks /Run    /TN "starlight-skill-index"
schtasks /End    /TN "starlight-skill-index"
schtasks /Delete /TN "starlight-skill-index" /F
```

Or one line without the XML:

```powershell
$py   = "C:\Path\to\python.exe"
$repo = "C:\Path\to\starlight-agentic-os"
schtasks /Create /TN "starlight-skill-index" /SC ONLOGON /RL LIMITED /F `
  /TR "`"$py`" `"$repo\mcp-server\server.py`" --http"
```

Verify: `curl http://127.0.0.1:8631/mcp` (expect an MCP handshake response, not a refusal).

---

## Linux / WSL / macOS (systemd user unit)

`starlight-skill-index.service` is a user unit (no root). Edit its `ExecStart` and
`WorkingDirectory` to your python + repo path, then:

```bash
mkdir -p ~/.config/systemd/user
cp starlight-skill-index.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now starlight-skill-index
systemctl --user status starlight-skill-index      # confirm active (running)
journalctl --user -u starlight-skill-index -f      # logs
```

macOS without systemd: run `python server.py --http` under `launchd` or a `tmux`/`screen`
session; the server itself is platform-agnostic.

---

## Health check

```bash
# The service is up if the port answers and list_packs returns the real catalog.
curl -s http://127.0.0.1:8631/mcp -H 'Accept: text/event-stream' -o /dev/null -w '%{http_code}\n'
```
For a functional check, point any MCP client at the URL and call `list_packs` — it
should report the full 418-skill catalog from the single shared process.
