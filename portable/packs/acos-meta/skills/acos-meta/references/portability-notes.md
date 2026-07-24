# Portability notes (acos-meta)

## Why AGENTS.md as the memory root
`AGENTS.md` is the emerging cross-agent convention (Codex, Grok, and many CLIs
read it natively). Making it the source and aliasing everything else means one
edit propagates everywhere; no CLI owns the truth.

## Symlink table (what the installer creates)
| Asset               | Claude Code                | Codex                      | Gemini                       | Grok                |
|---------------------|----------------------------|----------------------------|------------------------------|---------------------|
| skills/             | `~/.claude/skills/<pack>`  | `~/.agents/skills/<pack>`  | `~/.gemini/skills/<pack>`    | (shares AGENTS mem) |
| memory (AGENTS.md)  | `~/.claude/CLAUDE.md`      | `~/.codex/AGENTS.md`       | `~/.gemini/AGENTS.md` + settings.json | `~/.grok/AGENTS.md` |
| MCP (servers.json)  | `~/.claude/.mcp.json`      | `~/.codex/config.toml`     | `~/.gemini/settings.json`    | (json shape reuse)  |

## Interpolation
Values in `mcp/servers.json` may reference `${PACK_ROOT}`; the installer replaces
it with the absolute pack path so filesystem servers resolve correctly.

## Idempotency
Re-running the installer relinks only when the target differs. `--uninstall`
reads `.portable-install.manifest` and removes only what was created.
