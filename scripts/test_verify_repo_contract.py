#!/usr/bin/env python3
"""Regression tests for fail-closed repository receipt and path helpers."""
from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_repo  # noqa: E402


def test_receipts_require_reference_and_hash() -> None:
    with tempfile.TemporaryDirectory(prefix="starlight-receipt-test-") as directory:
        root = Path(directory)
        evidence = root / "receipts/eval.json"
        evidence.parent.mkdir()
        evidence.write_text('{"passed": true}\n', encoding="utf-8")
        digest = hashlib.sha256(evidence.read_bytes()).hexdigest()

        assert not verify_repo._receipt_is_inspectable(
            "receipts/eval.json", root=root
        )
        assert not verify_repo._receipt_is_inspectable(
            {"ref": "pending", "sha256": digest}, root=root
        )
        assert not verify_repo._receipt_is_inspectable(
            {"ref": "../../outside/results.json", "sha256": digest}, root=root
        )
        assert not verify_repo._receipt_is_inspectable(
            {"ref": "receipts/eval.json", "sha256": "not-a-hash"}, root=root
        )
        assert not verify_repo._receipt_is_inspectable(
            {"ref": "receipts/eval.json", "sha256": "a" * 64}, root=root
        )
        assert not verify_repo._receipt_is_inspectable(
            {"ref": "receipts/missing.json", "sha256": digest}, root=root
        )
        assert not verify_repo._receipt_is_inspectable(
            {"ref": "receipts", "sha256": digest}, root=root
        )
        for remote in (
            "http://example.com/evidence",
            "https://example.com/evidence",
            "file:///etc/passwd",
        ):
            assert not verify_repo._receipt_is_inspectable(
                {"ref": remote, "sha256": digest}, root=root
            )
        assert verify_repo._receipt_is_inspectable(
            {"ref": "receipts/eval.json", "sha256": digest}, root=root
        )
        assert verify_repo._receipt_is_inspectable(
            {"ref": "receipts/eval.json", "sha256": f"sha256:{digest}"}, root=root
        )


def test_catalog_paths_reject_traversal_and_host_paths() -> None:
    assert verify_repo._catalog_path_is_safe("skills/review/SKILL.md")
    assert not verify_repo._catalog_path_is_safe("../../outside/SKILL.md")
    assert not verify_repo._catalog_path_is_safe("/root/skills/SKILL.md")
    assert not verify_repo._catalog_path_is_safe(r"C:\Users\operator\SKILL.md")
    assert not verify_repo._catalog_path_is_safe("~/skills/SKILL.md")


def main() -> int:
    tests = [
        test_receipts_require_reference_and_hash,
        test_catalog_paths_reject_traversal_and_host_paths,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
