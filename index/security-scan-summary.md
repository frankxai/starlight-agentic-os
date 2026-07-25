# Skill Frontmatter Security Scan — Summary

**Date:** 2026-07-24 · **Scanner:** `scan_skill_frontmatter.py` · **Input:** `catalog.json` (418 skills)
**Threat class:** semantic supply-chain — a skill's router-visible `name`/`description` is read
*before* its body, so a malicious one can try to hijack routing or inject instructions.

## Result: 418 scanned · 2 active flags (0 high · 2 medium · 0 low) · 1 exact exception

All three lexical matches were reviewed. The single high-severity false positive is removed
from the blocking set only through a content-addressed exception bound to the exact skill id,
rule, and evidence digest. The two medium findings remain visible in the committed report.

| Sev | Skill | Rule | Evidence | Triage |
|---|---|---|---|---|
| 🔴 HIGH · exact exception | `superpowers:using-tmux-for-interactive-commands` | `exfiltration_intent` | "…sessions and **send**-**keys**" | **FALSE POSITIVE.** The exception is bound to evidence SHA-256 `5a30d9f8…d291`; any wording change makes it stale and fails the gate. |
| 🟡 MED | `agentic-creator-os:higgsfield-operator` | `embedded_url` | `https://mcp.higgsfield.ai/mcp` | **BENIGN.** A legitimate MCP connector URL — expected in an operator skill that wires that service. |
| 🟡 MED | `starlight-intelligence-system:safety/secret-detector` | `secret_solicitation` | "…credentials, API keys, tokens…" | **FALSE POSITIVE BY DESIGN.** This skill's *job* is detecting secrets, so its description lists what it looks for. |

## Interpretation

- The one HIGH is a **lexical collision** (`send-keys`), not intent. The exact exception preserves
  the valuable rule while refusing to transfer trust to changed evidence.
- The two MEDIUMs are the expected shape of legitimate skills: one names a real MCP endpoint, one
  is a security tool describing its own domain.

## CI enforcement

CI reruns the scanner with `--fail-on high`, validates the exact exception file, and requires the
live JSON report to equal this committed artifact. A new HIGH, changed evidence, stale exception,
or hand-edited report fails the repository gate.
