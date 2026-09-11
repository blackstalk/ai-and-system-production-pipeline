# ADR-002: AI Review Focuses on Production Risk, Not Style

## Status

Accepted

## Context

An LLM asked to "review this code" with no constraints will comment on
everything: naming, formatting, structure, alternative implementations,
missing docstrings. Most of that is either already enforced deterministically
(ruff for formatting/imports, mypy for types) or is a stylistic opinion with
no bearing on whether the code is safe to run in production. A reviewer that
produces ten comments per PR, nine of them stylistic noise, trains engineers
to skim past all ten — including the one that mattered.

## Decision

`prompts/code-review.md` explicitly instructs the model to ignore formatting,
naming preferences (unless a name is actively misleading), stylistic
opinions, trivial lint issues, and anything deterministic tooling already
owns. It instructs the model to prioritize four categories only: business
logic, security, reliability, and performance — with an explicit escalation
rule that changes touching high-risk areas (auth, payments, personal data,
destructive operations, data deletion, migrations, infrastructure, secrets,
external integrations) get treated as higher severity by default.

The output schema (`prompts/code-review.md` "Output format") requires a
concrete production impact and remediation for every finding — "this could
be a security issue" is explicitly disallowed as too vague to act on.

## Alternatives considered

- **Unconstrained "review this code" prompt.** Rejected for the noise
  problem described above — measured informally, an unconstrained prompt
  produces roughly 3-5x more comments, the large majority stylistic.
- **Scoring/grading the PR (e.g. "8/10").** Rejected: a score invites
  bikeshedding about the number and provides no actionable information a
  human can act on. Concrete findings with remediations do.
- **Reviewing only high-risk-area diffs, skipping everything else.**
  Rejected: a business-logic bug in a "low-risk" area (e.g. an off-by-one in
  pagination) is still worth catching; the high-risk-area rule adjusts
  severity, not whether review happens at all.

## Consequences

- Positive: every finding that survives is worth a human's attention,
  keeping trust in the tool high over time.
- Positive: clean separation of concerns with deterministic tooling means
  the AI reviewer's prompt doesn't need to be kept in sync with ruff's
  ruleset — they don't overlap by design.
- Negative: the prompt requires deliberate maintenance as new production
  incident patterns are discovered (see the Feedback Loop section of the
  README) — an unconstrained prompt wouldn't need this, but also wouldn't
  reliably catch the right things in the first place.
