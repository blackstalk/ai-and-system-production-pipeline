# ADR-004: A Human Remains the Final Decision-Maker

## Status

Accepted

## Context

Every layer in this pipeline before this one is automatable and mostly
automated: AI writes code, AI reviews code, deterministic tools verify code,
canary deployment and automated rollback handle production risk. It's
technically possible to automate the last step too — auto-merge on green
checks, auto-promote on passing canary metrics — and doing so would make the
pipeline fully autonomous end to end.

The risk this creates is specific: every automated layer in this pipeline
(AI review, tests, security scans, canary thresholds) is scoped to what it
was designed to check. None of them has business context — whether this is
the wrong week to ship a risky change, whether an edge case is acceptable
because the feature is behind a flag, whether "the numbers look fine" is
actually fine given something happening elsewhere in the system that no
metric captures. A fully autonomous pipeline has no place for that judgment
to enter, and no accountable person to have exercised it if something goes
wrong.

## Decision

Two independent points in the pipeline require explicit human action and
cannot be bypassed by automation:

1. **PR approval before merge.** Branch protection requires a human
   approving review in addition to every automated check passing. The PR
   template (`.github/pull_request_template.md`) requires the author to
   answer specific accountability questions (what could break, does this
   touch auth/data deletion, what's the rollback plan, what metrics to
   watch) — designed so the human reviewer is evaluating judgment, not
   re-deriving facts.
2. **Deployment approval before production traffic.** `deploy.yml`'s
   deployment jobs target a `production` GitHub Environment configured with
   required reviewers, a second, independent approval gate from the PR
   approval — someone must explicitly authorize this specific deployment,
   not just the code change in the abstract.

AI review findings and canary metrics inform these decisions; they do not
make them. A human can merge over an AI-flagged CRITICAL finding they judge
to be wrong (with that judgment itself now part of the reviewable record),
and a human approves each production deployment even when every automated
signal is green.

## Alternatives considered

- **Full auto-merge and auto-deploy on green checks.** Rejected: removes the
  one layer with business context and accountability, for a speed gain that
  doesn't offset the risk in a system explicitly designed around
  defense-in-depth.
- **Human approval only at PR merge, fully automated promotion after
  that.** Considered, and partially adopted — the canary
  promote/rollback *decision itself* is automated (see
  [ADR-003](003-progressive-delivery-over-big-bang-deployments.md)), since
  it's a narrow, well-defined metric comparison well-suited to automation.
  What remains human-gated is *authorizing the deployment to begin*, a
  different and broader judgment call than "do these specific numbers clear
  this specific threshold."
- **Human approval at every pipeline stage (after AI review, after each
  test suite, etc.).** Rejected: this defeats the purpose of automating
  deterministic and narrowly-scoped checks in the first place, and would
  make the pipeline slower than a pre-AI, fully-manual review process.

## Consequences

- Positive: accountability for what ships to production always traces to a
  specific person's explicit decision, not "the pipeline did it."
- Positive: preserves a place for context none of the automated layers have
  access to.
- Negative: caps how fast this pipeline can go — a fully autonomous version
  would be faster. This is treated as the correct trade-off, not an
  oversight; see the README's "Guiding Principle."
