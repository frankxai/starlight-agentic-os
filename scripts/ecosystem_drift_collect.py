#!/usr/bin/env python3
"""Deterministic official-source collector for plugin/MCP/marketplace drift.

No LLM. No clones. Conditional HTTP + git ls-remote only. First observation is
a baseline; later ticks emit changed-only packets. Monitor stdout is a content
fingerprint with no timestamps.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
WATCHLIST_PATH = ROOT / "registry" / "ecosystem-drift" / "watchlist.json"
DEFAULT_STATE_DIR = (
    Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes"))
    / "cache"
    / "ecosystem-drift"
)
USER_AGENT = "StarlightEcosystemDrift/1.0 (+https://github.com/frankxai/starlight-agentic-os)"
MAX_BODY = 2 * 1024 * 1024
FETCH_TIMEOUT = 25
FAILURE_GAP_AFTER = 2
EXCERPT_CHARS = 240

HttpFetch = Callable[[str, dict[str, str]], dict[str, Any]]
GitHead = Callable[[str], dict[str, Any]]


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def excerpt_text(payload: bytes) -> str:
    text = payload.decode("utf-8", errors="replace")
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= EXCERPT_CHARS:
        return text
    return text[:EXCERPT_CHARS].rstrip() + "…"


def default_http_fetch(url: str, extra_headers: dict[str, str]) -> dict[str, Any]:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*", **extra_headers}
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as response:
            body = response.read(MAX_BODY + 1)
            truncated = len(body) > MAX_BODY
            if truncated:
                body = body[:MAX_BODY]
            return {
                "ok": True,
                "status": int(getattr(response, "status", 200)),
                "url": response.geturl(),
                "body": body,
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "truncated": truncated,
            }
    except urllib.error.HTTPError as error:
        if error.code == 304:
            return {
                "ok": True,
                "status": 304,
                "url": url,
                "body": b"",
                "etag": error.headers.get("ETag") if error.headers else None,
                "last_modified": error.headers.get("Last-Modified") if error.headers else None,
                "truncated": False,
            }
        return {"ok": False, "status": int(error.code), "url": url, "error": f"http_{error.code}"}
    except Exception as error:  # noqa: BLE001 — collector must never crash a source
        return {"ok": False, "status": 0, "url": url, "error": type(error).__name__}


def default_git_head(repo: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["git", "ls-remote", f"https://github.com/{repo}.git", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
        timeout=FETCH_TIMEOUT,
    )
    if completed.returncode != 0:
        return {"ok": False, "status": 0, "error": "git_ls_remote_failed", "url": f"https://github.com/{repo}"}
    line = (completed.stdout or "").splitlines()[0] if completed.stdout else ""
    sha = line.split()[0] if line else ""
    if len(sha) < 40:
        return {"ok": False, "status": 0, "error": "git_ls_remote_empty", "url": f"https://github.com/{repo}"}
    return {
        "ok": True,
        "status": 200,
        "url": f"https://github.com/{repo}",
        "body": sha.encode("ascii"),
        "etag": sha,
        "last_modified": None,
        "truncated": False,
    }


def candidate_urls(source: dict[str, Any]) -> list[str]:
    url = source["url"]
    if source.get("prefer_markdown") and not url.endswith(".md"):
        if url.endswith("/"):
            return [url.rstrip("/") + ".md", url + "index.md", url]
        return [url + ".md", url]
    return [url]


def fetch_source(
    source: dict[str, Any],
    prior: dict[str, Any],
    http_fetch: HttpFetch,
    git_head: GitHead,
) -> dict[str, Any]:
    fetch = source["fetch"]
    if fetch == "github_repo":
        return git_head(source["repo"])
    if fetch != "http":
        return {"ok": False, "status": 0, "url": source.get("url", ""), "error": f"unknown_fetch_{fetch}"}

    extra: dict[str, str] = {}
    if prior.get("etag"):
        extra["If-None-Match"] = str(prior["etag"])
    if prior.get("last_modified"):
        extra["If-Modified-Since"] = str(prior["last_modified"])

    last_error: dict[str, Any] = {"ok": False, "status": 0, "url": source["url"], "error": "no_url"}
    for url in candidate_urls(source):
        result = http_fetch(url, extra)
        last_error = result
        if result.get("ok") and result.get("status") not in {404, 410}:
            return result
    return last_error


def fingerprint_from_state(source_ids: list[str], state: dict[str, Any]) -> str:
    rows: list[str] = []
    for source_id in source_ids:
        record = state.get("sources", {}).get(source_id, {})
        digest = record.get("digest") or "missing"
        gap = int(record.get("consecutive_failures") or 0) >= FAILURE_GAP_AFTER
        rows.append(f"{source_id}={digest}{'!gap' if gap else ''}")
    return digest_bytes("\n".join(rows).encode("utf-8"))


def collect(
    watchlist: dict[str, Any],
    state: dict[str, Any],
    http_fetch: HttpFetch = default_http_fetch,
    git_head: GitHead = default_git_head,
) -> dict[str, Any]:
    sources = watchlist["sources"]
    source_ids = [item["id"] for item in sources]
    prior_sources = dict(state.get("sources") or {})
    had_baseline = bool(prior_sources)
    next_sources: dict[str, Any] = {}
    changes: list[dict[str, Any]] = []
    coverage_gaps: list[dict[str, Any]] = []
    ok_count = 0

    for source in sources:
        source_id = source["id"]
        prior = prior_sources.get(source_id, {})
        result = fetch_source(source, prior, http_fetch, git_head)
        record = {
            "id": source_id,
            "ecosystem": source["ecosystem"],
            "kind": source["kind"],
            "fetch": source["fetch"],
            "url": result.get("url") or source.get("url") or source.get("repo"),
            "status": result.get("status", 0),
        }
        if result.get("ok") and result.get("status") == 304 and prior.get("digest"):
            record.update(
                {
                    "digest": prior["digest"],
                    "etag": result.get("etag") or prior.get("etag"),
                    "last_modified": result.get("last_modified") or prior.get("last_modified"),
                    "consecutive_failures": 0,
                    "excerpt": prior.get("excerpt", ""),
                }
            )
            ok_count += 1
        elif result.get("ok"):
            body = result.get("body") or b""
            digest = digest_bytes(body)
            record.update(
                {
                    "digest": digest,
                    "etag": result.get("etag"),
                    "last_modified": result.get("last_modified"),
                    "consecutive_failures": 0,
                    "excerpt": excerpt_text(body),
                    "truncated": bool(result.get("truncated")),
                }
            )
            ok_count += 1
            if had_baseline and digest != prior.get("digest"):
                changes.append(
                    {
                        "id": source_id,
                        "ecosystem": source["ecosystem"],
                        "kind": source["kind"],
                        "url": record["url"],
                        "event": "content_digest_changed",
                        "previous_digest": prior.get("digest"),
                        "digest": digest,
                        "excerpt": record["excerpt"],
                    }
                )
        else:
            failures = int(prior.get("consecutive_failures") or 0) + 1
            record.update(
                {
                    "digest": prior.get("digest"),
                    "etag": prior.get("etag"),
                    "last_modified": prior.get("last_modified"),
                    "consecutive_failures": failures,
                    "excerpt": prior.get("excerpt", ""),
                    "error": result.get("error", "fetch_failed"),
                }
            )
            if failures >= FAILURE_GAP_AFTER:
                coverage_gaps.append(
                    {
                        "id": source_id,
                        "ecosystem": source["ecosystem"],
                        "url": record["url"],
                        "event": "coverage_gap",
                        "consecutive_failures": failures,
                        "error": record["error"],
                    }
                )
        next_sources[source_id] = record

    next_state = {"schema": "starlight.ecosystem_drift_state.v1", "sources": next_sources}
    fingerprint = fingerprint_from_state(source_ids, next_state)
    if not had_baseline:
        kind = "baseline"
    elif changes or coverage_gaps:
        kind = "changed"
    else:
        kind = "unchanged"
    packet = {
        "schema": "starlight.ecosystem_drift_packet.v1",
        "kind": kind,
        "fingerprint": fingerprint,
        "canonical_issue_repo": watchlist.get("canonical_issue_repo"),
        "parent_issue": watchlist.get("parent_issue"),
        "related": watchlist.get("related") or {},
        "source_count": len(sources),
        "ok_count": ok_count,
        "changes": changes,
        "coverage_gaps": coverage_gaps,
    }
    return {"state": next_state, "packet": packet}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect official plugin/MCP/marketplace drift.")
    parser.add_argument("--watchlist", type=Path, default=WATCHLIST_PATH)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--fingerprint", action="store_true", help="Print digest fingerprint only.")
    parser.add_argument("--changed-only", action="store_true", help="Print packet only when changed.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    watchlist = load_json(args.watchlist, None)
    if not isinstance(watchlist, dict) or not watchlist.get("sources"):
        print(f"watchlist missing or empty: {args.watchlist}", file=sys.stderr)
        return 2
    state_dir: Path = args.state_dir
    state_path = state_dir / "state.json"
    packet_path = state_dir / "packet.json"
    state = load_json(state_path, {})
    result = collect(watchlist, state)
    save_json(state_path, result["state"])
    save_json(packet_path, result["packet"])
    packet = result["packet"]
    if args.fingerprint:
        print(packet["fingerprint"])
        return 0
    if args.changed_only and packet["kind"] != "changed":
        return 0
    json.dump(packet, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
