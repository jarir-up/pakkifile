# ADR-0046: How the weekly registry job publishes

- Status: Proposed
- Approved by: Not yet approved.

## Context
ADR-0030 has a scheduled job open pull requests and merge entries that pass the auto-publish rule. Real runs raise questions it doesn't settle: a date-only pull request every week is noise, model output is not yet good enough to merge unread, and pull requests opened with the built-in token do not trigger CI.

## Decision
Proposed:
- New and unchanged sources' dates and first checksums are committed directly to `main` after the checks pass.
- A changed source produces `registry-data/proposals/<source id>.yaml`, holding the extracted requirements, on one pull request from the `registry/proposals` branch. The source's new checksum goes with it. While that pull request is open, the source is not proposed again.
- A maintainer updates the entries by hand and deletes the proposal. Nothing merges automatically until the extraction evaluation passes its gates consistently.
- The job runs the checks itself, and reports the evaluation in the pull request body.
- The repository allows GitHub Actions to create pull requests.
- `extraction-eval` runs the real model on pull requests that change the prompt, the labels or the scorer. Other pull requests run no model.

## Consequences
Quiet weeks add one small commit to `main`, which also keeps scheduled workflows from being disabled after 60 days. Humans read every proposal for now, so auto-merge from ADR-0030 is deferred, not dropped. Registry pull requests carry no `gates` check run, because the built-in token cannot trigger one.
