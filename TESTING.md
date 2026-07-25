# Starlight Agentic OS — Testing

Install the pinned repository test dependencies first:

```bash
python -m pip install -r requirements-dev.txt
```

## Required Suites

| Check | Command |
| --- | --- |
| Repository invariants | `python3 scripts/validate_repo.py` |
| Router behavior and security fallback | `python3 mcp-server/test_server.py` |
| Content-addressed security exceptions | `python3 index/test_scan_skill_frontmatter.py` |
| Governance failure paths | `python3 -m unittest discover -s tests -p 'test_*.py'` |
| Portable exemplar | `bash portable/verify-portability.sh portable/packs/acos-meta` |
| Certification integrity | `python3 scripts/verify_certifications.py --all` |
| Generated README truth | `python3 scripts/gen_readme.py --check` |
| Bundled asset parity | `python3 scripts/sync_mcp_assets.py --check` |
| Reproducible package build | `python3 -m build --wheel --sdist mcp-server` |
| Clean-install distribution | `python3 scripts/test_built_distribution.py` |
| Python syntax | `python3 -m compileall -q index mcp-server portable scripts` |

Failure paths must be tested. A skipped or unavailable check is not a pass.
The wheel test must run with no source-tree path, `PYTHONPATH`, or
`STARLIGHT_*` override. Network-dependent publication checks belong to release
preflight and cannot be substituted with local assertions.
