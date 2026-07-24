#!/usr/bin/env bash
# =============================================================================
# Starlight Agentic OS — Portable Pack Installer (macOS / Linux)
# -----------------------------------------------------------------------------
# Symlinks ONE portable pack's assets into every CLI's expected location so a
# single pack runs identically on Claude Code, Codex, Gemini, and Grok.
#
# The portable tripod (locked decisions):
#   memory  -> AGENTS.md   (source of truth; aliased to CLAUDE.md, wired for Gemini)
#   skills  -> skills/<name>/SKILL.md   (symlinked into each CLI skills dir)
#   tools   -> mcp/servers.json  (rendered per-CLI into its native MCP config)
#
# Design goals: idempotent, --dry-run, --uninstall, no secrets, POSIX-friendly.
# Requires: bash 3.2+, coreutils, python3 (for JSON->TOML/JSON rendering).
# =============================================================================
set -euo pipefail

# ------------------------------- defaults ------------------------------------
PACK_DIR=""
DRY_RUN=0
UNINSTALL=0
FORCE=0
VERBOSE=0

# CLI target roots (override via env for non-standard installs)
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
CODEX_AGENTS_HOME="${CODEX_AGENTS_HOME:-$HOME/.agents}"   # Codex skills root
GEMINI_HOME="${GEMINI_HOME:-$HOME/.gemini}"
GROK_HOME="${GROK_HOME:-$HOME/.grok}"

SELF="$(basename "$0")"

# ------------------------------- helpers -------------------------------------
c_reset='\033[0m'; c_blue='\033[34m'; c_green='\033[32m'; c_yellow='\033[33m'; c_red='\033[31m'; c_dim='\033[2m'
log()   { printf "${c_blue}[*]${c_reset} %s\n" "$*"; }
ok()    { printf "${c_green}[+]${c_reset} %s\n" "$*"; }
warn()  { printf "${c_yellow}[!]${c_reset} %s\n" "$*" >&2; }
err()   { printf "${c_red}[x]${c_reset} %s\n" "$*" >&2; }
dbg()   { [ "$VERBOSE" -eq 1 ] && printf "${c_dim}    %s${c_reset}\n" "$*" || true; }
run()   { if [ "$DRY_RUN" -eq 1 ]; then printf "${c_dim}    dry-run: %s${c_reset}\n" "$*"; else eval "$@"; fi; }

usage() {
  cat <<EOF
${SELF} — install one portable pack across every agent CLI.

USAGE:
  ${SELF} --pack <path-to-pack> [--dry-run] [--uninstall] [--force] [--verbose]

OPTIONS:
  --pack <dir>   Path to the pack root (must contain AGENTS.md + skills/).
  --dry-run      Print every action without touching the filesystem.
  --uninstall    Remove only the symlinks/config this installer created.
  --force        Replace existing non-symlink targets (backs them up to *.bak).
  --verbose      Extra diagnostic output.
  -h, --help     This help.

TARGET ROOTS (override via env):
  CLAUDE_HOME=${CLAUDE_HOME}
  CODEX_AGENTS_HOME=${CODEX_AGENTS_HOME}   CODEX_HOME=${CODEX_HOME}
  GEMINI_HOME=${GEMINI_HOME}
  GROK_HOME=${GROK_HOME}

EXAMPLE (acos-meta exemplar pack):
  ${SELF} --pack ./packs/acos-meta --dry-run
  ${SELF} --pack ./packs/acos-meta
EOF
}

# ------------------------------- arg parse -----------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --pack)      PACK_DIR="${2:-}"; shift 2 ;;
    --pack=*)    PACK_DIR="${1#*=}"; shift ;;
    --dry-run)   DRY_RUN=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --force)     FORCE=1; shift ;;
    --verbose)   VERBOSE=1; shift ;;
    -h|--help)   usage; exit 0 ;;
    *) err "Unknown argument: $1"; usage; exit 2 ;;
  esac
done

[ -n "$PACK_DIR" ] || { err "--pack is required."; usage; exit 2; }
[ -d "$PACK_DIR" ] || { err "Pack directory not found: $PACK_DIR"; exit 2; }

# Resolve to an absolute path (symlinks must point at absolute targets).
PACK_ROOT="$(cd "$PACK_DIR" && pwd -P)"
PACK_NAME="$(basename "$PACK_ROOT")"
AGENTS_SRC="$PACK_ROOT/AGENTS.md"
SKILLS_SRC="$PACK_ROOT/skills"
MCP_SRC="$PACK_ROOT/mcp/servers.json"

