# Security

- The demo API accepts a trusted `X-Actor-Id` header and isolates authorization behind an application port. Production deployment must replace it with authenticated identity at the edge.
- Uploads are checked by extension, media type, file signature where applicable, size, row count, and parser errors. Formula-like cells are treated as data and exports escape formula prefixes.
- Raw transaction fields, documents, upload bytes, secrets, and connection strings are excluded from logs.
- Secrets are supplied through environment variables; `.env` is ignored.
- SQLAlchemy parameters are bound; no user-controlled SQL is composed.
- CORS origins and upload limits are explicit configuration.
- Manual review and export endpoints require actor context and create audit records.
- CI runs dependency auditing and static security checks where supported.
- Third-party GitHub Actions are pinned to full commit SHAs and updated through reviewed Dependabot pull requests.
- Published container images include SBOM, provenance, registry attestations, and are deployed only by immutable digest.
- Deployment verifies the SSH host against a preconfigured `known_hosts` value; the production Compose binds only the gateway-facing web port to loopback.

Known portfolio limitation: the local demo has no full identity provider or tenant model. This is stated in the README and must not be represented as production authorization.
