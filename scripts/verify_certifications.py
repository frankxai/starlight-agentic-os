#!/usr/bin/env python3
"""Verify exact-pack certification receipts against Git and registry truth."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

try:
    from .pack_digest import digest_directory
except ImportError:  # direct script execution
    from pack_digest import digest_directory

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry.yaml"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
EVIDENCE_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def load_registry() -> dict:
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


def repo_path(value: object, label: str, expected: str) -> tuple[Path, str]:
    """Resolve a repository-relative path without traversal or symlink indirection."""
    raw = Path(str(value))
    if raw.is_absolute() or not raw.parts or any(part in {"", ".", ".."} for part in raw.parts):
        raise ValueError(f"{label} must be a clean repository-relative path")

    cursor = ROOT
    for part in raw.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"{label} must not traverse a symlink")
    try:
        resolved = cursor.resolve(strict=True)
        resolved.relative_to(ROOT.resolve(strict=True))
    except (FileNotFoundError, ValueError):
        raise ValueError(f"{label} is missing or escapes the repository") from None
    if expected == "file" and not resolved.is_file():
        raise ValueError(f"{label} is not a file")
    if expected == "directory" and not resolved.is_dir():
        raise ValueError(f"{label} is not a directory")
    return resolved, raw.as_posix()


def evidence_failures(receipt: dict, source_commit: str) -> list[str]:
    """Validate v2 eval, safety, and observability evidence by exact bytes."""
    evidence = receipt.get("evidence")
    if not isinstance(evidence, dict):
        return ["receipt v2 requires an evidence object"]

    failures: list[str] = []
    for evidence_class in ("eval", "safety", "observability"):
        item = evidence.get(evidence_class)
        if not isinstance(item, dict):
            failures.append(f"receipt evidence.{evidence_class} must be an object")
            continue
        declared = str(item.get("sha256") or "")
        if not EVIDENCE_SHA_RE.fullmatch(declared):
            failures.append(
                f"receipt evidence.{evidence_class}.sha256 is not a SHA-256 digest"
            )
            continue
        try:
            evidence_file, relative = repo_path(
                item.get("path"),
                f"receipt evidence.{evidence_class}",
                "file",
            )
        except ValueError as exc:
            failures.append(str(exc))
            continue
        actual = hashlib.sha256(evidence_file.read_bytes()).hexdigest()
        if actual != declared:
            failures.append(
                f"receipt evidence.{evidence_class} does not match its SHA-256"
            )
        tracked = git("ls-tree", "--name-only", "HEAD", "--", relative)
        if tracked.returncode != 0 or tracked.stdout.strip() != relative:
            failures.append(f"receipt evidence.{evidence_class} is not committed")
        if (
            SHA_RE.fullmatch(source_commit)
            and git("cat-file", "-e", f"{source_commit}:{relative}").returncode == 0
        ):
            failures.append(
                f"receipt evidence.{evidence_class} already existed at source_commit"
            )
    return failures


def verify_pack(pack: dict) -> list[str]:
    failures: list[str] = []
    name = pack["name"]
    provenance = pack.get("provenance") or {}
    receipt_path = provenance.get("certification")
    checksum = provenance.get("checksum")
    if not receipt_path:
        return [f"{name}: improve=done requires provenance.certification"]
    try:
        receipt_file, receipt_relative = repo_path(
            receipt_path, f"{name}: certification receipt", "file"
        )
    except ValueError as exc:
        return [str(exc)]

    try:
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{name}: invalid certification JSON: {exc}"]

    required = {
        "schema_version",
        "pack",
        "version",
        "repository",
        "artifact_root",
        "source_commit",
        "artifact",
        "tests",
        "maker",
        "verifier",
        "verified_at",
        "verdict",
    }
    missing = sorted(required - receipt.keys())
    if missing:
        failures.append(f"{name}: receipt missing {', '.join(missing)}")
        return failures

    schema_version = receipt["schema_version"]
    if schema_version not in {
        "starlight.pack_certification.v1",
        "starlight.pack_certification.v2",
    }:
        failures.append(f"{name}: unsupported certification schema")
    if receipt["pack"] != name or receipt["version"] != str(pack["version"]):
        failures.append(f"{name}: receipt pack/version does not match registry")
    if receipt["repository"] != pack["repo"]:
        failures.append(f"{name}: receipt repository does not match registry")
    if receipt["maker"] == receipt["verifier"]:
        failures.append(f"{name}: maker and verifier must be distinct")
    if receipt["verdict"] != "pass":
        failures.append(f"{name}: certification verdict is not pass")
    try:
        verified_at = datetime.fromisoformat(
            str(receipt["verified_at"]).replace("Z", "+00:00")
        )
        if verified_at.tzinfo is None:
            raise ValueError
    except ValueError:
        failures.append(f"{name}: verified_at must be timezone-aware ISO-8601")

    source_commit = str(receipt["source_commit"])
    if not SHA_RE.fullmatch(source_commit):
        failures.append(f"{name}: source_commit is not a full Git SHA")
    elif git("cat-file", "-e", f"{source_commit}^{{commit}}").returncode != 0:
        failures.append(f"{name}: source_commit is not present in Git")
    else:
        head = git("rev-parse", "HEAD").stdout.strip()
        if source_commit == head:
            failures.append(f"{name}: receipt must be committed after source_commit")
        if git("merge-base", "--is-ancestor", source_commit, "HEAD").returncode != 0:
            failures.append(f"{name}: source_commit is not an ancestor of receipt HEAD")
        if git("cat-file", "-e", f"{source_commit}:{receipt_relative}").returncode == 0:
            failures.append(f"{name}: receipt already existed at source_commit")
        tracked = git("ls-tree", "--name-only", "HEAD", "--", receipt_relative)
        if tracked.returncode != 0 or tracked.stdout.strip() != receipt_relative:
            failures.append(f"{name}: receipt is not committed at HEAD")

    if schema_version == "starlight.pack_certification.v2":
        failures.extend(f"{name}: {failure}" for failure in evidence_failures(
            receipt, source_commit
        ))

    try:
        artifact_root, artifact_relative = repo_path(
            receipt["artifact_root"], f"{name}: artifact_root", "directory"
        )
        actual = digest_directory(artifact_root)
    except ValueError as exc:
        failures.append(f"{name}: {exc}")
        actual = None
    if actual and actual != receipt["artifact"]:
        failures.append(f"{name}: current artifact bytes do not match receipt")
    if actual and checksum != f"sha256:{actual['sha256']}":
        failures.append(f"{name}: registry checksum does not match artifact")

    if SHA_RE.fullmatch(source_commit) and actual:
        unchanged = git("diff", "--quiet", source_commit, "--", artifact_relative)
        if unchanged.returncode != 0:
            failures.append(
                f"{name}: artifact changed after source_commit; recertify current bytes"
            )

    tests = receipt.get("tests")
    if not isinstance(tests, list) or not tests:
        failures.append(f"{name}: receipt requires at least one test result")
    else:
        for index, result in enumerate(tests):
            if not isinstance(result, dict):
                failures.append(f"{name}: tests[{index}] is not an object")
                continue
            if not result.get("command") or result.get("exit_code") != 0:
                failures.append(f"{name}: tests[{index}] is not a passing command")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="verify every improve=done pack")
    parser.add_argument("pack", nargs="?")
    args = parser.parse_args()
    data = load_registry()
    packs = data.get("packs", [])
    if args.pack:
        packs = [pack for pack in packs if pack["name"] == args.pack]
        if not packs:
            sys.exit(f"unknown pack: {args.pack}")
    elif args.all:
        packs = [pack for pack in packs if pack["status"].get("improve") == "done"]
        if not packs:
            print(
                "Certification verification failed (1):\n"
                "- no pack has improve=done; --all may not pass vacuously",
                file=sys.stderr,
            )
            return 1
    else:
        parser.error("pass --all or a pack name")

    failures: list[str] = []
    for pack in packs:
        failures.extend(verify_pack(pack))
    if failures:
        print(f"Certification verification failed ({len(failures)}):", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(f"Certifications valid: {len(packs)} pack(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
