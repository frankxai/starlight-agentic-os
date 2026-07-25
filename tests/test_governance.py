from __future__ import annotations

import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.pack_digest import digest_directory
from scripts.validate_repo import lifecycle_failures, mcp_schema_failures
from scripts.verify_certifications import repo_path

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

    def test_pack_digest_rejects_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root.parent / f"{root.name}-outside.txt"
            outside.write_text("outside", encoding="utf-8")
            try:
                os.symlink(outside, root / "escape.txt")
                with self.assertRaisesRegex(ValueError, "contains a symlink"):
                    digest_directory(root)
            finally:
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
