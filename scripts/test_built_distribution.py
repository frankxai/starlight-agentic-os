#!/usr/bin/env python3
"""Prove the built wheel works without source-tree paths or env overrides."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "mcp-server/dist"
VERSION = "0.1.1"


def _python_for(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts/python.exe"
    return environment / "bin/python"


def _fail(message: str) -> int:
    print(f"BLOCK {message}", file=sys.stderr)
    return 1


def main() -> int:
    wheels = sorted(DIST.glob("starlight_skill_index-*.whl"))
    sdists = sorted(DIST.glob("starlight_skill_index-*.tar.gz"))
    if len(wheels) != 1:
        return _fail(f"expected exactly one wheel in {DIST}, found {len(wheels)}")
    if len(sdists) != 1:
        return _fail(f"expected exactly one sdist in {DIST}, found {len(sdists)}")
    wheel = wheels[0].resolve()
    sdist = sdists[0].resolve()

    expected_assets = {
        "catalog.json": ROOT / "index/catalog.json",
        "scan_skill_frontmatter.py": ROOT / "index/scan_skill_frontmatter.py",
        "security-allowlist.json": ROOT / "index/security-allowlist.json",
    }
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        metadata = [
            name
            for name in names
            if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata) != 1:
            return _fail("wheel must contain exactly one METADATA file")
        metadata_text = archive.read(metadata[0]).decode("utf-8")
        if f"Version: {VERSION}\n" not in metadata_text:
            return _fail(f"wheel metadata does not declare version {VERSION}")
        for filename, source in expected_assets.items():
            if filename not in names:
                return _fail(f"wheel is missing {filename}")
            if archive.read(filename) != source.read_bytes():
                return _fail(f"wheel {filename} differs from its canonical source")

    sdist_sources = {
        "server.json": ROOT / "mcp-server/server.json",
        **expected_assets,
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
                return _fail(f"sdist expected one {filename}, found {len(matches)}")
            extracted = archive.extractfile(matches[0])
            if extracted is None or extracted.read() != source.read_bytes():
                return _fail(f"sdist {filename} differs from its verified source")

    with tempfile.TemporaryDirectory(
        prefix="starlight-wheel-smoke-"
    ) as directory:
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
            check=False,
        )
        if install.returncode != 0:
            print(install.stdout + install.stderr, file=sys.stderr)
            return _fail("wheel installation failed")

        program = r"""
import json
import server

catalog = server.load_catalog()
search = server.run_search_skills("review a github pull request", k=3)
security = server.run_security_report()
print(json.dumps({
    "version": server.SERVER_VERSION,
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
            check=False,
        )
        if smoke.returncode != 0:
            print(smoke.stdout + smoke.stderr, file=sys.stderr)
            return _fail("installed wheel execution failed")
        try:
            receipt = json.loads(smoke.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError) as exc:
            print(smoke.stdout + smoke.stderr, file=sys.stderr)
            return _fail(f"invalid smoke-test receipt: {exc}")

    expected_catalog = json.loads(
        (ROOT / "index/catalog.json").read_text(encoding="utf-8")
    )
    expected_allowlist = json.loads(
        (ROOT / "index/security-allowlist.json").read_text(encoding="utf-8")
    )
    checks = {
        "installed version matches candidate": receipt["version"] == VERSION,
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
        "wheel and sdist assets match canonical sources": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    if failed:
        return _fail(f"installed distribution has {len(failed)} failure(s)")
    print("\nInstalled distribution: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
