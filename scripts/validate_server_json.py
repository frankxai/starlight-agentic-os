#!/usr/bin/env python3
"""Validate server.json against the pinned official MCP registry schema."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, FormatChecker


ROOT = Path(__file__).resolve().parent.parent
SERVER_PATH = ROOT / "mcp-server/server.json"
SCHEMA_PATH = ROOT / "mcp-server/server.schema.json"
SCHEMA_URL = (
    "https://static.modelcontextprotocol.io/schemas/2025-07-09/"
    "server.schema.json"
)
SCHEMA_CANONICAL_SHA256 = (
    "094719a56a9f407b5e4273f8be665f8a5a70a7c4b244369aba8b50ff6910f997"
)


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate() -> list[str]:
    errors: list[str] = []
    try:
        schema = _load_object(SCHEMA_PATH)
        server = _load_object(SERVER_PATH)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [str(exc)]

    if schema.get("$id") != SCHEMA_URL:
        errors.append("vendored schema $id does not match the pinned official URL")
    if _canonical_sha256(schema) != SCHEMA_CANONICAL_SHA256:
        errors.append("vendored official schema content has drifted")
    if server.get("$schema") != SCHEMA_URL:
        errors.append("server.json $schema does not match the pinned official URL")

    validator = Draft7Validator(schema, format_checker=FormatChecker())
    for error in sorted(validator.iter_errors(server), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"{location}: {error.message}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"BLOCK {error}", file=sys.stderr)
        print(f"\nOfficial MCP schema: BLOCK ({len(errors)} failure(s))", file=sys.stderr)
        return 1
    print(f"PASS server.json validates against {SCHEMA_URL}")
    print(f"PASS vendored schema canonical SHA-256 {SCHEMA_CANONICAL_SHA256}")
    print("\nOfficial MCP schema: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
