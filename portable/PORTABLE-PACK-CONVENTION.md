# Portable-Pack Convention — write once, run on Claude Code + Codex + Gemini + Grok

This is the canonical spec for a **Starlight portable pack**: a self-contained
directory that installs identically across every agent CLI via symlinks and a
per-CLI config render. One pack, one edit, four runtimes.

---

## 1. Canonical repo layout

```
<pack-name>/                     ← the unit that ships and installs
├── AGENTS.md                    ← MEMORY: single source of truth (portable tripod leg 1)
├── skills/                      ← SKILLS: progressive-disclosure capabilities (leg 2)
│   └── <skill-name>/
│       ├── SKILL.md             ← lean main file; frontmatter: name + description (required)
│       └── references/          ← depth, fetched on demand
├── mcp/
│   └── servers.json             ← TOOLS: one canonical MCP definition (leg 3)
├── .gemini/
│   └── settings.json            ← Gemini interop: {"context":{"fileName":"AGENTS.md"}}
└── .portable-install.manifest   ← created by installer; drives clean --uninstall
```

**The portable tripod (locked):** `memory = AGENTS.md`, `skills = SKILL.md`,
`tools = MCP`. Nothing in the pack body is CLI-specific — CLI wiring is generated.

---

## 2. The symlink table (what the installer wires)

`<pack>` = pack directory name (e.g. `acos-meta`). Roots are overridable via env
(`CLAUDE_HOME`, `CODEX_HOME`, `CODEX_AGENTS_HOME`, `GEMINI_HOME`, `GROK_HOME`).

