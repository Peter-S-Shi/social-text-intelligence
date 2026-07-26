# Moderation Training

Milestone 9 is an educational, local-first workflow for practicing structured
moderation decisions. It is not a platform enforcement system, expert
certification, psychological assessment, or model evaluation benchmark.

## Sources and provenance

The packaged policy and 20-case library are project-authored synthetic
resources:

- policy ID `sti-synthetic-moderation-training-policy`, version `1.0.0`;
- fixture version `1.0.0`;
- mock provider `sti-fixture-moderation-mock`, version `1.0.0`;
- stable case IDs and stable policy clause IDs.

The mock provider performs fixture lookup only. It does not load a model,
interpret text, call a remote service, or create independent expert advice.
Mock availability is deliberately incomplete so the UI and summary denominators
handle unavailable advice explicitly.

Reference provenance has three contract values:

- `built_in`: repository synthetic case/reference;
- `self_authored`: the current user prepared the reference and then trained
  against it in the same local workspace;
- `user_authored`: reserved for a future external author or policy provider.

The M9 UI creates only `self_authored` workspace references and explicitly says
they are not independent review.

## Decision contract

A complete judgment records:

- disposition: Allow, Warn, Remove, or Unclear / Needs Review;
- primary violation and optional unique secondary violations;
- severity: None, Low, Medium, High, or Critical;
- escalation choice and required reason when selected;
- at least one unclear reason for Unclear / Needs Review;
- required reasoning and reviewer note for every trainee submission.

Structural errors reject submission. Examples include missing required fields,
Warn or Remove without a violation, `No violation` combined with another
category, a primary category repeated as secondary, escalation without a reason,
Unclear without a reason, contradictory reason fields, duplicates, and illegal
enumeration values.

Policy-guidance warnings are separate and non-blocking. Examples include Allow
with a violation, Critical without escalation, High/Critical with a light
disposition, `No violation` with non-None severity, and other departures from
the ordinary synthetic-policy default. The workflow never automatically changes
or prohibits these decisions. It displays and retains their reasoning, reviewer
note, and warning codes.

## Workflow

### Prepare

The user can filter the built-in library by category, difficulty, ambiguity,
learning objective, and safety sensitivity. A completed temporary batch can be
linked by token. Only successfully analyzed records are eligible for explicit
snapshot preparation.

A workspace snapshot freezes the complete record or a literal user-selected
excerpt, source provenance, allowlisted metadata, sentiment and emotion model
identity/revision, separate human review, and applicable context notes.
Workspace references are optional and unreferenced cases are explicitly
unscored.

### Train

A session uses explicit case selection or a deterministic balanced sample. It
supports independent and synthetic-mock-assisted modes, immediate and
end-of-session feedback, and random, difficulty-progressive, or original order.
A concise sensitive-content notice must be confirmed when applicable.

The session freezes each case, policy ID/version, reference, and policy clause
IDs. The first submitted decision is immutable. After feedback is explicitly
viewed, an optional revision creates a separate final decision. Cancelling
preserves partial attempts; restarting creates a new session attempt.

### Review

Comparison distinguishes:

- exact preferred-reference match;
- complete acceptable alternative;
- disagreement;
- explicitly unscored.

Disposition, primary category, severity, and escalation are shown separately.
Educational flags identify specific patterns such as critical escalation misses,
over-enforcement, high-severity under-enforcement, unnecessary escalation, false
certainty under insufficient context, and confusing negative sentiment with a
policy violation.

Summaries expose raw numerators, eligible denominators, excluded counts, and the
configured insight sample warning. Trainee–mock agreement is labeled as
agreement, not accuracy. No composite score, ranking, certification, or
calibration claim is produced.

## Limits and lifecycle

The configurable defaults are:

- 100 prepared cases;
- 50 cases in one training session;
- 20 retained session attempts in one training workspace.

All state is process memory only and shares an inactivity-expiry model with
existing temporary workflows. Reaching a limit blocks creation and tells the
user to export and explicitly clear the workspace, or wait for expiry. No old
case, attempt, summary, or workspace is silently overwritten or evicted.
Use `sti-web --max-prepared-cases`, `--max-session-cases`, and
`--max-session-attempts` to change the defaults for one local process.

## Export

CSV export starts with a timezone-aware UTC audit row and includes policy,
fixture/mock identity, mode, feedback timing, case/completion/scored/excluded
counts, configured sample thresholds, and metric definitions. Separate metric
rows preserve numerator, denominator, excluded count, rate, and sample warning.
Case rows preserve first and final structured decisions, reasoning, reviewer
notes, guidance warnings, reference provenance, acceptable alternatives, mock
recommendation, comparison states, educational flags, and timestamps.

Built-in synthetic case text is included. User-derived source text, model
signals, context notes, and trusted metadata are excluded by default and require
explicit opt-in. Formula-like user-controlled cells are escaped and responses
use `Cache-Control: no-store`.

## Explicit non-goals

Milestone 9 adds no live moderation model, LLM, automatic enforcement, platform
action, support triage, persistence, background workflow, account system,
French capability, platform connector, or new dependency.
