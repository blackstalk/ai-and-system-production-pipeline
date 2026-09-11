# Threat Model

Scope: the reference `Item` API in this repository, and the pipeline that
ships changes to it. This is a lightweight, portfolio-appropriate threat
model (STRIDE-flavored), not an exhaustive enterprise assessment.

## Assets

- Item data (name, price, quantity) — low sensitivity in this demo, but
  modeled as if it mattered, since the same code shape would hold real data
  in a production fork
- Availability of the API itself
- The CI/CD pipeline's integrity (a compromised workflow could deploy
  arbitrary code)
- `ANTHROPIC_API_KEY` and any future deployment credentials stored as GitHub
  Secrets

## Trust boundaries

```text
Internet ── [API boundary: FastAPI + pydantic validation] ── Service layer ── Repository ── (in-memory store)
                                                                                   │
GitHub Actions runner ── [Secrets boundary] ── Anthropic API / (future) cloud deploy target
```

Validation happens exactly once, at the API boundary (`app/models/item.py`
pydantic constraints). Everything past that boundary — `services/`,
`repositories/` — assumes inputs are already well-formed. This is a
deliberate "validate at the edge" pattern: it means the service layer's
logic doesn't need defensive re-validation scattered through it, and it
means there is exactly one place to audit for injection/boundary issues.

## STRIDE walkthrough

| Threat | Where it applies here | Mitigation |
|---|---|---|
| **Spoofing** | No authentication exists in this reference app | Out of scope for the demo app; a real fork would add auth (OAuth2/JWT) at the same API boundary layer, and the AI reviewer prompt already treats "authentication" as a high-risk area |
| **Tampering** | Request bodies, query params | Pydantic `extra="forbid"` rejects unknown fields; type/range constraints (`gt`, `le`, `min_length`) reject malformed values; see `test_create_item_rejects_unknown_fields` |
| **Repudiation** | No audit trail of who did what | Structured JSON logs with request IDs give traceability of *what* happened; a real deployment needing non-repudiation would add authenticated audit logging, called out in `examples/unsafe_delete.py`'s remediation |
| **Information disclosure** | Unhandled exceptions leaking stack traces | `app/main.py`'s global exception handler returns a generic 500 + request ID, never the exception detail, to the client; the real exception is logged server-side only |
| **Denial of service** | Unbounded list queries, unbounded request bodies | `limit`/`offset` are constrained (`ge=1, le=100`) in `app/api/items.py`; pydantic string/int fields have explicit max bounds |
| **Elevation of privilege** | No authorization model exists in this reference app | Out of scope for the demo app (no user/role concept); `examples/missing_authorization.py` documents the IDOR pattern the AI reviewer is specifically instructed to catch once auth exists |

## Concrete vulnerability classes and where each layer catches them

| Vulnerability | Caught by |
|---|---|
| SQL injection | Bandit (`B608`), AI reviewer (security category) — see `examples/sql_injection.py` |
| Hardcoded secret | GitHub secret scanning + push protection (see `security.yml`), AI reviewer |
| Vulnerable dependency (known CVE) | `pip-audit`, and in a real deployment, Dependabot |
| Missing authorization / IDOR | AI reviewer (explicitly instructed; pattern tools can't catch this without semantic understanding) — see `examples/missing_authorization.py` |
| Unbounded/DoS-prone endpoint | AI reviewer (performance category), integration tests asserting `limit`/`offset` bounds |
| Debug mode / insecure default shipped | `security.yml`'s `unsafe-config-check` job (grep-based deterministic check) |
| Container running as root | `security.yml`'s `unsafe-config-check` job; `Dockerfile` sets a non-root `USER` |

## Where paid/managed tools would extend this

This repo intentionally requires no paid service to run its CI. A team with
budget and/or a GitHub Enterprise/Advanced Security license would add:

- **GitHub Dependabot** — automated dependency update PRs; complements
  `pip-audit`'s point-in-time scan with continuous monitoring
- **GitHub Advanced Security** (code scanning via CodeQL, secret scanning
  push protection on private repos) — deeper static analysis than Bandit for
  data-flow-sensitive vulnerability classes
- **Snyk** — SCA + container image scanning with a larger vulnerability
  database and license compliance checks
- **Trivy** — container/IaC scanning in CI, catching base-image CVEs Bandit
  and pip-audit don't cover (they scan Python code/dependencies, not the
  OS layer of the built image)

None of these are required for the pipeline in this repo to function — they
would slot in as additional jobs in `security.yml` alongside Bandit and
pip-audit, following the same defense-in-depth principle: each tool covers a
layer the others don't.

## Non-goals of this threat model

- No authentication/authorization system exists to model in depth, since
  the demo app has none — this is called out explicitly rather than
  pretended around.
- Infrastructure-level threats (cloud IAM misconfiguration, network
  segmentation) are out of scope because no real cloud infrastructure is
  provisioned by this repo — see `docs/deployment-strategy.md` "What is real
  vs. simulated."
