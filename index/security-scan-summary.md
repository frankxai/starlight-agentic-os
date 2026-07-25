# Skill Frontmatter Security Scan — Summary

**Date:** 2026-07-24 · **Scanner:** `scan_skill_frontmatter.py` · **Input:** `catalog.json` (418 skills)
**Threat class:** semantic supply-chain — a skill's router-visible `name`/`description` is read
*before* its body, so a malicious one can try to hijack routing or inject instructions.

## Result: 418 scanned · 3 flagged (1 high · 2 medium · 0 low) · **0 genuine attacks**

All three flags were manually triaged and cleared as benign / false-positive. The scanner is
working correctly (it caught the exact lexical patterns it should); none of Frank's real skills
carry an actual router-hijack, injection, exfiltration, or homoglyph attack.

**Gate state, 2026-07-25:** the one HIGH finding is now bound to its exact skill id, rule, and
evidence SHA-256 in `security-allowlist.json`. The two MEDIUM findings remain visible and
unallowlisted. Required CI fails on any other HIGH, changed evidence, stale exception, or duplicate
exception.

| Sev | Skill | Rule | Evidence | Triage |
|---|---|---|---|---|
| 🔴 HIGH | `superpowers:using-tmux-for-interactive-commands` | `exfiltration_intent` | "…sessions and **send**-**keys**" | **FALSE POSITIVE.** Matched `send…keys` — but "send-keys" is the literal **tmux subcommand name**, not data exfiltration. Vendored superpowers-lab skill. |
| 🟡 MED | `agentic-creator-os:higgsfield-operator` | `embedded_url` | `https://mcp.higgsfield.ai/mcp` | **BENIGN.** A legitimate MCP connector URL — expected in an operator skill that wires that service. |
| 🟡 MED | `starlight-intelligence-system:safety/secret-detector` | `secret_solicitation` | "…credentials, API keys, tokens…" | **FALSE POSITIVE BY DESIGN.** This skill's *job* is detecting secrets, so its description lists what it looks for. |

## Interpretation

- The one HIGH is a **lexical collision** (`send-keys`), not intent — the kind of thing a human
  reviewer clears in seconds but a regex can't. Keep it on the allow-list rather than suppressing
  the rule (the rule is valuable).
- The two MEDIUMs are the expected shape of legitimate skills: one names a real MCP endpoint, one
  is a security tool describing its own domain.

## CI contract

Run `scan_skill_frontmatter.py --fail-on high --allowlist index/security-allowlist.json` as the
pre-index gate. Only the exact HIGH collision is excepted; MEDIUM findings stay in the report for
review. Re-triage on every catalog regeneration. A new HIGH, modified evidence, or obsolete
exception blocks the build.
