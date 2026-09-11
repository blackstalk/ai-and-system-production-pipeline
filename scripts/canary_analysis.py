#!/usr/bin/env python3
"""Reference canary promotion/rollback decision script.

Queries the Prometheus instance started by `docker compose up` for the
error rate and p95 latency of the `canary` track vs. the `stable`
track, and prints a PROMOTE or ROLLBACK decision based on the
thresholds documented in docs/deployment-strategy.md.

This is a reference pattern, not a production canary controller: a real
deployment would run this on a schedule during the canary bake time
(e.g. as a step in deploy.yml / a CD tool like Argo Rollouts or AWS
CodeDeploy) rather than by hand. It intentionally has no third-party
dependencies beyond the standard library so it can run anywhere.

Usage:
    python scripts/canary_analysis.py [--prometheus-url http://localhost:9090]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass

# Rollback thresholds — see docs/deployment-strategy.md "Rollback Triggers".
MAX_ERROR_RATE = 0.02  # 2% of requests may 5xx before we roll back
MAX_P95_LATENCY_SECONDS = 0.5
MAX_ERROR_RATE_DELTA_VS_STABLE = 0.01  # canary must not be >1pp worse than stable


@dataclass
class TrackMetrics:
    track: str
    request_count: float
    error_count: float
    p95_latency_seconds: float

    @property
    def error_rate(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count


def query_prometheus(base_url: str, promql: str) -> float:
    url = f"{base_url}/api/v1/query?query={urllib.parse.quote(promql)}"
    with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310 (localhost only)
        payload = json.loads(response.read())
    result = payload.get("data", {}).get("result", [])
    if not result:
        return 0.0
    return float(result[0]["value"][1])


def fetch_track_metrics(base_url: str, track: str) -> TrackMetrics:
    requests = query_prometheus(base_url, f'sum(http_requests_total{{job="{track}"}})')
    errors = query_prometheus(base_url, f'sum(http_errors_total{{job="{track}"}})')
    p95 = query_prometheus(
        base_url,
        f"histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket"
        f'{{job="{track}"}}[5m])) by (le))',
    )
    return TrackMetrics(
        track=track, request_count=requests, error_count=errors, p95_latency_seconds=p95
    )


def decide(canary: TrackMetrics, stable: TrackMetrics) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if canary.error_rate > MAX_ERROR_RATE:
        reasons.append(
            f"canary error rate {canary.error_rate:.2%} exceeds "
            f"absolute threshold {MAX_ERROR_RATE:.2%}"
        )
    if canary.p95_latency_seconds > MAX_P95_LATENCY_SECONDS:
        reasons.append(
            f"canary p95 latency {canary.p95_latency_seconds:.3f}s exceeds threshold "
            f"{MAX_P95_LATENCY_SECONDS:.3f}s"
        )
    delta = canary.error_rate - stable.error_rate
    if delta > MAX_ERROR_RATE_DELTA_VS_STABLE:
        reasons.append(
            f"canary error rate is {delta:.2%} higher than stable "
            f"(threshold {MAX_ERROR_RATE_DELTA_VS_STABLE:.2%})"
        )

    return (len(reasons) == 0, reasons)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prometheus-url", default="http://localhost:9090")
    args = parser.parse_args()

    canary = fetch_track_metrics(args.prometheus_url, "canary")
    stable = fetch_track_metrics(args.prometheus_url, "stable")

    should_promote, reasons = decide(canary, stable)

    print(
        f"stable: requests={stable.request_count:.0f} error_rate={stable.error_rate:.2%} "
        f"p95={stable.p95_latency_seconds:.3f}s"
    )
    print(
        f"canary: requests={canary.request_count:.0f} error_rate={canary.error_rate:.2%} "
        f"p95={canary.p95_latency_seconds:.3f}s"
    )

    if should_promote:
        print("DECISION: PROMOTE — canary is within all thresholds relative to stable.")
        return 0

    print("DECISION: ROLLBACK — one or more thresholds were violated:")
    for reason in reasons:
        print(f"  - {reason}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
