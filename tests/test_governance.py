from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.pack_digest import digest_directory
from scripts.validate_repo import (
    catalog_failures,
    lifecycle_failures,
    mcp_schema_failures,
)
from scripts.verify_certifications import evidence_failures, repo_path

ROOT = Path(__file__).resolve().parent.parent


class GovernanceTests(unittest.TestCase):
    def test_pack_digest_is_stable_and_ignores_runtime_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").mkdir()
            (root / "a" / "one.txt").write_text("one", encoding="utf-8")
            first = digest_directory(root)
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "one.pyc").write_bytes(b"runtime")
            second = digest_directory(root)
            self.assertEqual(first, second)
            (root / "a" / "one.txt").write_text("two", encoding="utf-8")
            self.assertNotEqual(first["sha256"], digest_directory(root)["sha256"])

    def test_pack_digest_uses_platform_independent_case_sensitive_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {"README.md": b"upper", "catalog.json": b"lower"}
            for relative, data in files.items():
                (root / relative).write_bytes(data)

            expected = hashlib.sha256()
            for relative in sorted(files, key=lambda value: value.encode("utf-8")):
                encoded_path = relative.encode("utf-8")
                data = files[relative]
                expected.update(len(encoded_path).to_bytes(8, "big"))
                expected.update(encoded_path)
                expected.update(len(data).to_bytes(8, "big"))
                expected.update(data)

            self.assertEqual(expected.hexdigest(), digest_directory(root)["sha256"])

    def test_pack_digest_rejects_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root.parent / f"{root.name}-outside.txt"
            outside.write_text("outside", encoding="utf-8")
            junction = None
            outside_dir = None
            try:
                try:
                    os.symlink(outside, root / "escape.txt")
                except OSError as exc:
                    if os.name != "nt" or getattr(exc, "winerror", None) != 1314:
                        raise
                    outside_dir = root.parent / f"{root.name}-outside-dir"
                    outside_dir.mkdir()
                    (outside_dir / "outside.txt").write_text("outside", encoding="utf-8")
                    junction = root / "escape-dir"
                    result = subprocess.run(
                        ["cmd", "/d", "/c", "mklink", "/J", str(junction), str(outside_dir)],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        raise RuntimeError(
                            f"failed to create Windows test junction: {result.stderr.strip()}"
                        ) from exc
                with self.assertRaisesRegex(ValueError, "contains a symlink"):
                    digest_directory(root)
            finally:
                if junction is not None and junction.exists():
                    junction.rmdir()
                if outside_dir is not None:
                    (outside_dir / "outside.txt").unlink(missing_ok=True)
                    outside_dir.rmdir()
                outside.unlink(missing_ok=True)

    def test_lifecycle_cannot_skip_improve(self) -> None:
        failures = lifecycle_failures(
            "unsafe",
            {
                "install": "done",
                "improve": "todo",
                "indexed": "done",
                "registered": [],
            },
        )
        self.assertIn("unsafe: indexed work requires improve=done", failures)

    def test_certification_paths_reject_traversal(self) -> None:
        with self.assertRaisesRegex(ValueError, "clean repository-relative"):
            repo_path("../outside", "test artifact", "directory")

    def test_catalog_paths_reject_traversal_and_host_paths(self) -> None:
        failures = catalog_failures(
            [
                {"id": "safe", "path": "skills/safe/SKILL.md"},
                {"id": "traversal", "path": "../../outside/SKILL.md"},
                {"id": "host", "body_path": "/home/operator/private.md"},
            ]
        )
        self.assertEqual(len(failures), 2)
        self.assertTrue(any("traversal:path" in failure for failure in failures))
        self.assertTrue(any("host:body_path" in failure for failure in failures))

    def test_v2_certification_requires_three_evidence_classes(self) -> None:
        failures = evidence_failures(
            {"evidence": {"eval": {}, "safety": {}}},
            "0" * 40,
        )
        self.assertTrue(any("evidence.eval.sha256" in failure for failure in failures))
        self.assertTrue(any("evidence.safety.sha256" in failure for failure in failures))
        self.assertTrue(any("evidence.observability" in failure for failure in failures))

    def test_syndication_mutation_fails_closed(self) -> None:
        result = subprocess.run(
            [
                "python3",
                "scripts/syndicate.py",
                "starlight-skill-index",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("[stub]", result.stdout)

    def test_mcp_manifest_uses_current_schema_and_owned_identity(self) -> None:
        manifest = json.loads((ROOT / "mcp-server/server.json").read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["$schema"],
            "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
        )
        self.assertNotIn("status", manifest)
        self.assertEqual(
            manifest["repository"]["url"],
            "https://github.com/frankxai/starlight-agentic-os",
        )
        self.assertLessEqual(len(manifest["description"]), 100)

    def test_official_mcp_schema_rejects_known_bypasses(self) -> None:
        manifest = json.loads((ROOT / "mcp-server/server.json").read_text(encoding="utf-8"))
        mutations = []

        latest = copy.deepcopy(manifest)
        latest["packages"][0]["version"] = "latest"
        mutations.append(("latest package version", latest))

        missing_source = copy.deepcopy(manifest)
        del missing_source["repository"]["source"]
        mutations.append(("repository source", missing_source))

        incomplete_sse = copy.deepcopy(manifest)
        incomplete_sse["packages"][0]["transport"] = {"type": "sse"}
        mutations.append(("SSE URL", incomplete_sse))

        missing_env_name = copy.deepcopy(manifest)
        del missing_env_name["packages"][0]["environmentVariables"][0]["name"]
        mutations.append(("environment variable name", missing_env_name))

        for label, mutation in mutations:
            with self.subTest(label=label):
                self.assertTrue(mcp_schema_failures(mutation), label)


if __name__ == "__main__":
    unittest.main()
