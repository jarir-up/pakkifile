#!/usr/bin/env python3
"""CI gate: a second model reviews the pull request diff against docs/RULES.md.

The model that wrote the code always believes it followed the rules, so the
reviewer is a different model with no access to the author's reasoning.
Blocks the merge on any violation the owner hasn't waived in the PR
description with a line like `waive R-07: <reason>`.

Standard library only, so CI needs no install step.
Env: ANTHROPIC_API_KEY (required), RULES_GATE_MODEL, BASE_REF, MAX_DIFF_CHARS.
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
# Reviewer must differ from the model that writes the code. Coding with Opus?
# Review with Sonnet, or point this at another vendor's model for wider coverage.
DEFAULT_MODEL = "claude-sonnet-5-5"
WAIVER = re.compile(r"^\s*waive\s+(R-\d+)\s*:\s*(\S.*)$", re.IGNORECASE | re.MULTILINE)

REPORT_TOOL = {
    "name": "report",
    "description": "Report every rule violation found in the diff. Report an empty list if there are none.",
    "input_schema": {
        "type": "object",
        "properties": {
            "violations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "rule": {"type": "string", "description": "Rule ID, e.g. R-05"},
                        "file": {"type": "string"},
                        "line": {
                            "type": "integer",
                            "description": "Line number in the new file, or 0 if not applicable",
                        },
                        "evidence": {
                            "type": "string",
                            "description": "The offending code, at most a few lines",
                        },
                        "why": {
                            "type": "string",
                            "description": "One sentence on how this breaks the rule",
                        },
                    },
                    "required": ["rule", "file", "line", "evidence", "why"],
                },
            }
        },
        "required": ["violations"],
    },
}

INSTRUCTIONS = """You are the merge gate for a pull request. Check the diff against the project rules below.

- Judge only lines the diff adds or changes. Existing code outside the diff is not on trial.
- Report a violation only when the diff itself shows it. If you would need to guess, don't report it.
- Ignore rules marked (retired).
- Cite the exact rule ID for each violation.
- Call the report tool exactly once, with an empty list if the diff is clean."""


def parse_waivers(pr_body):
    """Map rule ID to reason for each `waive R-xx: reason` line."""
    return {rule.upper(): reason.strip() for rule, reason in WAIVER.findall(pr_body or "")}


def split_by_waiver(violations, waivers):
    blocking = [v for v in violations if v["rule"].upper() not in waivers]
    waived = [v for v in violations if v["rule"].upper() in waivers]
    return blocking, waived


def call_reviewer(rules, diff, model, api_key):
    body = {
        "model": model,
        "max_tokens": 8000,
        "tools": [REPORT_TOOL],
        "tool_choice": {"type": "tool", "name": "report"},
        "messages": [
            {
                "role": "user",
                "content": f"{INSTRUCTIONS}\n\n<rules>\n{rules}\n</rules>\n\n<diff>\n{diff}\n</diff>",
            }
        ],
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        payload = json.load(response)
    for block in payload.get("content", []):
        if block.get("type") == "tool_use" and block.get("name") == "report":
            return block["input"]["violations"]
    raise RuntimeError("Reviewer returned no report.")


def format_report(blocking, waived, waivers):
    lines = []
    for v in blocking:
        lines.append(
            f"- **{v['rule']}** `{v['file']}:{v['line']}` {v['why']}\n  ```\n  {v['evidence']}\n  ```"
        )
    for v in waived:
        lines.append(
            f"- ~~{v['rule']}~~ `{v['file']}:{v['line']}` waived: {waivers[v['rule'].upper()]}"
        )
    return "\n".join(lines)


def pr_body_from_event():
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path or not os.path.exists(path):
        return ""
    with open(path) as f:
        return (json.load(f).get("pull_request") or {}).get("body") or ""


def write_summary(text):
    print(text)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write(text + "\n")


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set; the rules gate cannot run.")
    model = os.environ.get("RULES_GATE_MODEL") or DEFAULT_MODEL
    base = os.environ.get("BASE_REF", "main")
    max_chars = int(os.environ.get("MAX_DIFF_CHARS", "150000"))

    with open("docs/RULES.md") as f:
        rules = f.read()
    diff = subprocess.run(
        ["git", "diff", f"origin/{base}...HEAD"], capture_output=True, text=True, check=True
    ).stdout
    if not diff.strip():
        write_summary("Rules gate: empty diff, nothing to review.")
        return
    if len(diff) > max_chars:
        # Truncating would let violations past unseen, so fail instead.
        write_summary(
            f"Rules gate: diff is {len(diff)} chars, over the {max_chars} limit. Split this PR into smaller tasks."
        )
        sys.exit(1)

    try:
        violations = call_reviewer(rules, diff, model, api_key)
    except (urllib.error.URLError, RuntimeError, KeyError) as e:
        # An unreachable reviewer must not count as approval.
        write_summary(f"Rules gate could not get a review from {model}: {e}")
        sys.exit(1)

    waivers = parse_waivers(pr_body_from_event())
    blocking, waived = split_by_waiver(violations, waivers)
    status = "FAILED" if blocking else "passed"
    write_summary(
        f"## Rules gate {status} ({model})\n\n{format_report(blocking, waived, waivers) or 'No violations.'}"
    )
    if blocking:
        sys.exit(1)


if __name__ == "__main__":
    main()
