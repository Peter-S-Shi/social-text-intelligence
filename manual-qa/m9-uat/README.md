# M9.1 synthetic UAT infrastructure

This directory is a versioned **instruction and recording tool**, not a completed
UAT session. The [M9 UAT protocol](../../docs/V2_M9_UAT_PROTOCOL.md) and
[evidence contract](../../docs/V2_M9_EVIDENCE_CONTRACT.md) govern actual M9.3
execution. All 49 required steps in a new session are `NOT RUN`. No expected
model label, screenshot, Windows accessibility result, or global Gate decision
is supplied.

Infrastructure verification is documented in [VALIDATION.md](VALIDATION.md).

## Reproduce locally

1. Open `index.html` in a browser directly from this directory. Its CSS and
   JavaScript are local files; no account, server, CDN, network call or upload
   is required. This browser check exercises only the recorder.
2. For **later authorized Windows UAT**, create disposable projects from
   `fixtures/feedback-v1.csv`; choose `message` as the text column. Its 12
   synthetic source rows include two `SYN-009` IDs, a blank `SYN-010` text,
   French text, and a formula-leading `source_label` marker. These are input
   fixtures, not predicted sentiment/emotion gold labels.
3. `python fixtures/make_long_text.py <disposable-output.txt>` writes
   deterministic synthetic long text for the capacity scenario; use a local
   disposable destination outside the repository and
   do not add session output to the repository.
4. For model, contention, storage-fault and accessibility scenarios, follow
   each step's precondition. Use only authorized existing pinned models and
   disposable app-data roots. Never exhaust the host disk. If a required setup
   is unavailable, leave its step `NOT RUN`; do not use `N/A` to fill progress.
5. Record actual environment and operator authorization before observed
   decisions. Use opaque `DEF-...` and `EVID-...` references. Export JSON
   regularly; browser local storage is a draft and may be cleared. Keep
   private exports local until a privacy review. The Markdown summary is a
   working report, never a formal PASS.

## Version and restore policy

The concrete field types, bounds and validation rules are in
[Recorder schema 1](SESSION_SCHEMA.md).

The protocol, scenario pack and fixture versions are `1.0.0`; the JSON session
schema is `1`. Stable IDs run `UAT-<FAMILY>-NN-SNN`. Import accepts only the
current exact schema and versions, with all 49 known steps in canonical order.
Unknown, duplicate or missing fields/steps, invalid statuses/metadata, unsafe
evidence references and oversized files are rejected without changing the
current draft. There is **no silent migration**: a later pack revision needs a
separate explicit migration or a new session while old JSON remains readable
as historical evidence with its matching tool version. Restore asks before
replacing the local draft. All imported progress is recomputed from validated
steps; stored totals or Gate decisions are not accepted.

This pack contains only project-authored `SYNTH_UAT` content. It is separate
from the historical [V1 questionnaire](../manual_review_questionnaire.html),
the STI desktop application, representative evaluation data and M10 packaging.

## Infrastructure checks

Run `node --test tests/manual_qa/test_m9_uat_core.cjs` from the repository root
and `python -m pytest tests/manual_qa/test_m9_uat_fixture.py` in the development
environment. For browser smoke, serve this directory on loopback port 8765 and
start Chrome with `--headless=new --remote-debugging-port=9223` and a fresh,
disposable `--user-data-dir` profile. Then run
`node tests/manual_qa/browser_smoke.cjs`. The script clears only that isolated
recorder profile's local draft, uses synthetic decisions, and saves a local
ignored narrow-view screenshot. It checks recorder interactions and DOM/AX
state, not desktop Windows or Narrator acceptance.
