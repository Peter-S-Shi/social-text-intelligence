# Support Triage

Milestone 10 is a local, human-led workbench for structuring support-triage
decisions. It is not a CRM, ticketing platform, response generator, routing
automation, SLA system, or model benchmark.

## Sources and provenance

The packaged `sti-synthetic-support-triage-guide@1.0.0` and its 22 tickets are
project-authored synthetic fixtures. They do not reproduce a real company's
policies, queues, SLA, legal duties, handbook, customers, or tickets. Stable
guide rules and ticket IDs provide auditable provenance.

Users may explicitly select successfully parsed records from one current batch
workspace. NLP analysis success is not required. A snapshot preserves a complete
source record or literal bounded excerpt and separately freezes any available
trusted metadata, sentiment/emotion signals, M7 human review, and M8 context
notes. These fields are supporting context only and never become automatic
triage verdicts. Triage does not mutate earlier milestone state.

Batch Results provides a linked `Prepare Support Triage` entry that carries the
active temporary batch token. A cleared or expired token fails safely. This is
the normal route for exercising workspace-derived tickets and their independent
privacy export opt-ins.

## Human decision and lifecycle

The human records:

- one primary and up to two secondary intents;
- one issue category;
- Low, Normal, High, Critical, or Unclear urgency;
- one recommended queue;
- escalation and a required reason when selected;
- one primary and up to two secondary recommended next actions;
- conditional unclear explanations and human notes.

Urgency reflects relative impact, time sensitivity, and possible risk. It is not
sentiment intensity, a confirmed incident, a response-time guarantee, or SLA.
Queue and action fields are recommendations only; they do not represent
assignment, transfer, dispatch, completion, refund, cancellation, or recovery.

The only statuses are Untriaged, Draft, and Finalized. Save Draft is explicit and
allows incomplete but legal fields. Finalize atomically validates the complete
decision, freezes guide identity and rules, and stores an immutable first
decision. Explicit revision validates a separate current final decision and
increments the revision count. Failed validation never partially mutates state.

Structural errors remain separate from non-blocking synthetic-guide warnings.
Warnings do not rewrite human judgment, but remain visible and auditable and
require a human note.

## Deterministic mock boundary

The application includes no real support classifier or LLM. Built-in mocks are
fixed fixture values; workspace mocks are explicitly same-user authored.
Independent mode hides a mock before first finalize. Assisted simulation may
show the deterministic mock first, but the human form starts empty and is never
prefilled.

When no mock exists, the ticket explicitly reports it as unavailable. Assisted
copy never claims a visible suggestion in that state, and unavailable tickets
remain outside both visible-before and hidden-before counts.

First and final comparisons report six distinct fields: primary intent, issue
category, urgency, recommended queue, escalation, and primary next action.
Differences are overrides. Agreement is descriptive, never accuracy, correctness,
quality, causal effect, productivity, or certification.

## Summary and export

Summaries disclose total eligible, synthetic/workspace provenance, Untriaged,
Draft, Finalized, and excluded counts. Finalized distributions exclude drafts
and untriaged tickets. Mock-unavailable tickets remain in human distributions
but are excluded from mock-comparison denominators. Follow-up reasons overlap
and are never collapsed into a risk or quality score.

Existing sample semantics apply independently to each metric's eligible
denominator: finalized human distributions use only finalized tickets, while
each first/final human-mock agreement metric uses only finalized tickets with
an available mock. Fewer than five shows counts without percentage emphasis,
five through nine shows a small-sample warning, and ten or more permits ordinary
descriptive percentages. Finalized-distribution and mock-comparison notices are
shown separately.

A mock is recorded as visible before first submission only when a suggestion is
available and the workspace is in mock-assisted mode. Finalized tickets without
a mock are explicitly unavailable and enter neither the visible nor hidden
count.

CSV export contains UTC audit metadata, guide provenance, lifecycle fields,
warnings, mock provenance, first/final comparisons, raw numerators,
denominators, exclusions, and sample status. Built-in synthetic ticket text may
be included by default. Workspace source text, NLP signals, human review,
context notes, and trusted metadata are separate explicit opt-ins. Formula-like
user-controlled cells are escaped and the response is `Cache-Control: no-store`.

## Limits and non-goals

Defaults are 200 tickets per workspace, eight concurrent workspaces, and a
30-minute sliding inactivity expiry. Reaching a limit blocks creation without
evicting or overwriting older work. Clearing is explicit. There is no database,
browser storage, automatic file, import/reload, cloud save, or background job.

Milestone 10 adds no external support connector, ticket creation, assignment,
reply drafting or sending, SLA, real classifier, LLM, training, bulk judgment,
account system, ranking, persistence, French support, or automatic confirmation
or execution of safety, fraud, refund, cancellation, payment, or account action.
