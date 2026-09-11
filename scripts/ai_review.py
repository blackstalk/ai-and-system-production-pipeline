#!/usr/bin/env python3
"""AI-assisted PR review — reference implementation.

Reads a unified diff, sends it to an LLM alongside the reviewer system
prompt in prompts/code-review.md, and prints:

  1. A markdown summary suitable for posting as a PR comment.
  2. A machine-readable summary line used by the calling workflow to
     decide whether to fail the check (see .github/workflows/ai-review.yml
     and docs/ai-review-strategy.md).

Design notes
------------
The `Reviewer` protocol below is the extension point referenced in
README.md: swapping providers (Claude, OpenAI, CodeRabbit, an in-house
model) means implementing one method, not touching the workflow YAML or
the merge-gate logic. `AnthropicReviewer` is the only implementation
provided; it depends on nothing beyond the standard library so this
script needs no extra install step in CI.

No API key, no crash
---------------------
If ANTHROPIC_API_KEY is unset, `main()` exits 0 with a clear message
instead of failing the workflow — an AI reviewer being unavailable must
never become a way to block all merges. Deterministic checks (ci.yml,
security.yml) and human review remain the required gates regardless.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Protocol

REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = REPO_ROOT / "prompts" / "code-review.md"

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]
BLOCKING_SEVERITIES = {"CRITICAL", "HIGH"}


class Reviewer(Protocol):
    def review(self, diff: str, system_prompt: str) -> str:
        """Return the raw model response (expected to be a JSON array)."""
        ...


class AnthropicReviewer:
    """Calls the Anthropic Messages API directly over HTTPS.

    Uses raw urllib rather than the `anthropic` SDK so this script has
    zero third-party dependencies and can run in any CI image.
    """

    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def review(self, diff: str, system_prompt: str) -> str:
        body = {
            "model": self._model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Review this pull request diff. Respond with the "
                        "JSON array described in your instructions, nothing "
                        f"else.\n\n```diff\n{diff}\n```"
                    ),
                }
            ],
        }
        request = urllib.request.Request(
            self.API_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": self.API_VERSION,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic API error {exc.code}: {detail}") from exc

        return "".join(
            block.get("text", "")
            for block in payload.get("content", [])
            if block.get("type") == "text"
        )


def get_diff(base_ref: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", "diff", f"{base_ref}...HEAD", "--", ".", ":!examples"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def parse_findings(raw_response: str) -> list[dict[str, Any]]:
    text = raw_response.strip()
    # Models sometimes wrap JSON in a fenced code block despite instructions.
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[len("json") :]
    findings = json.loads(text)
    if not isinstance(findings, list):
        raise ValueError("Expected the model to return a JSON array of findings.")
    return findings


def render_markdown(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return (
            "## AI Review\n\nNo findings. This is one signal among several — "
            "see [docs/ai-review-strategy.md](../docs/ai-review-strategy.md)."
        )

    findings_sorted = sorted(
        findings, key=lambda f: SEVERITY_ORDER.index(f.get("severity", "INFORMATIONAL"))
    )
    lines = ["## AI Review", ""]
    blocking = [f for f in findings_sorted if f.get("severity") in BLOCKING_SEVERITIES]
    if blocking:
        lines.append(
            f"**{len(blocking)} blocking finding(s)** (CRITICAL/HIGH) — "
            "this check will fail until resolved or explicitly overridden by a human reviewer."
        )
    else:
        lines.append("No CRITICAL/HIGH findings. Lower-severity items below are informational.")
    lines.append("")

    for finding in findings_sorted:
        severity = finding.get("severity", "INFORMATIONAL")
        severity_emoji = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🔵",
            "INFORMATIONAL": "⚪",
        }
        emoji = severity_emoji.get(severity, "⚪")
        lines.append(
            f"### {emoji} {severity} — {finding.get('category', 'uncategorized')} — "
            f"`{finding.get('file', 'unknown')}:{finding.get('line', '?')}`"
        )
        lines.append(f"**{finding.get('summary', '')}**")
        lines.append("")
        lines.append(finding.get("explanation", ""))
        lines.append("")
        lines.append(f"- **Production impact:** {finding.get('production_impact', 'n/a')}")
        lines.append(f"- **Suggested remediation:** {finding.get('remediation', 'n/a')}")
        lines.append("")

    return "\n".join(lines)


def build_reviewer() -> Reviewer | None:
    provider = os.getenv("AI_REVIEW_PROVIDER", "anthropic").lower()
    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        model = os.getenv("AI_REVIEW_MODEL", "claude-sonnet-5")
        return AnthropicReviewer(api_key=api_key, model=model)

    raise NotImplementedError(
        f"AI_REVIEW_PROVIDER={provider!r} is not implemented in this reference repo. "
        "Implement the Reviewer protocol (see AnthropicReviewer above) to add OpenAI, "
        "CodeRabbit, or another provider without changing the workflow or merge-gate logic."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", default=os.getenv("BASE_REF", "origin/main"))
    parser.add_argument("--output", default="ai-review-comment.md")
    args = parser.parse_args()

    reviewer = build_reviewer()
    if reviewer is None:
        print(
            "ANTHROPIC_API_KEY is not set — skipping AI review. This check is "
            "advisory-only and never the sole merge gate "
            "(see docs/adr/001-ai-review-is-not-authoritative.md)."
        )
        Path(args.output).write_text(
            "## AI Review\n\nSkipped: no API key configured for this run. "
            "Deterministic checks and human review remain required.\n"
        )
        return 0

    diff = get_diff(args.base_ref)
    if not diff.strip():
        print("Empty diff — nothing to review.")
        Path(args.output).write_text("## AI Review\n\nNo reviewable changes in this diff.\n")
        return 0

    system_prompt = PROMPT_PATH.read_text()
    raw_response = reviewer.review(diff=diff, system_prompt=system_prompt)

    try:
        findings = parse_findings(raw_response)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Could not parse AI reviewer output as JSON: {exc}", file=sys.stderr)
        print(f"Raw response:\n{raw_response}", file=sys.stderr)
        Path(args.output).write_text(
            "## AI Review\n\nThe reviewer returned an unparseable response this run. "
            "Treat this as a tooling failure, not a signal about the code — "
            "deterministic checks and human review still apply.\n"
        )
        # A malformed model response should not block merges by itself.
        return 0

    Path(args.output).write_text(render_markdown(findings))

    blocking = [f for f in findings if f.get("severity") in BLOCKING_SEVERITIES]
    for finding in blocking:
        print(
            f"::error file={finding.get('file')},line={finding.get('line')}::"
            f"[{finding.get('severity')}] {finding.get('summary')}"
        )

    if blocking:
        print(f"{len(blocking)} blocking (CRITICAL/HIGH) finding(s). Failing this check.")
        return 1

    print("No blocking findings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
