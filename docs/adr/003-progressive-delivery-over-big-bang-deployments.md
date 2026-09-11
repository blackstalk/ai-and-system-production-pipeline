# ADR-003: Progressive Delivery Over Big-Bang Deployments

## Status

Accepted

## Context

Every check before merge — tests, static analysis, security scans, AI
review, human approval — reduces risk but cannot eliminate it. Some classes
of bug only manifest under real production conditions: traffic patterns and
concurrency levels a test suite doesn't replicate, data shapes a fixture
doesn't cover, or a dependency behaving differently under load than in CI.
Deploying a merged change to 100% of production traffic immediately means
any such bug is immediately customer-facing at full blast radius, with the
only recovery path being a full rollback after the damage is already done.

This risk is not unique to AI-assisted development, but it is amplified by
it: AI-generated code can look complete and pass every pre-merge check while
still encoding an assumption that only breaks under a production condition
none of the reviewers (human or AI) happened to think of.

## Decision

Ship every change through a canary: deploy to a small subset of
instances/traffic (default 5%), observe golden-signal metrics against the
stable baseline for a bake period, and only promote to 100% if the canary
stays within fixed thresholds (`scripts/canary_analysis.py`,
`docs/deployment-strategy.md` "Rollback triggers"). Any threshold violation
triggers an automatic rollback rather than requiring a human to notice and
intervene.

## Alternatives considered

- **Deploy directly to 100% after merge ("big bang").** Rejected: maximizes
  blast radius of any bug that only manifests in production, and makes
  rollback reactive (after customer impact) rather than preventive.
- **Blue/green deployment (instant full cutover, keep old version standing
  by).** Considered but not chosen as the default: blue/green catches
  "doesn't start" or "fails health check" failures well, but routes 100% of
  traffic to the new version the moment it's live, so it doesn't limit
  exposure to bugs that only appear under a fraction of real traffic the way
  a canary does. The same infrastructure in this repo (weighted routing)
  could implement blue/green as a special case (100/0 → 0/100 with no
  intermediate step) if a future change wanted that trade-off instead.
- **Manual, human-gated rollout stages with no automated thresholds.**
  Rejected as the sole mechanism: relies on a human actively watching
  dashboards during the bake window and catching a threshold violation in
  real time, which doesn't scale and introduces reaction-time lag an
  automated check doesn't have. (Human approval is still required to
  *initiate* the deployment — see [ADR-004](004-human-remains-final-decision-maker.md) —
  it's the moment-to-moment rollback decision that's automated.)

## Consequences

- Positive: a bug that only manifests in production affects a bounded
  fraction of traffic/users for a bounded time, not everyone immediately.
- Positive: rollback is automatic and fast (metric threshold violated →
  drain canary), not dependent on a human noticing a dashboard.
- Negative: adds latency between merge and full deployment (the bake
  window) — an explicit trade of deployment speed for safety, consistent
  with this repo's overall philosophy (see README "Guiding Principle").
- Negative: requires meaningful traffic volume to produce statistically
  useful canary metrics quickly; a very low-traffic service would need a
  longer bake window or a different validation strategy (e.g. synthetic
  traffic, as `deploy.yml` does for this demo app).