| Asset               | Claude Code                     | Codex                        | Gemini                                   | Grok                     |
|---------------------|---------------------------------|------------------------------|------------------------------------------|--------------------------|
| **skills/**         | `~/.claude/skills/<pack>` →      | `~/.agents/skills/<pack>` →   | `~/.gemini/skills/<pack>` →               | (uses AGENTS.md memory)  |
| **memory** AGENTS.md| `~/.claude/CLAUDE.md` →          | `~/.codex/AGENTS.md` →        | `~/.gemini/AGENTS.md` → + `settings.json`| `~/.grok/AGENTS.md` →     |
| **MCP** servers.json| `~/.claude/.mcp.json` (render)  | `~/.codex/config.toml` (render)| `~/.gemini/settings.json` (render)      | (reuses JSON `mcpServers`)|

Arrows (→) are symlinks pointing back at the pack; "(render)" means the file is
generated from `mcp/servers.json`, not symlinked.

---

## 3. The four interop moves

These are the only CLI-specific transforms; everything else is a plain symlink.

1. **Claude memory alias** — `ln -s AGENTS.md CLAUDE.md`
   Claude Code reads `CLAUDE.md`; we make it an alias so AGENTS.md stays canonical.

2. **Gemini memory pointer** — write `.gemini/settings.json`:
   ```json
   { "context": { "fileName": "AGENTS.md" } }
   ```
   Gemini does not read `AGENTS.md` by default; this points its context loader at it.

3. **Codex MCP render** — emit `[mcp_servers.<name>]` tables into `~/.codex/config.toml`
   (TOML), wrapped in `# >>> starlight-portable mcp_servers >>>` markers so it merges
   with a user's existing config and un-installs cleanly.

4. **Gemini MCP render** — merge the `mcpServers` object into `~/.gemini/settings.json`
   (JSON). Claude Code takes the same `mcpServers` shape in `~/.claude/.mcp.json`, so
   one JSON definition serves both; only Codex needs the TOML transform.

> Grok and Codex read `AGENTS.md` natively, so memory needs no transform for them —
> just a discovery symlink at their home dir.

---

## 4. `mcp/servers.json` schema

```json
{
  "mcpServers": {
    "<server-name>": {
      "command": "npx",
      "args": ["-y", "@scope/server", "${PACK_ROOT}"],
      "env": { "SOME_KEY": "${SOME_ENV_PLACEHOLDER}" }
    }
  }
}
```

- `${PACK_ROOT}` is interpolated to the absolute pack path at install time.
- **No secrets.** Reference env placeholders; the CLI resolves them at runtime.
- Renders: Claude/Gemini get the object verbatim (JSON); Codex gets TOML tables.

---

## 5. Frontmatter contract (enforced by CI)

Every `skills/<name>/SKILL.md` MUST begin with YAML frontmatter:

```yaml
---
name: <skill-name>
description: <one-to-three sentences; when to use this skill>
---
```

`verify-portability.sh` fails the build if `name:` or `description:` is missing.

---

## 6. Worked example — the `acos-meta` exemplar pack

Layout shipped in `portable/packs/acos-meta/`:

```
packs/acos-meta/
├── AGENTS.md
├── skills/acos-meta/SKILL.md
├── skills/acos-meta/references/portability-notes.md
├── mcp/servers.json
└── .gemini/settings.json
```

### Dry-run, then install (macOS / Linux)

```bash
cd portable

# See exactly what will happen — no filesystem changes:
./install.sh --pack ./packs/acos-meta --dry-run

# Wire it into all four CLIs:
./install.sh --pack ./packs/acos-meta
```

Resulting links for this pack:

```
~/.claude/skills/acos-meta   -> <repo>/portable/packs/acos-meta/skills
~/.agents/skills/acos-meta   -> <repo>/portable/packs/acos-meta/skills     (Codex)
~/.gemini/skills/acos-meta   -> <repo>/portable/packs/acos-meta/skills
~/.claude/CLAUDE.md          -> <repo>/portable/packs/acos-meta/AGENTS.md
~/.codex/AGENTS.md           -> <repo>/portable/packs/acos-meta/AGENTS.md
~/.grok/AGENTS.md            -> <repo>/portable/packs/acos-meta/AGENTS.md
~/.gemini/AGENTS.md          -> <repo>/portable/packs/acos-meta/AGENTS.md
~/.claude/.mcp.json          (rendered: mcpServers = acos-filesystem, acos-memory)
~/.gemini/settings.json      (rendered: mcpServers + context.fileName=AGENTS.md)
~/.codex/config.toml         (rendered: [mcp_servers.acos-filesystem], [mcp_servers.acos-memory])
```

### Windows (PowerShell)

```powershell
cd portable

# Enable Developer Mode OR run this shell as Administrator first (symlink caveat).
.\install.ps1 -Pack .\packs\acos-meta -DryRun
.\install.ps1 -Pack .\packs\acos-meta
```

**Windows symlink caveat:** `New-Item -ItemType SymbolicLink` (and `mklink`)
require **Developer Mode** enabled *or* an **elevated (Administrator)** shell.
`install.ps1` tries `New-Item` first, falls back to `cmd /c mklink` (`/D` for
directories), and finally to a directory **junction** (`mklink /J`, which needs
no elevation but only works for local directories). If every strategy fails, the
script tells you to enable Developer Mode or re-run as Admin.

### Verify (CI-usable)

```bash
bash verify-portability.sh ./packs/acos-meta
echo "exit code: $?"   # 0 = portable-clean; non-zero = fix the pack
```

### Uninstall (removes only what was created)

```bash
./install.sh --pack ./packs/acos-meta --uninstall      # macOS / Linux
.\install.ps1 -Pack .\packs\acos-meta -Uninstall       # Windows
```

---

## 7. CI snippet

```yaml
# .github/workflows/portability.yml
name: portability
on: [push, pull_request]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: bash portable/verify-portability.sh portable/packs/acos-meta
```

---

## 8. Adding a new CLI

Extend the installer's target roots and add its three moves (skills dir, memory
alias/pointer, MCP render). If the CLI reads `AGENTS.md` and takes `mcpServers`
JSON, it costs one symlink and zero transforms — that is the whole point of the
convention.