# A per-pack manifest so --uninstall only ever touches what we created.
MANIFEST="$PACK_ROOT/.portable-install.manifest"

# ------------------------- filesystem primitives -----------------------------
ensure_dir() {
  local d="$1"
  if [ ! -d "$d" ]; then
    log "mkdir -p $d"
    run "mkdir -p '$d'"
  fi
}

record() { # record a path we created (for uninstall)
  [ "$DRY_RUN" -eq 1 ] && return 0
  printf '%s\n' "$1" >> "$MANIFEST"
}

# Idempotent symlink: link_path -> target. Safe to re-run.
link() {
  local target="$1" link_path="$2"
  if [ -L "$link_path" ]; then
    local cur; cur="$(readlink "$link_path" 2>/dev/null || true)"
    if [ "$cur" = "$target" ]; then
      dbg "up-to-date: $link_path -> $target"
      return 0
    fi
    log "relink $link_path -> $target"
    run "rm -f '$link_path'"
  elif [ -e "$link_path" ]; then
    if [ "$FORCE" -eq 1 ]; then
      warn "backing up existing $link_path -> ${link_path}.bak"
      run "mv '$link_path' '${link_path}.bak'"
    else
      err "Refusing to overwrite non-symlink: $link_path (use --force to back up & replace)"
      return 1
    fi
  else
    log "link  $link_path -> $target"
  fi
  ensure_dir "$(dirname "$link_path")"
  run "ln -s '$target' '$link_path'"
  record "$link_path"
}

# ------------------------- uninstall path ------------------------------------
# Reverse a file's lines portably (GNU tac, else BSD `tail -r`, else awk).
reverse_file() {
  if command -v tac >/dev/null 2>&1; then tac "$1"
  elif tail -r "$1" >/dev/null 2>&1; then tail -r "$1"
  else awk '{a[NR]=$0} END{for(i=NR;i>=1;i--) print a[i]}' "$1"
  fi
}

do_uninstall() {
  log "Uninstalling pack '$PACK_NAME' (removing only installer-created links)"
  if [ ! -f "$MANIFEST" ]; then
    warn "No manifest at $MANIFEST — nothing recorded to remove."
  else
    # Remove symlinks in reverse creation order so nested dirs empty out cleanly.
    while IFS= read -r p; do
      [ -z "$p" ] && continue
      if [ -L "$p" ]; then
        log "unlink $p"; run "rm -f '$p'"
      elif [ -e "$p" ]; then
        warn "skip (not a symlink): $p"
      fi
    done < <(reverse_file "$MANIFEST")
    if [ "$DRY_RUN" -eq 0 ]; then rm -f "$MANIFEST" 2>/dev/null || : > "$MANIFEST"; fi
  fi
  # Surgically undo MCP wiring: strip Codex marker block + remove our JSON keys.
  unwire_mcp
  ok "Uninstall complete for '$PACK_NAME'."
  exit 0
}

# Remove only the servers THIS pack added, leaving user-authored config intact.
unwire_mcp() {
  [ -f "$MCP_SRC" ] || return 0
  [ "$DRY_RUN" -eq 1 ] && { log "dry-run: would strip Codex block + remove our keys from JSON MCP files"; return 0; }
  command -v python3 >/dev/null 2>&1 || { warn "python3 missing — leaving MCP configs; strip manually."; return 0; }
  local codex_out="$CODEX_HOME/config.toml"
  local claude_out="$CLAUDE_HOME/.mcp.json"
  local gemini_out="$GEMINI_HOME/settings.json"
  MCP_SRC="$MCP_SRC" CODEX_OUT="$codex_out" CLAUDE_OUT="$claude_out" GEMINI_OUT="$gemini_out" \
  python3 - <<'PY'
import json, os, re
with open(os.environ["MCP_SRC"]) as f:
    names = list(json.load(f).get("mcpServers", {}).keys())

# Codex: strip our marked block.
cx = os.environ["CODEX_OUT"]
if os.path.exists(cx):
    t = open(cx).read()
    t = re.sub(r"# >>> starlight-portable mcp_servers >>>.*?# <<< starlight-portable mcp_servers <<<\n?",
               "", t, flags=re.S)
    open(cx, "w").write(t)

# JSON files: remove only our server keys.
for path in (os.environ["CLAUDE_OUT"], os.environ["GEMINI_OUT"]):
    if not os.path.exists(path): continue
    try:
        d = json.load(open(path))
    except Exception:
        continue
    ms = d.get("mcpServers", {})
    for n in names: ms.pop(n, None)
    if isinstance(ms, dict) and not ms:
        d.pop("mcpServers", None)
    json.dump(d, open(path, "w"), indent=2); open(path, "a").write("\n")
print("[+] MCP unwired: removed %d server(s)" % len(names))
PY
}

