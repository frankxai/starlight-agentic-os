from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ecosystem_drift_collect import collect, digest_bytes, main


WATCHLIST = {
    "schema": "starlight.ecosystem_drift_watchlist.v1",
    "canonical_issue_repo": "frankxai/starlight-agentic-os",
    "parent_issue": 7,
    "sources": [
        {
            "id": "docs-a",
            "ecosystem": "openai",
            "kind": "docs",
            "fetch": "http",
            "url": "https://example.test/a.md",
        },
        {
            "id": "repo-b",
            "ecosystem": "claude",
            "kind": "marketplace",
            "fetch": "github_repo",
            "repo": "example/official",
        },
    ],
}


def http_map(bodies: dict[str, bytes], etag: str = "etag-a", not_modified: bool = False):
    def fetch(url: str, extra_headers: dict[str, str]) -> dict:
        if not_modified and extra_headers.get("If-None-Match") == etag:
            return {
                "ok": True,
                "status": 304,
                "url": url,
                "body": b"",
                "etag": etag,
                "last_modified": None,
                "truncated": False,
            }
        body = bodies.get(url)
        if body is None:
            return {"ok": False, "status": 404, "url": url, "error": "http_404"}
        return {
            "ok": True,
            "status": 200,
            "url": url,
            "body": body,
            "etag": etag,
            "last_modified": None,
            "truncated": False,
        }

    return fetch


def git_map(shas: dict[str, str]):
    def head(repo: str) -> dict:
        sha = shas.get(repo)
        if not sha:
            return {"ok": False, "status": 0, "error": "git_ls_remote_failed", "url": f"https://github.com/{repo}"}
        return {
            "ok": True,
            "status": 200,
            "url": f"https://github.com/{repo}",
            "body": sha.encode("ascii"),
            "etag": sha,
            "last_modified": None,
            "truncated": False,
        }

    return head


class EcosystemDriftCollectTests(unittest.TestCase):
    def test_first_observation_is_baseline_not_a_change(self) -> None:
        result = collect(
            WATCHLIST,
            {},
            http_fetch=http_map({"https://example.test/a.md": b"alpha"}),
            git_head=git_map({"example/official": "a" * 40}),
        )
        self.assertEqual(result["packet"]["kind"], "baseline")
        self.assertEqual(result["packet"]["changes"], [])
        self.assertEqual(result["packet"]["ok_count"], 2)
        self.assertEqual(len(result["packet"]["fingerprint"]), 64)

    def test_digest_change_emits_changed_packet(self) -> None:
        first = collect(
            WATCHLIST,
            {},
            http_fetch=http_map({"https://example.test/a.md": b"alpha"}),
            git_head=git_map({"example/official": "a" * 40}),
        )
        second = collect(
            WATCHLIST,
            first["state"],
            http_fetch=http_map({"https://example.test/a.md": b"beta"}),
            git_head=git_map({"example/official": "a" * 40}),
        )
        self.assertEqual(second["packet"]["kind"], "changed")
        self.assertEqual([item["id"] for item in second["packet"]["changes"]], ["docs-a"])
        self.assertEqual(second["packet"]["changes"][0]["digest"], digest_bytes(b"beta"))
        self.assertNotEqual(first["packet"]["fingerprint"], second["packet"]["fingerprint"])

    def test_not_modified_is_unchanged(self) -> None:
        first = collect(
            WATCHLIST,
            {},
            http_fetch=http_map({"https://example.test/a.md": b"alpha"}),
            git_head=git_map({"example/official": "a" * 40}),
        )
        second = collect(
            WATCHLIST,
            first["state"],
            http_fetch=http_map({"https://example.test/a.md": b"alpha"}, not_modified=True),
            git_head=git_map({"example/official": "a" * 40}),
        )
        self.assertEqual(second["packet"]["kind"], "unchanged")
        self.assertEqual(second["packet"]["fingerprint"], first["packet"]["fingerprint"])

    def test_two_failures_become_coverage_gap_and_change_fingerprint(self) -> None:
        first = collect(
            WATCHLIST,
            {},
            http_fetch=http_map({"https://example.test/a.md": b"alpha"}),
            git_head=git_map({"example/official": "a" * 40}),
        )
        failing_http = http_map({})
        failing_git = git_map({})
        second = collect(WATCHLIST, first["state"], http_fetch=failing_http, git_head=failing_git)
        self.assertEqual(second["packet"]["kind"], "unchanged")
        third = collect(WATCHLIST, second["state"], http_fetch=failing_http, git_head=failing_git)
        self.assertEqual(third["packet"]["kind"], "changed")
        self.assertEqual({item["id"] for item in third["packet"]["coverage_gaps"]}, {"docs-a", "repo-b"})
        self.assertNotEqual(first["packet"]["fingerprint"], third["packet"]["fingerprint"])

    def test_changed_only_stdout_is_empty_on_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            watchlist = root / "watchlist.json"
            watchlist.write_text(json.dumps(WATCHLIST), encoding="utf-8")
            state_dir = root / "state"
            with patch("scripts.ecosystem_drift_collect.default_http_fetch", http_map({"https://example.test/a.md": b"alpha"})):
                with patch("scripts.ecosystem_drift_collect.default_git_head", git_map({"example/official": "a" * 40})):
                    code = main(["--watchlist", str(watchlist), "--state-dir", str(state_dir), "--changed-only"])
            self.assertEqual(code, 0)
            packet = json.loads((state_dir / "packet.json").read_text(encoding="utf-8"))
            self.assertEqual(packet["kind"], "baseline")


if __name__ == "__main__":
    unittest.main()
