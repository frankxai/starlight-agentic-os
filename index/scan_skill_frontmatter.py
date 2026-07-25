#!/usr/bin/env python3
"""scan_skill_frontmatter.py — Starlight Agentic OS, Phase D security gate.

A skill's ``description``/frontmatter is an attack surface: it is read by the
router BEFORE the skill body, so a malicious skill can try to hijack routing or
inject instructions ("semantic supply-chain" attack). This scanner statically
inspects each skill's routing-visible text and flags suspicious patterns.

It is designed to gate CI: it exits non-zero when any HIGH-severity finding is
present (configurable via ``--fail-on``), so a poisoned skill cannot silently
enter the index.

Detections
----------
* imperative-instruction injection ("ignore previous instructions", "you must",
  "disregard the system prompt", ...)
* router-hijack / over-broad triggers ("always use this skill", "for every
  request", "use this for all tasks", ...)
* exfiltration / URL patterns (http(s) links, IPs, ``curl``/``wget``, base64
  blobs, prompts to send data somewhere)
* unicode tricks: zero-width characters, bidi control chars, and homoglyphs
  (Cyrillic/Greek letters mixed into ASCII words)
* secret-solicitation ("api key", "password", "token", "credentials")

Input
-----
Either a ``catalog.json`` (``--catalog``) or a directory tree of ``SKILL.md``
files (``--skills-dir``). At least one is required.

Usage
-----
    python scan_skill_frontmatter.py --catalog catalog.json
    python scan_skill_frontmatter.py --skills-dir ./skills --json report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}


# --------------------------------------------------------------------------- #
# Finding model
# --------------------------------------------------------------------------- #
@dataclass
class Finding:
    rule: str
    severity: str  # "low" | "medium" | "high"
    field: str  # which field the match was in ("description", "name", ...)
    message: str
    evidence: str


@dataclass
class SkillReport:
    id: str
    name: str
    path: Optional[str]
    findings: List[Finding] = field(default_factory=list)

    @property
    def max_severity(self) -> Optional[str]:
        if not self.findings:
            return None
        return max((f.severity for f in self.findings), key=lambda s: SEVERITY_ORDER[s])


# --------------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------------- #
# Each rule: (name, severity, compiled regex, human message).
_TEXT_RULES: List[tuple] = [
    (
        "instruction_injection",
        "high",
        re.compile(
            r"\b(ignore|disregard|forget|override)\b[^.\n]{0,40}"
            r"\b(previous|prior|above|earlier|system|all)\b[^.\n]{0,20}"
            r"\b(instruction|instructions|prompt|context|rules?)\b",
            re.IGNORECASE,
        ),
        "Attempts to override prior/system instructions.",
    ),
    (
        "role_reassignment",
        "high",
        re.compile(
            r"\byou\s+are\s+now\b|\bnew\s+system\s+prompt\b|\bact\s+as\s+(?:the\s+)?system\b",
            re.IGNORECASE,
        ),
        "Attempts to reassign the agent's role / system persona.",
    ),
    (
        "router_hijack",
        "high",
        re.compile(
            r"\balways\s+(?:use|select|choose|pick|route\s+to)\b[^.\n]{0,30}\bthis\b"
            r"|\buse\s+this\s+skill\s+for\s+(?:all|every|any)\b"
            r"|\bfor\s+(?:all|every|any)\s+(?:request|task|query|prompt)s?\b"
            r"|\bregardless\s+of\b[^.\n]{0,30}\b(request|task|query|topic)\b",
            re.IGNORECASE,
        ),
        "Over-broad trigger that would hijack the router into always selecting this skill.",
    ),
    (
        "exfiltration_intent",
        "high",
        re.compile(
            r"\b(send|post|upload|exfiltrate|forward|transmit|leak)\b[^.\n]{0,40}"
            r"\b(secrets?|tokens?|keys?|passwords?|credentials?|env|environment|"
            r"conversation|history|data)\b",
            re.IGNORECASE,
        ),
        "Solicits sending sensitive data to an external destination.",
    ),
    (
        "secret_solicitation",
        "medium",
        re.compile(
            r"\b(api[\s_-]?keys?|secret\s+keys?|passwords?|access\s+tokens?|"
            r"bearer\s+tokens?|private\s+keys?|credentials?|\.env\b|aws_secret|"
            r"ssh\s+keys?)\b",
            re.IGNORECASE,
        ),
        "References secrets/credentials in routing-visible text.",
    ),
    (
        "shell_or_download",
        "medium",
        re.compile(
            r"\b(curl|wget|invoke-webrequest|iwr|powershell\s+-enc|base64\s+-d|"
            r"subprocess|os\.system|eval\(|exec\()\b",
            re.IGNORECASE,
        ),
        "References shell/download/eval primitives in frontmatter.",
    ),
    (
        "embedded_url",
        "medium",
        re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE),
        "Contains an embedded URL (possible exfil / drive-by instruction target).",
    ),
    (
        "raw_ip",
        "medium",
        re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        "Contains a raw IP address.",
    ),
    (
        "base64_blob",
        "low",
        re.compile(r"\b[A-Za-z0-9+/]{60,}={0,2}\b"),
        "Contains a long base64-looking blob (possible hidden payload).",
    ),
    (
        "urgency_pressure",
        "low",
        re.compile(
            r"\b(urgent|immediately|do\s+not\s+tell|don't\s+tell|without\s+asking|"
            r"do\s+not\s+mention|silently)\b",
            re.IGNORECASE,
        ),
        "Uses pressure / secrecy language.",
    ),
]

# Zero-width and bidi control characters that can hide instructions.
_INVISIBLE_CHARS = {
    "\u200B": "ZERO WIDTH SPACE",
    "\u200C": "ZERO WIDTH NON-JOINER",
    "\u200D": "ZERO WIDTH JOINER",
    "\u2060": "WORD JOINER",
    "\uFEFF": "ZERO WIDTH NO-BREAK SPACE / BOM",
    "\u202A": "LEFT-TO-RIGHT EMBEDDING",
    "\u202B": "RIGHT-TO-LEFT EMBEDDING",
    "\u202C": "POP DIRECTIONAL FORMATTING",
    "\u202D": "LEFT-TO-RIGHT OVERRIDE",
    "\u202E": "RIGHT-TO-LEFT OVERRIDE",
    "\u2066": "LEFT-TO-RIGHT ISOLATE",
    "\u2067": "RIGHT-TO-LEFT ISOLATE",
    "\u2068": "FIRST STRONG ISOLATE",
    "\u2069": "POP DIRECTIONAL ISOLATE",
}

# Non-ASCII letters that look like ASCII (homoglyph confusables).
_HOMOGLYPHS = {
    "\u0430", "\u0435", "\u043E", "\u0440", "\u0441", "\u0445", "\u0443",
    "\u0410", "\u0415", "\u041E", "\u0420", "\u0421", "\u0425",
    "\u0391", "\u0392", "\u0395", "\u039F", "\u03A1", "\u03A4",
    "\u03B1", "\u03BF", "\u03C1", "\u03BD",
}


# --------------------------------------------------------------------------- #
# Scanning
# --------------------------------------------------------------------------- #
def _scan_field(field_name: str, text: str) -> List[Finding]:
    """Run all detectors on a single text field."""
    findings: List[Finding] = []
    if not text:
        return findings

    for rule, severity, pattern, message in _TEXT_RULES:
        m = pattern.search(text)
        if m:
            findings.append(
                Finding(
                    rule=rule,
                    severity=severity,
                    field=field_name,
                    message=message,
                    evidence=_snippet(text, m.start(), m.end()),
                )
            )

    # Invisible / bidi control characters.
    invisibles = sorted({ch for ch in text if ch in _INVISIBLE_CHARS})
    if invisibles:
        names = ", ".join(f"U+{ord(c):04X} {_INVISIBLE_CHARS[c]}" for c in invisibles)
        findings.append(
            Finding(
                rule="invisible_characters",
                severity="high",
                field=field_name,
                message=f"Hidden zero-width/bidi control characters: {names}.",
                evidence=repr(text[:80]),
            )
        )

    # Homoglyph letters embedded in otherwise-ASCII text.
    homos = sorted({ch for ch in text if ch in _HOMOGLYPHS})
    if homos:
        names = ", ".join(
            f"U+{ord(c):04X} {unicodedata.name(c, 'UNKNOWN')}" for c in homos
        )
        findings.append(
            Finding(
                rule="homoglyphs",
                severity="high",
                field=field_name,
                message=f"Non-ASCII homoglyph letters mixed into text: {names}.",
                evidence=repr("".join(homos)),
            )
        )

    return findings


def _snippet(text: str, start: int, end: int, pad: int = 30) -> str:
    lo = max(0, start - pad)
    hi = min(len(text), end + pad)
    return ("..." if lo else "") + text[lo:hi].replace("\n", " ") + ("..." if hi < len(text) else "")


def scan_skill(entry: Dict[str, object]) -> SkillReport:
    """Scan the routing-visible fields of one catalog entry."""
    report = SkillReport(
        id=str(entry.get("id") or entry.get("name") or "<unknown>"),
        name=str(entry.get("name") or ""),
        path=(str(entry["path"]) if entry.get("path") else None),
    )
    # Fields the router actually reads. `description` is the primary surface.
    for field_name in ("name", "description"):
        report.findings.extend(_scan_field(field_name, str(entry.get(field_name) or "")))
    return report


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
def _load_from_catalog(catalog_path: Path) -> List[Dict[str, object]]:
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("catalog.json must be a JSON array")
    return [e for e in raw if isinstance(e, dict)]


def _parse_frontmatter(md_text: str) -> Dict[str, str]:
    """Minimal YAML-frontmatter extractor for name/description (no yaml dep)."""
    if not md_text.startswith("---"):
        return {}
    end = md_text.find("\n---", 3)
    if end == -1:
        return {}
    block = md_text[3:end]
    out: Dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            key, _, val = line.partition(":")
            out[key.strip().lower()] = val.strip().strip("'\"")
    return out


def _load_from_dir(skills_dir: Path) -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    for md in sorted(skills_dir.rglob("SKILL.md")):
        fm = _parse_frontmatter(md.read_text(encoding="utf-8", errors="replace"))
        entries.append(
            {
                "id": fm.get("name") or md.parent.name,
                "name": fm.get("name") or md.parent.name,
                "description": fm.get("description", ""),
                "path": str(md),
            }
        )
    return entries


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def _evidence_sha256(finding: Finding) -> str:
    return hashlib.sha256(finding.evidence.encode("utf-8")).hexdigest()


def _apply_allowlist(
    reports: List[SkillReport], allowlist_path: Optional[Path]
) -> List[Dict[str, str]]:
    """Remove only exact, content-addressed exceptions from the blocking set.

    Every exception binds a skill id, scanner rule, and SHA-256 of the scanner's
    evidence snippet. A changed description therefore invalidates the exception
    instead of silently inheriting an old approval.
    """
    if allowlist_path is None:
        return []

    raw = json.loads(allowlist_path.read_text(encoding="utf-8"))
    if (
        not isinstance(raw, dict)
        or raw.get("schema_version") != 1
        or not isinstance(raw.get("entries"), list)
    ):
        raise ValueError("allowlist must have schema_version=1 and an entries array")

    allowed: Dict[tuple[str, str, str], Dict[str, object]] = {}
    for index, entry in enumerate(raw["entries"]):
        if not isinstance(entry, dict):
            raise ValueError(f"allowlist entry {index} must be an object")
        key = (
            str(entry.get("skill_id") or ""),
            str(entry.get("rule") or ""),
            str(entry.get("evidence_sha256") or ""),
        )
        if not all(key):
            raise ValueError(
                f"allowlist entry {index} requires skill_id, rule, and evidence_sha256"
            )
        if not re.fullmatch(r"[0-9a-f]{64}", key[2]):
            raise ValueError(f"allowlist entry {index} has an invalid evidence_sha256")
        if key in allowed:
            raise ValueError(f"duplicate allowlist entry: {key[0]} / {key[1]}")
        allowed[key] = entry

    matched: set[tuple[str, str, str]] = set()
    applied: List[Dict[str, str]] = []
    for report in reports:
        retained: List[Finding] = []
        for finding in report.findings:
            digest = _evidence_sha256(finding)
            key = (report.id, finding.rule, digest)
            entry = allowed.get(key)
            if entry is None:
                retained.append(finding)
                continue
            matched.add(key)
            applied.append(
                {
                    "skill_id": report.id,
                    "rule": finding.rule,
                    "severity": finding.severity,
                    "evidence_sha256": digest,
                    "reason": str(entry.get("reason") or ""),
                    "reviewed_on": str(entry.get("reviewed_on") or ""),
                }
            )
        report.findings = retained

    stale = sorted(set(allowed) - matched)
    if stale:
        rendered = ", ".join(f"{skill_id}/{rule}" for skill_id, rule, _ in stale)
        raise ValueError(f"stale allowlist entries did not match current findings: {rendered}")
    return applied


def build_report(
    reports: List[SkillReport], allowlisted: Optional[List[Dict[str, str]]] = None
) -> Dict[str, object]:
    counts = {"low": 0, "medium": 0, "high": 0}
    flagged = []
    for r in reports:
        if not r.findings:
            continue
        for f in r.findings:
            counts[f.severity] += 1
        flagged.append(
            {
                "id": r.id,
                "name": r.name,
                "path": r.path,
                "max_severity": r.max_severity,
                "findings": [asdict(f) for f in r.findings],
            }
        )
    return {
        "scanned": len(reports),
        "flagged": len(flagged),
        "severity_counts": counts,
        "skills": flagged,
        "allowlisted": allowlisted or [],
    }


def _print_human(report: Dict[str, object]) -> None:
    print(
        f"Scanned {report['scanned']} skills — {report['flagged']} flagged "
        f"(high={report['severity_counts']['high']}, "
        f"medium={report['severity_counts']['medium']}, "
        f"low={report['severity_counts']['low']}); "
        f"{len(report.get('allowlisted', []))} exact finding(s) allowlisted\n"
    )
    for skill in report["skills"]:  # type: ignore[index]
        print(f"[{skill['max_severity'].upper()}] {skill['name']}  ({skill['id']})")
        if skill["path"]:
            print(f"   {skill['path']}")
        for f in skill["findings"]:
            print(f"   - {f['severity'].upper():6} {f['rule']} in {f['field']}: {f['message']}")
            print(f"           evidence: {f['evidence']}")
        print()
    if not report["skills"]:
        print("No suspicious patterns found. ✓")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scan skill frontmatter for router-hijack / injection.")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--catalog", type=Path, help="Path to catalog.json.")
    src.add_argument("--skills-dir", type=Path, help="Directory tree of SKILL.md files.")
    p.add_argument("--json", type=Path, default=None, help="Write JSON report to this path.")
    p.add_argument(
        "--allowlist",
        type=Path,
        default=None,
        help=(
            "JSON file of exact skill_id/rule/evidence_sha256 exceptions. "
            "Stale or duplicate entries fail the scan."
        ),
    )
    p.add_argument(
        "--fail-on",
        choices=("low", "medium", "high", "never"),
        default="high",
        help="Minimum severity that makes the scan exit non-zero (default: high).",
    )
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        if args.catalog:
            entries = _load_from_catalog(args.catalog)
        else:
            if not args.skills_dir.is_dir():
                print(f"error: not a directory: {args.skills_dir}", file=sys.stderr)
                return 1
            entries = _load_from_dir(args.skills_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: could not load input: {exc}", file=sys.stderr)
        return 1

    reports = [scan_skill(e) for e in entries]
    try:
        allowlisted = _apply_allowlist(reports, args.allowlist)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: invalid allowlist: {exc}", file=sys.stderr)
        return 1
    report = build_report(reports, allowlisted)

    _print_human(report)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nJSON report written to {args.json}")

    # Gate.
    if args.fail_on == "never":
        return 0
    threshold = SEVERITY_ORDER[args.fail_on]
    worst = max(
        (SEVERITY_ORDER[f["severity"]] for s in report["skills"] for f in s["findings"]),
        default=-1,
    )
    if worst >= threshold:
        print(
            f"\nFAIL: findings at or above '{args.fail_on}' severity present.",
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
