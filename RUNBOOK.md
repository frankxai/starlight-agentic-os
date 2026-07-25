# Starlight Agentic OS — Runbook

## Local Health

```bash
python3 scripts/validate_repo.py
python3 mcp-server/test_server.py
python3 index/test_scan_skill_frontmatter.py
python3 -m unittest discover -s tests -p 'test_*.py'
bash portable/verify-portability.sh portable/packs/acos-meta
python3 scripts/verify_certifications.py --all
python3 scripts/gen_readme.py --check
python3 scripts/sync_mcp_assets.py --check
python3 -m build --wheel --sdist mcp-server
python3 scripts/test_built_distribution.py
python3 -m compileall -q index mcp-server portable scripts
```

## Improve A Pack

1. Select the declared pack version.
2. Run its quality suite at an isolated source commit.
3. Compute the stable directory digest with `scripts/pack_digest.py`.
4. Have a distinct verifier rerun the suite.
5. Add `certifications/<pack>/<version>.json` in a later commit.
6. Set `improve: done`, the exact checksum, and receipt path in
   `registry.yaml`.
7. Regenerate the README and run all health checks.

## Publish Preflight

1. Confirm `improve: done` and certification validation.
2. Confirm the package exists at the version declared by `server.json`.
3. Confirm package ownership metadata matches the MCP server name.
4. Validate the current official MCP Registry schema.
5. Obtain named-human approval.
6. Publish, inspect the external record, then update `registered`.

No dry run, package build, workflow success, or authored playbook changes
`registered`.

## Rollback

- Before merge: close the PR or delete only its isolated branch.
- After merge: revert the bounded commit.
- After publication: restore the previous certified version and record any
  external registry rollback separately.
