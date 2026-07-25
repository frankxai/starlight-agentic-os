#!/usr/bin/env python3
"""Prove the built wheel works without source-tree paths or environment overrides."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import tempfile
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "mcp-server/dist"


def _python_for(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts/python.exe"
    return environment / "bin/python"


def main() -> int:
    wheels = sorted(DIST.glob("starlight_skill_index-*.whl"))
    if len(wheels) != 1:
        print(
            f"BLOCK expected exactly one built wheel in {DIST}, found {len(wheels)}",
            file=sys.stderr,
        )
        return 1
    wheel = wheels[0].resolve()
    sdists = sorted(DIST.glob("starlight_skill_index-*.tar.gz"))
    if len(sdists) != 1:
        print(
            f"BLOCK expected exactly one built sdist in {DIST}, found {len(sdists)}",
            file=sys.stderr,
        )
        return 1
    sdist = sdists[0].resolve()

    sdist_sources = {
        "server.json": ROOT / "mcp-server/server.json",
        "server.schema.json": ROOT / "mcp-server/server.schema.json",
        "catalog.json": ROOT / "index/catalog.json",
        "scan_skill_frontmatter.py": ROOT / "index/scan_skill_frontmatter.py",
        "security-allowlist.json": ROOT / "index/security-allowlist.json",
    }
    with tarfile.open(sdist, "r:gz") as archive:
        members = archive.getmembers()
        for filename, source in sdist_sources.items():
            matches = [
                member
                for member in members
                if member.isfile() and member.name.endswith(f"/{filename}")
            ]
            if len(matches) != 1:
                print(
                    f"BLOCK sdist expected one {filename}, found {len(matches)}",
                    file=sys.stderr,
                )
                return 1
            extracted = archive.extractfile(matches[0])
            if extracted is None or extracted.read() != source.read_bytes():
                print(
                    f"BLOCK sdist {filename} differs from its verified source",
                    file=sys.stderr,
                )
                return 1

    with tempfile.TemporaryDirectory(prefix="starlight-wheel-smoke-") as directory:
        temp = Path(directory)
        environment = temp / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _python_for(environment)

        install = subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-deps",
                str(wheel),
            ],
            cwd=temp,
            text=True,
            capture_output=True,
        )
        if install.returncode != 0:
            print("BLOCK wheel installation failed", file=sys.stderr)
            print(install.stdout + install.stderr, file=sys.stderr)
            return 1

        program = r"""
import json
import server

catalog = server.load_catalog()
search = server.run_search_skills("review a github pull request", k=3)
security = server.run_security_report()
print(json.dumps({
    "catalog_path": str(server.resolve_catalog_path() or ""),
    "catalog_count": len(catalog),
    "search_mode": search.get("mode"),
    "search_ids": [item.get("id") for item in search.get("results", [])],
    "security_available": security.get("available"),
    "security_high": security.get("severity_counts", {}).get("high"),
    "allowlisted_count": len(security.get("allowlisted_findings", [])),
}))
"""
        clean_env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("STARLIGHT_") and key != "PYTHONPATH"
        }
        clean_env["PYTHONNOUSERSITE"] = "1"
        smoke = subprocess.run(
            [str(python), "-c", program],
            cwd=temp,
            env=clean_env,
            text=True,
            capture_output=True,
        )
        if smoke.returncode != 0:
            print("BLOCK installed wheel execution failed", file=sys.stderr)
            print(smoke.stdout + smoke.stderr, file=sys.stderr)
            return 1
        try:
            receipt = json.loads(smoke.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError) as exc:
            print(f"BLOCK invalid smoke-test receipt: {exc}", file=sys.stderr)
            print(smoke.stdout + smoke.stderr, file=sys.stderr)
            return 1

    expected_catalog = json.loads(
        (ROOT / "index/catalog.json").read_text(encoding="utf-8")
    )
    expected_allowlist = json.loads(
        (ROOT / "index/security-allowlist.json").read_text(encoding="utf-8")
    )
    checks = {
        "bundled catalog resolved": bool(receipt["catalog_path"]),
        "bundled catalog count matches source": (
            receipt["catalog_count"] == len(expected_catalog)
        ),
        "catalog fallback active": receipt["search_mode"] == "catalog-fallback",
        "search returned results": bool(receipt["search_ids"]),
        "security report available": receipt["security_available"] is True,
        "zero unallowlisted high findings": receipt["security_high"] == 0,
        "allowlisted count matches source": (
            receipt["allowlisted_count"] == len(expected_allowlist["entries"])
        ),
        "sdist publication metadata matches source": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    if failed:
        print(f"\nInstalled distribution: BLOCK ({len(failed)} failure(s))", file=sys.stderr)
        return 1
    print("\nInstalled distribution: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
