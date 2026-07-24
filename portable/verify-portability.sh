#!/usr/bin/env bash
# =============================================================================
# verify-portability.sh — CI-usable portability gate for a Starlight pack.
# -----------------------------------------------------------------------------
# Verifies a pack satisfies the portable tripod convention:
#   1. AGENTS.md exists at the pack root (memory source of truth).
#   2. At least one skills/<name>/SKILL.md exists with VALID YAML frontmatter
#      containing non-empty `name:` and `description:` keys.
#   3. mcp/servers.json (if present) is valid JSON with an mcpServers object.
#   4. Declared aliases resolve: if CLAUDE.md / GEMINI.md exist they must point
#      at AGENTS.md (symlink target or identical content).
#
# Exit 0 = portable. Exit non-zero = a human/CI must fix the pack.
#
# USAGE:  ./verify-portability.sh <pack-dir>       # defaults to CWD
#         ./verify-portability.sh ./packs/acos-meta
# =============================================================================
set -uo pipefail

PACK="${1:-.}"
FAIL=0
PASS=0

c_reset='\033[0m'; c_green='\033[32m'; c_red='\033[31m'; c_yellow='\033[33m'; c_dim='\033[2m'
pass() { printf "${c_green}PASS${c_reset} %s\n" "$*"; PASS=$((PASS+1)); }
fail() { printf "${c_red}FAIL${c_reset} %s\n" "$*"; FAIL=$((FAIL+1)); }
warn() { printf "${c_yellow}WARN${c_reset} %s\n" "$*"; }
info() { printf "${c_dim}  -> %s${c_reset}\n" "$*"; }

if [ ! -d "$PACK" ]; then
  echo "verify-portability: not a directory: $PACK" >&2
  exit 2
fi
PACK="$(cd "$PACK" && pwd -P)"
echo "Verifying portable pack: $PACK"
echo "-------------------------------------------------------------"

# --- 1. AGENTS.md ------------------------------------------------------------
if [ -f "$PACK/AGENTS.md" ] && [ -s "$PACK/AGENTS.md" ]; then
  pass "AGENTS.md present and non-empty"
else
  fail "AGENTS.md missing or empty at pack root"
fi

# --- 2. skills/<name>/SKILL.md with valid frontmatter ------------------------
if [ ! -d "$PACK/skills" ]; then
  fail "skills/ directory missing"
else
  skill_count=0
  valid_skills=0
  while IFS= read -r skill; do
    skill_count=$((skill_count+1))
    # Frontmatter must start on line 1 with '---' and close with '---'.
    first_line="$(head -n 1 "$skill")"
    if [ "$first_line" != "---" ]; then
      fail "frontmatter missing (no leading '---'): $skill"
      continue
    fi
    # Extract the frontmatter block (between first two '---' fences).
    fm="$(awk 'NR==1&&/^---[[:space:]]*$/{f=1;next} f&&/^---[[:space:]]*$/{exit} f{print}' "$skill")"
    name_val="$(printf '%s\n' "$fm"        | sed -n 's/^name:[[:space:]]*//p'        | head -n1)"
    desc_val="$(printf '%s\n' "$fm"        | sed -n 's/^description:[[:space:]]*//p' | head -n1)"
    if [ -z "$name_val" ]; then
      fail "frontmatter missing 'name:' -> $skill"; continue
    fi
    if [ -z "$desc_val" ]; then
      fail "frontmatter missing 'description:' -> $skill"; continue
    fi
    valid_skills=$((valid_skills+1))
    info "skill '$name_val' ok ($(basename "$(dirname "$skill")")/SKILL.md)"
  done < <(find "$PACK/skills" -mindepth 2 -maxdepth 2 -name 'SKILL.md' 2>/dev/null)

  if [ "$skill_count" -eq 0 ]; then
    fail "no skills/<name>/SKILL.md found"
  elif [ "$valid_skills" -eq "$skill_count" ]; then
    pass "$valid_skills/$skill_count SKILL.md files have valid frontmatter"
  else
    fail "$valid_skills/$skill_count SKILL.md files valid (see failures above)"
  fi
fi

# --- 3. mcp/servers.json (optional, but must be valid if present) ------------
if [ -f "$PACK/mcp/servers.json" ]; then
  if command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); assert isinstance(d.get("mcpServers", d), dict)' "$PACK/mcp/servers.json" 2>/dev/null; then
      pass "mcp/servers.json is valid JSON with an mcpServers object"
    else
      fail "mcp/servers.json is invalid JSON or lacks an mcpServers object"
    fi
  else
    warn "python3 not found — skipping mcp/servers.json validation"
  fi
else
  warn "mcp/servers.json not present (pack ships no tools — acceptable)"
fi

# --- 4. Alias resolution -----------------------------------------------------
check_alias() {
  local alias_path="$1" label="$2"
  [ -e "$alias_path" ] || return 0   # alias is optional
  if [ -L "$alias_path" ]; then
    local tgt; tgt="$(readlink "$alias_path")"
    case "$tgt" in
      *AGENTS.md) pass "$label symlink resolves to AGENTS.md" ;;
      *) fail "$label symlink points at '$tgt', expected AGENTS.md" ;;
    esac
  else
    # Not a symlink: accept only if byte-identical to AGENTS.md.
    if [ -f "$PACK/AGENTS.md" ] && cmp -s "$alias_path" "$PACK/AGENTS.md"; then
      pass "$label is a content copy identical to AGENTS.md"
    else
      fail "$label exists but is neither a symlink to nor a copy of AGENTS.md"
    fi
  fi
}
check_alias "$PACK/CLAUDE.md" "CLAUDE.md"
check_alias "$PACK/GEMINI.md" "GEMINI.md"

# Gemini settings.json (if shipped in-pack) should point context.fileName at AGENTS.md.
if [ -f "$PACK/.gemini/settings.json" ] && command -v python3 >/dev/null 2>&1; then
  fn="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("context",{}).get("fileName",""))' "$PACK/.gemini/settings.json" 2>/dev/null)"
  if [ "$fn" = "AGENTS.md" ]; then
    pass ".gemini/settings.json context.fileName -> AGENTS.md"
  else
    fail ".gemini/settings.json context.fileName is '$fn', expected AGENTS.md"
  fi
fi

echo "-------------------------------------------------------------"
echo "Result: $PASS passed, $FAIL failed."
if [ "$FAIL" -gt 0 ]; then
  echo "Pack is NOT portable-clean. Fix the FAIL items above." >&2
  exit 1
fi
echo "Pack is portable-clean."
exit 0
