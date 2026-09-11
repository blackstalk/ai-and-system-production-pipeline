# AI Review Strategy

## The core claim, stated precisely

AI code review is a useful, cheap, always-on layer for catching the kind of
contextual issue that deterministic tooling structurally cannot see (does
this authorization check actually check ownership? does this exception
handler hide a payment failure?). It is **not** a substitute for
deterministic tooling, and it is **not** a substitute for a human who is
accountable for the change. See
[ADR-001](adr/001-ai-review-is-not-authoritative.md) and
[ADR-002](adr/002-ai-review-focuses-on-production-risk.md).

## Division of labor

| Layer | Owns | Example |
|---|---|---|
| Ruff | Formatting, import order, trivial lint | Unused import, inconsistent quotes |
| mypy | Type correctness | Passing `str` where `int` expected |
| Bandit / pip-audit | Known vulnerability patterns and CVEs | Hardcoded password pattern, vulnerable dependency version |
| **AI reviewer** | Contextual/architectural reasoning tools can't pattern-match | "This authorization check verifies the caller is logged in but not that they own the resource" |
| **Human** | Business context, risk tolerance, final accountability | "This edge case is fine to ship because the feature is behind a flag" |

The full prompt the reviewer runs under is [`prompts/code-review.md`](../prompts/code-review.md).
It explicitly tells the model to ignore formatting, naming preferences, and
anything deterministic tooling already owns — an AI reviewer that repeats
what ruff already said is noise, and noisy reviewers get ignored, which
defeats the purpose.

## What the reviewer looks for

Summarized from the full prompt — see that file for the complete list:

- **Business logic** — incorrect assumptions, bad state transitions, missing
  validation, broken workflows, race conditions
- **Security** — injection, auth bypass, IDOR, unsafe deserialization,
  secrets exposure, insecure defaults, SSRF, path traversal
- **Reliability** — unhandled exceptions, missing timeouts/retries, resource
  leaks, non-idempotent operations, weak failure handling
- **Performance** — N+1 queries, unbounded loops/workloads, unnecessary
  network calls

High-risk areas (auth, payments, personal data, destructive operations, data
deletion, migrations, infrastructure, secrets, external integrations) are
treated as higher severity by default, because the blast radius of a mistake
there is larger than the same mistake in, say, a formatting utility.

## Output and severity

Findings are CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL, each with file,
line, category, explanation, production impact, and a specific remediation —
see the JSON schema in `prompts/code-review.md`. **CRITICAL/HIGH findings
fail the `AI Review` check; MEDIUM and below are posted as informational PR
comments and do not block merge.** This threshold exists so the check fails
on things worth blocking a merge for, not on every stylistic quibble a model
might raise — see [ADR-002](adr/002-ai-review-focuses-on-production-risk.md).

## Implementation

`.github/workflows/ai-review.yml` runs after `ci.yml` and `security.yml`,
calling `scripts/ai_review.py`. That script defines a small `Reviewer`
protocol:

```python
class Reviewer(Protocol):
    def review(self, diff: str, system_prompt: str) -> str: ...
```

`AnthropicReviewer` is the only implementation in this reference repo, but
swapping to OpenAI, CodeRabbit, or an in-house model means implementing this
one method — the workflow YAML and merge-gate logic don't change. The model
receives the PR diff (`examples/` is excluded from the diff sent to the
model, since it is intentionally vulnerable code that would generate noise)
plus the system prompt, and is asked to return the JSON finding array
directly.

## Failure modes and how they're handled

- **No API key configured** (e.g. a fork PR, or a repo that hasn't set the
  secret yet): the script exits 0 with an explanatory comment. An
  unavailable AI reviewer must never become a way to block all merges —
  deterministic checks and human review are unaffected.
- **Model returns unparseable output**: treated as a tooling failure, not a
  code signal. The check passes with a note; it does not block the merge on
  a model formatting mistake.
- **Model hallucinates a finding**: this is why the AI reviewer is one layer
  among several, not the merge gate — a human reviewer reading the PR
  comment can dismiss a wrong finding, the same way they'd dismiss a wrong
  lint suppression.

## Smoke-testing the reviewer

`examples/` contains five intentionally vulnerable snippets
(`examples/README.md` has the full list) specifically so anyone evaluating
this repo can copy one into a throwaway branch and confirm the reviewer
flags it at the expected severity.
