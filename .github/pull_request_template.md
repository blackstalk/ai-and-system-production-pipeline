## What does this change do?

<!-- One or two sentences. Assume the reader has no context. -->

## What could break?

<!-- Name the specific failure mode you're most worried about, not "nothing should break." -->

## Risk checklist

- [ ] Touches authentication or authorization
- [ ] Modifies persistent data (schema, migration, or write path)
- [ ] Deletes or destroys data
- [ ] Adds a new external dependency or third-party integration
- [ ] Touches secrets, credentials, or configuration defaults

If any box is checked, explain the specific risk and mitigation below.

## Tests

<!-- What did you add or change? Why do these tests prove the change is correct? -->

## Rollback plan

<!-- If this ships a bug, what is the fastest safe way to undo it? -->

## Metrics to watch after deploy

<!-- Which dashboard/metric would show this change misbehaving? e.g. error rate on POST /api/items, p95 latency, a specific log query. -->

---

*This template exists because [ADR-004](../docs/adr/004-human-remains-final-decision-maker.md) makes the human author accountable for these answers — AI review and CI checks are additional layers, not a substitute for them. See [docs/ai-review-strategy.md](../docs/ai-review-strategy.md) for how automated review fits into this.*
