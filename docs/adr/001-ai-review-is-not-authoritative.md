# ADR-001: AI Review Is Not Authoritative

## Status

Accepted

## Context

LLM-based code review can catch contextual issues (missing authorization
checks, subtle state-machine bugs, misleading assumptions) that pattern-based
static analysis structurally cannot, because they require understanding
intent, not just syntax. It's tempting to treat a clean AI review as
sufficient evidence a PR is safe to merge, especially since it's fast and
runs on every PR at near-zero marginal cost.

But LLM output is probabilistic, not deterministic. The same diff can
produce different findings on different runs. A model can miss a real
vulnerability it would catch nine times out of ten, or confidently assert a
finding that doesn't hold up (a hallucination). Treating a probabilistic
signal as an authoritative merge gate would mean the safety of production
code depends on a single non-reproducible check.

## Decision

The AI reviewer (`.github/workflows/ai-review.yml`) is one layer in a
defense-in-depth pipeline, never the sole gate. Concretely:

- Deterministic tools (ruff, mypy, Bandit, pip-audit, pytest) run
  independently and are required regardless of what the AI reviewer finds.
- The AI reviewer fails its own check on CRITICAL/HIGH findings, but a human
  reviewer retains the ability to review those findings and merge anyway if
  they judge the finding to be wrong or acceptable — the same authority they
  have over any other CI check.
- The AI reviewer being unavailable (no API key, API outage, unparseable
  response) never blocks a merge by itself — see `scripts/ai_review.py`'s
  graceful-skip behavior.
- A human must approve every PR regardless of AI review outcome — see
  [ADR-004](004-human-remains-final-decision-maker.md).

## Alternatives considered

- **AI review as a hard, unbypassable merge gate.** Rejected: makes merge
  velocity hostage to a non-reproducible check, and creates an incentive to
  route around the tool (e.g. by gaming prompts) rather than trust it.
- **AI review as pure informational commentary, never blocking.** Rejected:
  a CRITICAL finding (e.g. an obvious SQL injection) that never blocks
  anything is easy to miss in a busy PR thread. Blocking on CRITICAL/HIGH,
  with an explicit human override path, balances signal against velocity.
- **No AI review at all, deterministic tools only.** Rejected: deterministic
  tools cannot express "this authorization check doesn't verify ownership" —
  that requires semantic understanding of the code's intent, which is
  exactly the gap AI review fills.

## Consequences

- Positive: fast, cheap, always-on layer catching a class of bug no other
  tool in this pipeline catches.
- Positive: the pipeline degrades gracefully if the AI reviewer is
  unavailable or wrong — nothing else in the pipeline depends on it being
  perfect.
- Negative: requires human judgment to interpret and potentially override
  findings, which is more cognitive load than "green checkmark means safe."
  This is treated as a feature, not a bug — see [ADR-004](004-human-remains-final-decision-maker.md).
