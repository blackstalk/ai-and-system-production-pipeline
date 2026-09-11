# Deployment Strategy: Progressive Delivery

## Why not deploy straight to 100%

A merge to `main` means tests, static analysis, security scans, AI review,
and a human all agreed the change looks safe. None of that guarantees it
*is* safe under real production traffic, real data shapes, and real load —
only production traffic can reveal some classes of bug (a rare input shape,
a dependency that behaves differently under load, a race condition that
needs concurrency to trigger). Canary deployment is the second safety net:
AI review and testing try to catch issues **before** merge; canary
monitoring catches what only becomes visible **after** merge, while limiting
the blast radius to a small fraction of traffic. See
[ADR-003](adr/003-progressive-delivery-over-big-bang-deployments.md).

## Sequence

```text
Build artifact
  ↓
Deploy canary (small % of instances/traffic)
  ↓
Route a small percentage of traffic to canary (start: 1–5%)
  ↓
Observe metrics (canary vs. stable baseline)
  ↓
Compare against baseline against fixed thresholds
  ↓
Promote (ramp toward 100%) OR Rollback (drain canary, keep stable)
```

Implemented in this repo as:

- `.github/workflows/deploy.yml` — build → deploy → observe → decide
- `docker-compose.yml` + `deploy/canary/nginx.conf.template` — a `stable`
  container and a `canary` container behind an nginx router doing weighted
  traffic splitting (`split_clients`, default 5% canary / 95% stable)
- `deploy/canary/prometheus.yml` — scrapes both tracks' `/metrics` endpoint
  independently so they can be compared
- `scripts/canary_analysis.py` — queries Prometheus and prints a
  PROMOTE/ROLLBACK decision based on fixed thresholds

This is a **reference pattern**, not a production canary controller — see
"Cloud equivalents" below for what actually runs this in a real environment.

## Rollback triggers

`scripts/canary_analysis.py` currently checks:

| Trigger | Threshold |
|---|---|
| Canary error rate (absolute) | > 2% of requests return 5xx |
| Canary p95 latency | > 500ms |
| Canary error rate vs. stable (relative) | > 1 percentage point worse than stable |

A real deployment would add:

- Health check failures (readiness probe failing repeatedly)
- A business KPI dropping unexpectedly (e.g. checkout completion rate) —
  this requires product-specific instrumentation this reference app doesn't
  have, but the pattern is the same: define the KPI, define the threshold,
  wire it into the same decision function
- Critical exception rate spikes (a specific exception class/count, not just
  aggregate error rate)

Any single trigger firing is sufficient to roll back — this is intentional.
A canary is guilty until proven innocent; the cost of a false-positive
rollback (a few minutes of re-running the pipeline) is far lower than the
cost of a false-negative promotion (a bad build serving 100% of traffic).

## Production monitoring → golden signals

`GET /metrics` (Prometheus format, `app/core/metrics.py`) and structured
JSON access logs (`app/core/logging.py`, one line per request with a
correlation ID) map directly onto the four golden signals:

| Golden signal | This repo's implementation |
|---|---|
| **Latency** | `http_request_duration_seconds` histogram; p95 used in canary analysis |
| **Traffic** | `http_requests_total` counter, labeled by method/path/status |
| **Errors** | `http_errors_total` counter (5xx); `http_requests_total` filtered by status code for 4xx |
| **Saturation** | Not instrumented in this reference app (would be CPU/memory/connection-pool utilization) — the same `Counter`/`Histogram`/`Gauge` pattern in `app/core/metrics.py` extends directly to it |

Example alert conditions a real deployment would wire into
Prometheus/Alertmanager or CloudWatch Alarms:

- `rate(http_errors_total[5m]) / rate(http_requests_total[5m]) > 0.02` for 5
  minutes → page on-call
- `histogram_quantile(0.95, http_request_duration_seconds) > 0.5` for 10
  minutes → page on-call
- `up{job="ai-production-pipeline"} == 0` for 1 minute → page on-call
  (instance down)

## Cloud equivalents

The local Docker Compose + nginx setup is a stand-in for infrastructure this
portfolio project doesn't provision. The same sequence, unchanged:

| Step | Kubernetes | AWS ECS | AWS Lambda | Service mesh / API Gateway |
|---|---|---|---|---|
| Deploy canary | New `Deployment` + `Service` subset, or Argo Rollouts `canary` step | New task definition revision, second target group | New version + alias pointing at it | New backend/target registered |
| Route % traffic | Argo Rollouts / Flagger traffic weight | ALB weighted target groups | Lambda alias traffic shifting (`$LATEST` weights) | Istio `VirtualService` weight, or API Gateway canary stage percentage |
| Observe | Prometheus + Grafana, or CloudWatch Container Insights | CloudWatch metrics per target group | CloudWatch metrics per alias | Mesh telemetry (Envoy stats) or API Gateway stage metrics |
| Promote | Increase weight to 100%, delete old ReplicaSet | Shift ALB weights to 100%, deregister old tasks | Shift alias to 100% | Increase mesh/gateway weight to 100% |
| Rollback | Scale canary to 0 / delete it, weight stays on stable | Deregister canary tasks from target group | Shift alias weight back to 0 | Weight back to 0 on canary backend |

## Human approval as a second enforcement point

`deploy.yml`'s `deploy-canary`, `observe-and-decide`, and
`promote-or-rollback` jobs all target a `production` GitHub Environment.
Configuring that environment with required reviewers in repository settings
means a human must explicitly approve the deployment run — independent of,
and in addition to, the human who approved the PR that merged. See
[ADR-004](adr/004-human-remains-final-decision-maker.md).