# ------------------------- MCP rendering -------------------------------------
# Render mcp/servers.json into each CLI's native format using python3.
render_mcp() {
  [ -f "$MCP_SRC" ] || { warn "No mcp/servers.json — skipping MCP wiring."; return 0; }
  command -v python3 >/dev/null 2>&1 || { warn "python3 not found — skipping MCP render."; return 0; }

  local claude_out="$CLAUDE_HOME/.mcp.json"          # Claude Code (mcpServers)
  local gemini_out="$GEMINI_HOME/settings.json"      # Gemini (mcpServers, merged)
  local codex_out="$CODEX_HOME/config.toml"          # Codex ([mcp_servers.*])

  ensure_dir "$CLAUDE_HOME"; ensure_dir "$GEMINI_HOME"; ensure_dir "$CODEX_HOME"

  if [ "$DRY_RUN" -eq 1 ]; then
    log "dry-run: would render MCP -> $claude_out (json), $gemini_out (json merge), $codex_out (toml merge)"
    return 0
  fi

  PACK_ROOT="$PACK_ROOT" MCP_SRC="$MCP_SRC" \
  CLAUDE_OUT="$claude_out" GEMINI_OUT="$gemini_out" CODEX_OUT="$codex_out" \
  python3 - <<'PY'
import json, os, re, sys

src   = os.environ["MCP_SRC"]
proot = os.environ["PACK_ROOT"]
with open(src) as f:
    data = json.load(f)

# Allow ${PACK_ROOT} interpolation inside servers.json values.
def interp(obj):
    if isinstance(obj, str):
        return obj.replace("${PACK_ROOT}", proot)
    if isinstance(obj, list):
        return [interp(x) for x in obj]
    if isinstance(obj, dict):
        return {k: interp(v) for k, v in obj.items()}
    return obj

servers = interp(data.get("mcpServers", data))

# ---- Claude Code + Gemini share the mcpServers JSON shape -------------------
def write_json_merge(path, key):
    existing = {}
    if os.path.exists(path):
        try:
            with open(path) as f: existing = json.load(f)
        except Exception:
            existing = {}
    existing.setdefault(key, {})
    existing[key].update(servers)
    with open(path, "w") as f:
        json.dump(existing, f, indent=2)
        f.write("\n")

write_json_merge(os.environ["CLAUDE_OUT"], "mcpServers")
write_json_merge(os.environ["GEMINI_OUT"], "mcpServers")

# ---- Codex config.toml : [mcp_servers.<name>] -------------------------------
def toml_val(v):
    if isinstance(v, bool):  return "true" if v else "false"
    if isinstance(v, (int, float)): return str(v)
    if isinstance(v, list):  return "[" + ", ".join(toml_val(x) for x in v) + "]"
    s = str(v).replace("\\", "\\\\").replace('"', '\\"')
    return '"' + s + '"'

def render_codex(servers):
    out = ["# Managed by Starlight portable installer — [mcp_servers.*] block", ""]
    for name, cfg in servers.items():
        out.append(f"[mcp_servers.{name}]")
        for k, v in cfg.items():
            if isinstance(v, dict):
                # nested table, e.g. env = { KEY = "val" }
                inner = ", ".join(f'{ik} = {toml_val(iv)}' for ik, iv in v.items())
                out.append(f"{k} = {{ {inner} }}")
            else:
                out.append(f"{k} = {toml_val(v)}")
        out.append("")
    return "\n".join(out)

codex_path = os.environ["CODEX_OUT"]
block = render_codex(servers)
marker_start = "# >>> starlight-portable mcp_servers >>>"
marker_end   = "# <<< starlight-portable mcp_servers <<<"
wrapped = f"{marker_start}\n{block}\n{marker_end}\n"
prev = ""
if os.path.exists(codex_path):
    with open(codex_path) as f: prev = f.read()
if marker_start in prev and marker_end in prev:
    prev = re.sub(re.escape(marker_start) + r".*?" + re.escape(marker_end) + r"\n?",
                  wrapped, prev, flags=re.S)
    newcontent = prev
else:
    newcontent = (prev.rstrip() + "\n\n" if prev.strip() else "") + wrapped
with open(codex_path, "w") as f:
    f.write(newcontent)

print(f"[+] MCP rendered: {len(servers)} server(s) -> Claude(.mcp.json), Gemini(settings.json), Codex(config.toml)")
PY

  # NB: MCP config files are shared, human-edited files — we do NOT record them
  # as manifest links. Uninstall (unwire_mcp) strips the Codex marker block and
  # removes only our server keys from the JSON files. See PORTABLE-PACK-CONVENTION.md.
}

