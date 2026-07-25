# Pack Certifications

Each receipt binds one declared pack version to exact bytes, a source commit,
passing commands, and an independent verifier.

Receipts live at `certifications/<pack>/<version>.json` and validate with:

```bash
python3 scripts/verify_certifications.py --all
```

Receipts are added after the source commit they certify. They are evidence, not a
substitute for external package or registry inspection.
