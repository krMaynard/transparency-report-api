#!/usr/bin/env python3
"""Post a Gemini-generated code review on the current pull request.

A free, self-contained approximation of the (sunsetting) Gemini Code Assist
review bot: it sends the PR diff to a Gemini model via the Google AI Studio
REST API (free tier) and posts the model's review back as a single *sticky* PR
comment — updated in place on every push, so it never spams the thread.

Runtime deps: none beyond the Python standard library + the `gh` CLI (both
present on GitHub-hosted runners). Everything is configured via environment
variables so the workflow stays declarative:

  GEMINI_API_KEY      (required)  AI Studio API key. If unset, the script
                                  no-ops with a notice (so PRs aren't blocked
                                  before the secret is configured).
  GH_TOKEN            (required)  Token for the `gh` CLI (github.token is fine).
  PR_NUMBER           (required)  The pull-request number to review.
  GITHUB_REPOSITORY   (required)  "owner/repo" — set automatically by Actions.
  GEMINI_MODEL        (optional)  Model id, default "gemini-2.5-flash". Override
                                  with e.g. "gemini-2.5-flash-lite" (higher free
                                  quota) or "gemini-flash-latest" if the free
                                  lineup has advanced past 2.5.
  MAX_DIFF_CHARS      (optional)  Diff truncation cap, default 200000.

The script is deliberately *advisory*: any Gemini/API failure logs a warning
and exits 0, so a rate-limit or outage never turns into a red required check.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

# Hidden marker used to find (and update) our own prior comment.
MARKER = "<!-- gemini-review -->"
API_HOST = "https://generativelanguage.googleapis.com"

PROMPT = """\
You are reviewing a GitHub pull request for the transparency-report-api
project — a FastAPI service that compiles validated, structured query
parameters (never raw SQL) into parameterised SQLite SELECTs and serves
transparency-reporting datasets.

Review the unified diff below. Focus, in priority order, on:
1. Correctness bugs — especially in `compile_query` / `_compile_composite`
   (the single SQL trust boundary) and any new `TableSpec`.
2. The no-SQL invariant: no user value may be interpolated into SQL; every
   value must be bound with `?` and validated against a table's field registry.
3. New or changed dataset seeders: double-count / `is_total` handling, mixing
   units in SUM/AVG, and the `_leg_warnings` guards.
4. If any `static/*.html` changed: whether the localized copies
   (es/fr/de/it/ja/zh/ko) were regenerated via scripts/localize_static.py and
   the per-page CSP inline-script hashes are current.
5. Security: SSRF guards on callback URLs, CSV formula-injection, auth scoping.

Report only concrete, verifiable findings, most severe first. For each, give
the file, a one-line description, and a suggested fix. If the diff is clean,
say so briefly — do not invent nits. Keep the whole review under ~400 words of
GitHub-flavoured Markdown.
"""


def run(cmd: list[str]) -> str:
    """Run a command, returning stdout; raises on non-zero exit."""
    return subprocess.run(
        cmd, check=True, capture_output=True, text=True
    ).stdout


def gh_api(args: list[str]) -> str:
    return run(["gh", "api", *args])


def notice(msg: str) -> None:
    print(f"::notice::{msg}")


def warn(msg: str) -> None:
    print(f"::warning::{msg}")


def call_gemini(model: str, api_key: str, diff: str) -> str:
    """Send the diff to Gemini and return the review text."""
    url = f"{API_HOST}/v1beta/models/{model}:generateContent"
    body = json.dumps(
        {
            "contents": [
                {"parts": [{"text": PROMPT + "\n\n---\nDIFF:\n\n" + diff}]}
            ],
            # Low temperature keeps the review deterministic and terse.
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.load(resp)

    # A safety-blocked or empty completion carries no usable candidate.
    candidates = payload.get("candidates") or []
    if not candidates:
        raise RuntimeError(
            f"Gemini returned no candidates: {json.dumps(payload)[:500]}"
        )
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise RuntimeError("Gemini returned an empty review")
    return text


def find_sticky_comment(repo: str, pr: str) -> str | None:
    """Return the id of our prior review comment, if one exists."""
    raw = gh_api(
        [
            f"repos/{repo}/issues/{pr}/comments",
            "--paginate",
            "-q",
            f'.[] | select(.body | contains("{MARKER}")) | .id',
        ]
    )
    ids = raw.split()
    return ids[0] if ids else None


def upsert_comment(repo: str, pr: str, body: str) -> None:
    """Create the review comment, or update ours in place if it exists."""
    full = f"{MARKER}\n{body}"
    existing = find_sticky_comment(repo, pr)
    if existing:
        gh_api(
            [
                "--method",
                "PATCH",
                f"repos/{repo}/issues/comments/{existing}",
                "-f",
                f"body={full}",
            ]
        )
        notice(f"Updated existing review comment {existing}")
    else:
        gh_api(
            [
                "--method",
                "POST",
                f"repos/{repo}/issues/{pr}/comments",
                "-f",
                f"body={full}",
            ]
        )
        notice("Posted new review comment")


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY")
    pr = os.environ.get("PR_NUMBER")
    repo = os.environ.get("GITHUB_REPOSITORY")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    max_chars = int(os.environ.get("MAX_DIFF_CHARS", "200000"))

    if not api_key:
        notice("GEMINI_API_KEY is not set — skipping Gemini review.")
        return 0
    if not pr or not repo:
        warn("PR_NUMBER / GITHUB_REPOSITORY not set — cannot run.")
        return 0

    diff = run(["gh", "pr", "diff", pr])
    if not diff.strip():
        notice("Empty diff — nothing to review.")
        return 0
    if len(diff) > max_chars:
        warn(f"Diff is {len(diff)} chars; truncating to {max_chars} for review.")
        diff = diff[:max_chars] + "\n\n[... diff truncated for review ...]"

    try:
        review = call_gemini(model, api_key, diff)
    except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError) as exc:
        detail = ""
        if isinstance(exc, urllib.error.HTTPError):
            detail = exc.read().decode(errors="replace")[:500]
        # Advisory: never fail the PR on a review error (rate limit, outage, …).
        warn(f"Gemini review skipped — API error: {exc} {detail}")
        return 0

    footer = (
        f"\n\n---\n_🔷 Automated review by `{model}` (Gemini free tier). "
        "Advisory — verify each finding before acting._"
    )
    upsert_comment(repo, pr, review + footer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