# ------------------------- main install --------------------------------------
main() {
  log "Pack: $PACK_NAME"
  log "Root: $PACK_ROOT"
  [ "$DRY_RUN" -eq 1 ] && warn "DRY-RUN: no filesystem changes will be made."

  [ -f "$AGENTS_SRC" ] || { err "Missing AGENTS.md at $AGENTS_SRC"; exit 1; }
  [ -d "$SKILLS_SRC" ] || { err "Missing skills/ at $SKILLS_SRC"; exit 1; }

  [ "$UNINSTALL" -eq 1 ] && do_uninstall

  # 1) SKILLS — symlink the pack's skills dir into each CLI's skills root.
  #    Layout: <CLI_SKILLS>/<pack-name> -> <pack>/skills
  log "--- Skills ---"
  link "$SKILLS_SRC" "$CLAUDE_HOME/skills/$PACK_NAME"
  link "$SKILLS_SRC" "$CODEX_AGENTS_HOME/skills/$PACK_NAME"     # Codex reads ~/.agents/skills
  link "$SKILLS_SRC" "$GEMINI_HOME/skills/$PACK_NAME"           # Gemini skills path

  # 2) MEMORY — AGENTS.md is the source; alias it for every CLI.
  log "--- Memory (AGENTS.md) ---"
  #    Codex + Grok read AGENTS.md natively at the pack root: nothing to do,
  #    but we surface it at each home for user-scope discovery.
  link "$AGENTS_SRC" "$CODEX_HOME/AGENTS.md"
  link "$AGENTS_SRC" "$GROK_HOME/AGENTS.md"
  #    Claude Code reads CLAUDE.md -> alias to AGENTS.md.
  link "$AGENTS_SRC" "$CLAUDE_HOME/CLAUDE.md"
  #    Gemini: point its context fileName at AGENTS.md via settings.json.
  wire_gemini_memory

  # 3) TOOLS — render one mcp/servers.json into each CLI's native MCP config.
  log "--- MCP tools ---"
  render_mcp

  ok "Installed pack '$PACK_NAME' across Claude Code, Codex, Gemini, Grok."
  [ "$DRY_RUN" -eq 0 ] && log "Manifest: $MANIFEST"
  log "Verify with: ./verify-portability.sh '$PACK_ROOT'"
}

# Gemini needs an explicit context.fileName pointer (it does not read AGENTS.md
# by default). We also symlink AGENTS.md next to settings.json for locality.
wire_gemini_memory() {
  local gsettings="$GEMINI_HOME/settings.json"
  link "$AGENTS_SRC" "$GEMINI_HOME/AGENTS.md"
  if [ "$DRY_RUN" -eq 1 ]; then
    log "dry-run: would set context.fileName=AGENTS.md in $gsettings"
    return 0
  fi
  command -v python3 >/dev/null 2>&1 || { warn "python3 missing — set context.fileName=AGENTS.md manually in $gsettings"; return 0; }
  ensure_dir "$GEMINI_HOME"
  GSET="$gsettings" python3 - <<'PY'
import json, os
p = os.environ["GSET"]
d = {}
if os.path.exists(p):
    try:
        with open(p) as f: d = json.load(f)
    except Exception:
        d = {}
d.setdefault("context", {})
d["context"]["fileName"] = "AGENTS.md"
with open(p, "w") as f:
    json.dump(d, f, indent=2); f.write("\n")
print("[+] Gemini context.fileName -> AGENTS.md")
PY
}

main
