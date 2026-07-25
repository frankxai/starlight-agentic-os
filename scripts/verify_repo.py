#!/usr/bin/env python3
"""Fail-closed verification for the Starlight Agentic OS command center."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
INSTALL_STATES = {"done", "partial", "todo"}
IMPROVE_STATES = {"done", "in-progress", "todo", "deprecate-candidate"}
INDEXED_STATES = {"done", "in-progress", "todo"}
REQUIRED_PATHS = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "STRATEGY.md",
    "ROADMAP.md",
    "registry.yaml",
    "index/catalog.json",
    "index/security-scan-report.json",
    "index/security-allowlist.json",
    "mcp-server/server.py",
    "mcp-server/server.json",
    "mcp-server/pyproject.toml",
    "mcp-server/catalog.json",
    "mcp-server/scan_skill_frontmatter.py",
    "mcp-server/security-allowlist.json",
    ".github/workflows/verify.yml",
)


class Verification:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.receipts: list[str] = []

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def receipt(self, message: str) -> None:
        self.receipts.append(message)


def _load_json(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _load_registry() -> dict[str, Any]:
    value = yaml.safe_load((ROOT / "registry.yaml").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("registry.yaml must contain a mapping")
    return value


def verify_required_paths(v: Verification) -> None:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).is_file()]
    v.require(not missing, f"required repository paths missing: {missing}")
    if not missing:
        v.receipt(f"required paths: {len(REQUIRED_PATHS)}/{len(REQUIRED_PATHS)}")


def verify_registry(v: Verification, registry: dict[str, Any]) -> None:
    v.require(registry.get("meta", {}).get("schema_version") == 1, "registry schema_version must be 1")
    packs = registry.get("packs")
    v.require(isinstance(packs, list) and bool(packs), "registry packs must be a non-empty array")
    if not isinstance(packs, list):
        return

    names: list[str] = []
    for index, pack in enumerate(packs):
        if not isinstance(pack, dict):
            v.errors.append(f"registry pack {index} must be an object")
            continue
        name = str(pack.get("name") or "")
        names.append(name)
        prefix = f"pack {name or index}"
        v.require(bool(name), f"{prefix}: name is required")
        version = str(pack.get("version") or "")
        v.require(bool(SEMVER.fullmatch(version)), f"{prefix}: invalid semver {version!r}")
        v.require(
            pack.get("origin") in {"original", "absorbed", "forked"},
            f"{prefix}: invalid origin {pack.get('origin')!r}",
        )
        status = pack.get("status")
        if not isinstance(status, dict):
            v.errors.append(f"{prefix}: status must be an object")
            continue
        v.require(status.get("install") in INSTALL_STATES, f"{prefix}: invalid install state")
        v.require(status.get("improve") in IMPROVE_STATES, f"{prefix}: invalid improve state")
        v.require(status.get("indexed") in INDEXED_STATES, f"{prefix}: invalid indexed state")
        if status.get("improve") in {"in-progress", "done", "deprecate-candidate"}:
            v.require(
                status.get("install") == "done",
                f"{prefix}: improve work requires install=done",
            )
        if status.get("indexed") in {"in-progress", "done"}:
            v.require(
                status.get("improve") == "done",
                f"{prefix}: indexed work requires improve=done",
            )
        registered = status.get("registered")
        v.require(
            isinstance(registered, list)
            and all(isinstance(item, str) and item for item in registered),
            f"{prefix}: registered must be an array of non-empty strings",
        )
        if status.get("improve") == "done":
            v.require(
                bool(pack.get("improve_note")),
                f"{prefix}: improve=done requires an inspectable improve_note",
            )
            provenance = pack.get("provenance")
            checksum = provenance.get("checksum") if isinstance(provenance, dict) else None
            v.require(
                isinstance(checksum, str)
                and bool(re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", checksum)),
                f"{prefix}: improve=done requires a SHA-256 provenance checksum",
            )
            receipts = pack.get("improve_receipts")
            v.require(
                isinstance(receipts, dict)
                and all(
                    isinstance(receipts.get(key), str) and bool(receipts.get(key))
                    for key in ("eval", "safety", "observability")
                ),
                f"{prefix}: improve=done requires eval, safety, and observability receipts",
            )
        if registered:
            v.require(
                status.get("indexed") == "done",
                f"{prefix}: registered packs must already be indexed=done",
            )

    duplicates = sorted({name for name in names if names.count(name) > 1})
    v.require(not duplicates, f"duplicate registry pack names: {duplicates}")
    v.receipt(f"registry packs: {len(packs)}; unique names: {len(set(names))}")


def verify_catalog(v: Verification) -> int:
    catalog = _load_json("index/catalog.json")
    v.require(isinstance(catalog, list), "index/catalog.json must be an array")
    if not isinstance(catalog, list):
        return 0

    ids: list[str] = []
    unsafe_paths: list[str] = []
    for index, skill in enumerate(catalog):
        if not isinstance(skill, dict):
            v.errors.append(f"catalog entry {index} must be an object")
            continue
        skill_id = str(skill.get("id") or "")
        ids.append(skill_id)
        v.require(bool(skill_id), f"catalog entry {index} requires id")
        v.require(bool(skill.get("name")), f"catalog entry {skill_id or index} requires name")
        v.require(
            isinstance(skill.get("description"), str),
            f"catalog entry {skill_id or index} requires string description",
        )
        for field in ("path", "body_path"):
            value = skill.get(field)
            if not isinstance(value, str) or not value:
                continue
            posix = value.replace("\\", "/")
            if (
                PurePosixPath(posix).is_absolute()
                or re.match(r"^[A-Za-z]:/", posix)
                or posix.startswith(("~/", "/home/", "/Users/", "/root/"))
            ):
                unsafe_paths.append(f"{skill_id}:{field}={value}")

    duplicates = sorted({skill_id for skill_id in ids if ids.count(skill_id) > 1})
    v.require(not duplicates, f"duplicate catalog ids: {duplicates[:20]}")
    v.require(not unsafe_paths, f"catalog leaks host-absolute paths: {unsafe_paths[:20]}")
    v.receipt(f"catalog skills: {len(catalog)}; unique ids: {len(set(ids))}; host paths: 0")
    return len(catalog)


def verify_security_scan(v: Verification, catalog_count: int) -> None:
    committed = _load_json("index/security-scan-report.json")
    v.require(
        committed.get("scanned") == catalog_count,
        "committed security scan count does not match catalog",
    )

    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "scan.json"
        command = [
            sys.executable,
            str(ROOT / "index/scan_skill_frontmatter.py"),
            "--catalog",
            str(ROOT / "index/catalog.json"),
            "--allowlist",
            str(ROOT / "index/security-allowlist.json"),
            "--json",
            str(output),
            "--fail-on",
            "high",
        ]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        v.require(
            result.returncode == 0,
            "security scan failed:\n" + (result.stdout + result.stderr).strip(),
        )
        if result.returncode != 0 or not output.exists():
            return
        live = json.loads(output.read_text(encoding="utf-8"))
        v.require(live.get("scanned") == catalog_count, "live security scan count drifted")
        v.require(
            live.get("severity_counts", {}).get("high") == 0,
            "unallowlisted high-severity findings remain",
        )
        v.receipt(
            "security scan: "
            f"{live.get('scanned')} scanned; "
            f"{live.get('severity_counts', {}).get('high')} unallowlisted high; "
            f"{len(live.get('allowlisted', []))} exact exception"
        )


def verify_mcp_contract(v: Verification, registry: dict[str, Any]) -> None:
    server_json = _load_json("mcp-server/server.json")
    pyproject = tomllib.loads((ROOT / "mcp-server/pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject.get("project", {})
    version = str(project.get("version") or "")
    packages = server_json.get("packages") or []
    package_version = packages[0].get("version") if packages and isinstance(packages[0], dict) else None
    registry_pack = next(
        (pack for pack in registry.get("packs", []) if pack.get("name") == "starlight-skill-index"),
        None,
    )

    v.require(server_json.get("version") == version, "server.json and pyproject versions differ")
    v.require(package_version == version, "server package and pyproject versions differ")
    v.require(
        registry_pack is not None and registry_pack.get("version") == version,
        "registry and MCP package versions differ",
    )
    repository = server_json.get("repository") or {}
    v.require(
        repository.get("url") == "https://github.com/frankxai/starlight-agentic-os",
        "server.json repository URL is not canonical",
    )
    v.require(repository.get("subfolder") == "mcp-server", "server.json subfolder must be mcp-server")
    urls = project.get("urls") or {}
    v.require(
        urls.get("Repository")
        == "https://github.com/frankxai/starlight-agentic-os/tree/main/mcp-server",
        "pyproject Repository URL is not canonical",
    )
    v.receipt(f"MCP version alignment: {version}")


def verify_mcp_assets(v: Verification) -> None:
    pairs = (
        ("index/catalog.json", "mcp-server/catalog.json"),
        ("index/scan_skill_frontmatter.py", "mcp-server/scan_skill_frontmatter.py"),
        ("index/security-allowlist.json", "mcp-server/security-allowlist.json"),
    )
    drifted = [
        f"{source} != {mirror}"
        for source, mirror in pairs
        if (ROOT / source).read_bytes() != (ROOT / mirror).read_bytes()
    ]
    v.require(not drifted, f"generated MCP package assets are stale: {drifted}")
    if not drifted:
        v.receipt(f"MCP package assets: {len(pairs)}/{len(pairs)} synchronized")


def verify_readme(v: Verification) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/gen_readme.py"), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    v.require(
        result.returncode == 0,
        "generated README matrix is stale:\n" + (result.stdout + result.stderr).strip(),
    )
    if result.returncode == 0:
        v.receipt("README matrix: current")


def main() -> int:
    verification = Verification()
    try:
        verify_required_paths(verification)
        registry = _load_registry()
        verify_registry(verification, registry)
        catalog_count = verify_catalog(verification)
        verify_security_scan(verification, catalog_count)
        verify_mcp_contract(verification, registry)
        verify_mcp_assets(verification)
        verify_readme(verification)
    except (OSError, ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError, yaml.YAMLError) as exc:
        verification.errors.append(f"verification crashed while reading repository state: {exc}")

    for receipt in verification.receipts:
        print(f"PASS {receipt}")
    if verification.errors:
        for error in verification.errors:
            print(f"FAIL {error}", file=sys.stderr)
        print(f"\nRepository contract: BLOCK ({len(verification.errors)} failure(s))", file=sys.stderr)
        return 1
    print("\nRepository contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
