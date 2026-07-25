#!/usr/bin/env python3
"""Compute a stable SHA-256 digest for one pack directory."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

IGNORED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "dist",
    "build",
}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def digest_directory(root: Path) -> dict[str, object]:
    root = root.expanduser()
    if root.is_symlink():
        raise ValueError(f"artifact root must not be a symlink: {root}")
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"artifact root is not a directory: {root}")

    digest = hashlib.sha256()
    file_count = 0
    byte_count = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"artifact root contains a symlink: {path.relative_to(root)}")
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        data = path.read_bytes()
        encoded_path = relative.as_posix().encode("utf-8")
        digest.update(len(encoded_path).to_bytes(8, "big"))
        digest.update(encoded_path)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
        file_count += 1
        byte_count += len(data)

    if file_count == 0:
        raise ValueError(f"artifact root contains no certifiable files: {root}")
    return {
        "sha256": digest.hexdigest(),
        "file_count": file_count,
        "bytes": byte_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact_root")
    args = parser.parse_args()
    print(json.dumps(digest_directory(Path(args.artifact_root)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
