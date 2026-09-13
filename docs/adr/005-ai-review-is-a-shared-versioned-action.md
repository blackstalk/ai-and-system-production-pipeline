# ADR-005: AI Review Is a Shared, Versioned Action, Not Embedded Logic

## Status

Accepted

## Context

The AI review layer (a system prompt plus a script that calls an LLM API,
parses findings, and posts a PR comment) started as `prompts/code-review.md`
and `scripts/ai_review.py` inside this repo. That worked fine as long as
this was the only repo using it. It stopped being the right shape once the
goal changed to applying the same pipeline across multiple repos and
multiple stacks (this repo's Python/FastAPI service today; PHP repos and
future ML projects going forward) — the review logic itself is
stack-agnostic (it only ever operates on a `git diff`), but embedding it in
one application repo meant every other repo wanting it would either
copy-paste the script and prompt (immediately out of sync the moment either
changed) or depend on reaching into this repo's internals in a way GitHub
Actions doesn't really support cleanly.

## Decision

Extract the review engine, prompt, and composite action definition into
[`blackstalk-labs/ai-review-action`](https://github.com/blackstalk-labs/ai-review-action),
a standalone, independently versioned (semver-tagged) repo. This repo
consumes it the same way any other repo would:

```yaml
- uses: blackstalk-labs/ai-review-action@v1
  with:
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    base-ref: origin/${{ github.event.pull_request.base.ref }}
    exclude-paths: examples
    system-prompt-path: prompts/code-review.md
```

The action's default system prompt is stack-agnostic; this repo overrides
it via `system-prompt-path` with a version that adds references to its own
deterministic tooling (ruff, mypy, Bandit, pip-audit) and its own ADRs —
demonstrating that per-repo customization on top of a shared base is a
first-class use case, not a workaround.

## Alternatives considered

- **Keep the script embedded in this repo; other repos copy it.** Rejected:
  a fix or prompt improvement made in one copy doesn't reach the others.
  Given the explicit goal of using this across a PHP codebase now and
  Python/ML repos later, copy-drift was going to happen immediately, not
  eventually.
- **A shared library/package (e.g. a PyPI package) imported by each repo's
  own workflow script.** Rejected for the cross-language goal specifically:
  a Python package doesn't help a PHP repo at all, whereas a GitHub Action
  is invoked the same way (`uses:`) regardless of the consuming repo's
  language.
- **A reusable GitHub Actions workflow (`workflow_call`)** instead of a
  composite action. Considered, but a composite action is the better fit
  here: this is a single reusable *step* (call an LLM, post a comment) that
  slots into a job a consuming repo already owns and controls, not an
  entire job/pipeline a consumer would have to adopt wholesale. Consuming
  repos keep their own `ci.yml`/`security.yml` shape entirely; they only
  delegate the AI-review step.

## Consequences

- Positive: one source of truth for the reviewer prompt and logic. A bug
  fix or new provider implementation in `ai-review-action` benefits every
  consuming repo without a sync step.
- Positive: genuinely stack-agnostic — the same action works unmodified for
  a PHP repo (`exclude-paths: vendor`) and a Python repo
  (`exclude-paths: tests`), since it only operates on the diff.
- Positive: per-repo customization via `system-prompt-path` (and
  `fail-on-severity`, `exclude-paths`) means "shared" doesn't mean "rigid."
- Negative: introduces a cross-repo dependency and a versioning discipline
  this repo didn't previously need — bumping `ai-review-action` from `@v1`
  to a new major version now requires deliberate action here, the same way
  any third-party Action dependency does.
