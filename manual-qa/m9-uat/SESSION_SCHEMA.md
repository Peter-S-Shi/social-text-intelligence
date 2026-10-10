# Recorder schema 1

Protocol, scenario-pack and fixture version: `1.0.0`. JSON uses exact field sets,
not extensible dictionaries. Unsupported versions require a separate explicit
migration; this recorder rejects them. No totals or overall Gate decision are
stored or imported. All 49 steps are required and start `NOT RUN`.

| Object | Fields and bounds |
| --- | --- |
| Session | `schema_version`: integer 1; `session_id`: 1–64 ASCII letters/digits/hyphens; `protocol_version`, `pack_version`, `fixture_version`: exact strings; `created_at`, `updated_at`: UTC ISO timestamp with milliseconds; `authorization_ref`: string ≤120; `environment`, `results`, `retests` |
| Environment | `tested_sha`: empty before execution or exactly 40 hex characters; `os`, `python`, `qt`, `platform`, `scale`, `text_size`, `window_width`, `narrator`, `high_contrast`, `operator_role`: strings ≤120 |
| Step | `step_id`: exact known ID in canonical order; `status`: `NOT RUN`, `PASS`, `FAIL`, `N/A`; `observed_action`, `observed_outcome`, `rationale`, `na_reason`, `defect_id`, `evidence_ref`, `severity`, `blocking_status`: strings ≤500; `note`: string ≤2000; `history`: at most 50 prior snapshots |
| Failure | `defect_id`: `DEF-` plus 1–48 uppercase letters/digits/hyphens; `severity`: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`; `blocking_status`: `BLOCKING`, `NON_BLOCKING`, `UNDECIDED`; nonempty rationale required. Classification does not establish owner acceptance of a non-blocking finding |
| History snapshot | All decision fields above, plus `replaced_at` UTC timestamp; original failure evidence is retained and appears in JSON and Markdown |
| Retest | At most 200 entries; known `step_id`, matching current/historical FAIL `defect_id`; `classification`: `PRODUCT`, `FIXTURE`, `ENVIRONMENT`, `PROTOCOL`; `blocking_rationale` nonempty ≤500; `automated_check` ≤500; `fix_sha` empty or 40 hex characters; `tested_at` UTC timestamp; `outcome`: `PASS` or `FAIL`; required `evidence_ref`; `note` ≤2000 |

PASS/FAIL require observed action and outcome. N/A requires a genuine
applicability reason; known unavailable-setup wording is rejected, and human
review must assess the reason. A required unavailable setup remains NOT RUN.
Any current or historical observation requires complete environment and
authorization metadata. The UI locks session provenance after the first
observation, including after a decision is reset to NOT RUN. A different
application SHA/environment needs a new session; retests carry their own fix SHA.

Import is bounded to 1 MiB, rejects excessive nesting, duplicate JSON members,
unknown/missing fields, duplicate/unknown steps, malformed types/statuses,
invalid history and invalid references before replacement. Evidence references
use `EVID-` plus 1–48 uppercase letters/digits/hyphens. Control characters,
recognized local paths, email addresses and credential-bearing URLs are rejected
in text fields. This is a guardrail, not an exhaustive privacy classifier or a
tamper-proof signature. Keep exports local and inspect them before publication.

The UI renders text through DOM text properties. Markdown escapes user text and
flattens embedded newlines. No imported content is executed or fetched. Draft
storage can fail or be cleared; JSON export is necessary for durable evidence.
Unsaved form edits prompt before navigation/replacement. Infrastructure smoke
records use synthetic observations and do not constitute Windows UAT evidence.
