# Intentionally Vulnerable Examples

These files are **intentionally insecure** and exist purely to demonstrate what
the layered defenses in this repository — the AI reviewer
([`prompts/code-review.md`](../prompts/code-review.md)), Bandit, and human
review — are expected to catch.

**None of this code is imported by, or reachable from, the running
application.** `tests/security/test_examples_are_isolated.py` fails CI if
anything under `app/` ever imports from `examples/`, and `pyproject.toml`
excludes this directory from `ruff` and `mypy`.

Each snippet is deliberately minimal and paired with a comment describing the
vulnerability class and what a correct fix looks like.

| File | Vulnerability class | Severity a reviewer should assign |
|---|---|---|
| [`sql_injection.py`](sql_injection.py) | SQL injection via string-formatted query | CRITICAL |
| [`missing_authorization.py`](missing_authorization.py) | Missing authorization / broken access control | CRITICAL |
| [`n_plus_one_query.py`](n_plus_one_query.py) | N+1 query performance defect | MEDIUM |
| [`swallowed_exception.py`](swallowed_exception.py) | Silently swallowed exception hides failures | HIGH |
| [`unsafe_delete.py`](unsafe_delete.py) | Destructive operation without safeguards | CRITICAL |

## Why this exists

A reviewer of this repository — human or AI — should be able to point at
these five files and immediately see the categories of defects the pipeline
is designed to catch before they reach production. If you're evaluating the
AI review workflow (`.github/workflows/ai-review.yml`), a good smoke test is
opening a draft PR that copies one of these snippets into `app/` and
confirming the reviewer flags it at the severity listed above.
