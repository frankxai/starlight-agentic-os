# Starlight Agentic OS — Security

## Data Boundary

- Classification: public source, no PII.
- Secrets: prohibited.
- Local paths, usernames, tokens, private memory, and unredacted prompts:
  prohibited from catalogs and receipts.

## Router Boundary

- Bind shared HTTP transport to `127.0.0.1`.
- Do not expose the catalog router off-host without authentication, TLS, rate
  limits, and a separate threat review.
- Treat skill descriptions and frontmatter as untrusted input.
- Fail closed on path traversal, symlink escape, malformed catalog data, and
  registry/package identity mismatch.

## Publication

- Use short-lived or approved secret-store credentials only.
- Never write credentials to workflow logs or certification artifacts.
- Verify package ownership metadata and external registry identity before
  recording `registered`.
