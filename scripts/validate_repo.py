#!/usr/bin/env python3
"""Deterministic repository and lifecycle truth gate."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml
from jsonschema import Draft7Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
MCP_SCHEMA_PATH = ROOT / "schemas/mcp-server-2025-12-11.schema.json"
MCP_SCHEMA_SHA256 = "6fcf2f679ccf47ee5d6f578a8e87c2980b929c696cbc878a48cde7cc9b549506"
REQUIRED = [
    ".agent-harness.json",
    "AGENTS.md",
    "SYSTEM.md",
    "SCHEMA.md",
    "SKILLS.md",
    "RUNBOOK.md",
    "TESTING.md",
    "SECURITY.md",
    "README.md",
    "registry.yaml",
    "mcp-server/server.json",
    "mcp-server/pyproject.toml",
    "mcp-server/README.md",
    "requirements-dev.txt",
    "schemas/README.md",
    "schemas/mcp-server-2025-12-11.schema.json",
    "scripts/verify_certifications.py",
]
INSTALL = {"todo", "partial", "done"}
IMPROVE = {"todo", "in-progress", "done", "deprecate-candidate"}
INDEXED = {"todo", "in-progress", "done"}
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
MCP_NAME = re.compile(r"^[a-zA-Z0-9.-]+/[a-zA-Z0-9._-]+$")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def lifecycle_failures(name: str, status: dict) -> list[str]:
    """Enforce install → improve → indexed → registered without shortcuts."""
    failures: list[str] = []
    install = status.get("install")
    improve = status.get("improve")
    indexed = status.get("indexed")
    registered = status.get("registered")

    if install not in INSTALL:
        failures.append(f"{name}: invalid install state")
    if improve not in IMPROVE:
        failures.append(f"{name}: invalid improve state")
    if indexed not in INDEXED:
        failures.append(f"{name}: invalid indexed state")
    if not isinstance(registered, list):
        failures.append(f"{name}: registered must be a list")
        registered = []

    if improve in {"in-progress", "done", "deprecate-candidate"} and install != "done":
        failures.append(f"{name}: improve requires install=done")
    if indexed in {"in-progress", "done"} and improve != "done":
        failures.append(f"{name}: indexed work requires improve=done")
    if registered and indexed != "done":
        failures.append(f"{name}: registration requires indexed=done")
    if registered and (
        any(not isinstance(item, str) or not item.strip() for item in registered)
        or len(registered) != len(set(registered))
    ):
        failures.append(f"{name}: registered entries must be unique non-empty strings")
    return failures


def mcp_schema_failures(manifest: dict) -> list[str]:
    """Validate the complete manifest against the pinned official Draft 7 schema."""
    schema_bytes = MCP_SCHEMA_PATH.read_bytes()
    actual_sha = hashlib.sha256(schema_bytes).hexdigest()
    if actual_sha != MCP_SCHEMA_SHA256:
        return [
            "pinned MCP schema digest changed; review upstream provenance and update the pin"
        ]
    schema = json.loads(schema_bytes)
    Draft7Validator.check_schema(schema)
    validator = Draft7Validator(schema, format_checker=FormatChecker())
    failures: list[str] = []
    for error in sorted(validator.iter_errors(manifest), key=lambda item: list(item.path)):
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        failures.append(f"MCP official schema {location}: {error.message}")
    return failures


def main() -> int:
    failures: list[str] = []
    for path in REQUIRED:
        if not (ROOT / path).is_file():
            failures.append(f"missing required file: {path}")

    try:
        registry = yaml.safe_load(read("registry.yaml"))
    except (OSError, yaml.YAMLError) as exc:
        failures.append(f"invalid registry.yaml: {exc}")
        registry = {"packs": []}

    packs = registry.get("packs") or []
    names: set[str] = set()
    for pack in packs:
        name = pack.get("name")
        if not name or name in names:
            failures.append(f"pack name missing or duplicated: {name!r}")
            continue
        names.add(name)
        version = str(pack.get("version", ""))
        if not SEMVER.fullmatch(version):
            failures.append(f"{name}: version is not clean semver: {version}")
        status = pack.get("status") or {}
        failures.extend(lifecycle_failures(name, status))
        provenance = pack.get("provenance") or {}
        if status.get("improve") == "done":
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(provenance.get("checksum"))):
                failures.append(f"{name}: improve=done requires a SHA-256 checksum")
            if not provenance.get("certification"):
                failures.append(f"{name}: improve=done requires a certification path")
        if status.get("registered") and not provenance.get("last_reviewed"):
            failures.append(f"{name}: registered entries require last_reviewed")

    server = json.loads(read("mcp-server/server.json"))
    failures.extend(mcp_schema_failures(server))
    project = tomllib.loads(read("mcp-server/pyproject.toml"))["project"]
    skill_pack = next((pack for pack in packs if pack.get("name") == "starlight-skill-index"), None)
    expected_schema = (
        "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json"
    )
    if server.get("$schema") != expected_schema:
        failures.append("mcp-server/server.json must use the current stable 2025-12-11 schema")
    if "status" in server:
        failures.append("mcp-server/server.json contains registry-managed status")
    server_name = str(server.get("name", ""))
    if not MCP_NAME.fullmatch(server_name) or len(server_name) > 200:
        failures.append("MCP server name violates the official schema")
    if server_name != "io.github.frankxai/starlight-skill-index":
        failures.append("MCP server name is not the owned namespace")
    title = str(server.get("title", ""))
    if not title or len(title) > 100:
        failures.append("MCP server title must contain 1-100 characters")
    description = str(server.get("description", ""))
    if not description or len(description) > 100:
        failures.append("MCP server description must contain 1-100 characters")
    server_version = str(server.get("version", ""))
    if not server_version or len(server_version) > 255 or server_version == "latest":
        failures.append("MCP server version violates the official schema")
    if server.get("repository", {}).get("url") != "https://github.com/frankxai/starlight-agentic-os":
        failures.append("MCP manifest repository URL is not canonical")
    for index, package in enumerate(server.get("packages") or []):
        if not all(package.get(key) for key in ("registryType", "identifier", "transport")):
            failures.append(f"MCP package[{index}] lacks a required registry identity or transport")
        transport = package.get("transport") or {}
        if transport.get("type") not in {"stdio", "sse", "streamable-http"}:
            failures.append(f"MCP package[{index}] has an invalid transport")
    if skill_pack:
        versions = {
            str(server.get("version")),
            str(project.get("version")),
            str(skill_pack.get("version")),
        }
        if len(versions) != 1:
            failures.append(f"router version drift: {sorted(versions)}")
    urls = project.get("urls") or {}
    for key, url in urls.items():
        if "frankxai/starlight-agentic-os" not in str(url):
            failures.append(f"pyproject URL {key} points outside the canonical repository")
    ownership_token = "<!-- mcp-name: io.github.frankxai/starlight-skill-index -->"
    if ownership_token not in read("mcp-server/README.md"):
        failures.append("PyPI README lacks the MCP Registry ownership token")

    workflows = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / ".github/workflows").glob("*.yml"))
    )
    if "|| true" in workflows:
        failures.append("workflow ignores a command failure with `|| true`")
    if re.search(r'echo\s+["\']?TODO', workflows):
        failures.append("workflow can report success by echoing a TODO")

    generated = subprocess.run(
        [sys.executable, "scripts/gen_readme.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if generated.returncode != 0:
        failures.append("README status matrix is stale")

    harness = json.loads(read(".agent-harness.json"))
    if harness.get("repo", {}).get("canonical_source", {}).get("ref") != (
        "frankxai/starlight-agentic-os"
    ):
        failures.append("agent harness canonical repository is wrong")
    if harness.get("delivery", {}).get("promotion_policy") != (
        "independent-verifier-and-named-human-approval"
    ):
        failures.append("agent harness promotion policy is not fail-closed")

    if failures:
        print(f"Repository validation failed ({len(failures)}):", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(f"Repository valid: {len(packs)} packs, lifecycle and MCP identities coherent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
