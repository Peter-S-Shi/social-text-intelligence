# M9.2-A — Independent human annotation feasibility

Version: **1.0.0**. Research baseline: `main@26e1d08`.
Status: **PLAN PREPARED; PERSONNEL AND EXECUTION PENDING**.
No person has been recruited, contacted, committed or authorized by this document.
No feedback records, reference labels or model outputs have been produced.

The owner-approved [evaluation protocol](V2_M9_EVALUATION_PROTOCOL.md) and
[evidence contract](V2_M9_EVIDENCE_CONTRACT.md) remain binding. This plan fills
operational prerequisites; it changes no sample, metric or annotation design.

## Roles and concrete workload

| Role | Required commitment before execution | Present disposition |
| --- | --- | --- |
| Source/privacy custodian | Verify owner-approved source/version/use, lawful access, restricted storage, minimization, withdrawal and deletion; maintain private provenance links | PENDING, unassigned |
| Sampling coordinator | Apply frozen eligibility/dedup rules blind to labels/predictions; select 60 real records per channel and freeze IDs and independent subset | PENDING, unassigned |
| Human annotator A | Independently label all 180 selected real records for both tasks under the frozen guide | PENDING, no availability evidence |
| Human annotator B | Independently label the preregistered 20 records/channel, at least 60 total, blind to A and AI | PENDING, no availability evidence |
| Blinded adjudication | Either a distinct human adjudicator or documented blinded consensus; retain both originals and unresolved uncertainty | PENDING, owner must choose protocol-supported route |
| Model operator / analysis reviewer | Obtain frozen references only after completion; run exact shipped semantics in a separately authorized later scope | PENDING, not part of M9.2-A |

A and B must be distinct humans. The coordinator/custodian may share a role only
if access controls prevent prediction or peer-label leakage; role overlap must
be recorded. An owner may serve as a human role if the same blindness conditions
hold. Codex or another AI cannot occupy a reference-annotator role. App Review,
Accept/Correct actions and existing M8 trial data cannot establish blind gold.

Workload is **180 A assignments + at least 60 B assignments**, each containing
sentiment and emotion decisions with reasons where uncertain; adjudication adds
work only after originals are locked. No hours, completion date, recruitment
success or available budget is assumed. The remaining 120 single-annotated
records are not independently corroborated.

## Availability gate: evidence required from the owner

Use role codes, never names, addresses, account IDs or contact details in Git.
Private recruitment/consent evidence stays outside public documentation.

1. Identify two separate human roles with adequate English and software/app
   feedback comprehension; disclose relevant conflicts, prior exposure and
   whether either has seen source labels, STI predictions or peer references.
2. Obtain explicit agreement to the workload, local-only authorized text handling,
   no AI assistance, blindness, confidentiality and applicable deletion rules.
   Confirm that source terms permit sharing with these authorized people.
3. Record availability window, device/offline access constraints, compensation or
   volunteer arrangement and realistic capacity privately. The owner must arrange
   recruitment/communication; this research does not send invitations.
4. Before the real execution freeze, prepare a versioned guide and author-created
   neutral training examples under a later authorized task. Calibrate comprehension
   without exposing evaluation records or using models. Measure a small training
   workload to estimate hours; do not invent a throughput estimate now.
5. Require separate agreement to the blinded adjudication route and retain original
   independent submissions. If capacity, independence or lawful access is absent,
   stop and escalate; do not reduce 60 dual references, replace B with AI, or
   silently amend the owner-approved design.

## Blind procedure to preregister, not execute here

The coordinator distributes pseudonymous text and permitted context through
separate restricted packages. Strip usernames, source ratings, existing dataset
labels, AI outputs/confidences, and peer annotations from the labeling view;
document any context redaction without changing the authentic appraisal text.
No automated language/sentiment model may screen for easy records. English
eligibility screening is a separate blind process, not reference labeling.

Both annotators use exactly positive/neutral/negative or sentiment UNCERTAIN
with reason; emotion uses the nine approved dominant labels, distinct non-neutral
secondaries, or task uncertainty. Neutral has no secondaries. The guide must
specify missing context, mixed appraisal, irony, dominance and ambiguity without
reverse-engineering classifier thresholds. Sentiment certainty is independent
of emotion certainty. A definite complete emotion reference is required for
both dominant and set analyses; no partial-reference policy is introduced.

Lock A and B originals before revealing disagreements. Adjudication remains
blind to predictions and records disagreement reasons, guide/version and
unresolved UNCERTAIN. Lock adjudicated references before model unblinding.
Maintain access/event records and disclose any exposure; exposed decisions
cannot be relabeled as blind preregistration.

Agreement uses pre-adjudication originals: sentiment observed agreement and
Cohen's kappa where estimable; emotion exact non-neutral set agreement, mean
Jaccard and label-wise agreement/support, with the protocol's empty-set convention.
Report assigned pairs, completed pairs, task-definitive pairs, uncertainty and
per-channel counts. Undefined kappa is not estimable, not perfect agreement.
Task metrics later use separate N, D_s, D_d, D_e, P_t and M_t ledgers; uncertainty,
withdrawal, missing reference and prediction failure never disappear from N.

## Execution preregistration prerequisites

The M9.0 **design freeze is already approved**. M9.2-A prepares feasibility only;
it neither performs nor approves the separate **execution freeze**.

| Order | Required evidence before progression |
| --- | --- |
| 1 — Source approval | Source intake entry explicitly approved by owner for actual source/version/access/local use and privacy; third-party rights supported, not invented by owner assent |
| 2 — Authorized acquisition | Separate bounded acquisition authorization and approved storage; establish actual frames/counts without labels or predictions |
| 3 — Feasibility confirmation | At least 60 eligible authentic English real records per channel after cross-channel dedup; committed independent human roles; prospective amendment if insufficient |
| 4 — Execution freeze | Actual source versions/date ranges, channel overlap precedence, screening/exclusion counts, normalization/exact/near-dedup algorithm and canonical member, random generator/version/seed, uniform selection without replacement, all 180 IDs and at least 60 dual-subset IDs, guide/roles/adjudication, storage/retention, environment/model revisions/mapping/threshold and analysis seeds |
| 5 — Explicit later authorization | Freeze version/digest, reviewed owner decision and amendment/exposure history precede labels or predictions; only then separately scoped reference and inference work |

The approved 45 SYNTH_CHALLENGE cases remain separate future work (15 per
channel), not substitutes for real records or part of this research. Keep the
approved 2,000 fixed-seed stratified bootstrap resamples, 95% percentile intervals
and task-specific uncertainty rules unchanged. Feasibility does not produce scores.

## Owner decision packet and exit meaning

Owner input is needed on candidate sources in the
[source-intake register](V2_M9_2A_SOURCE_INTAKE_REGISTER.md), rights questions,
two human commitments, adjudication route, private handling and resource plan.
Record decision date, role, approved versions, scope and reasons without PII.
Until those facts exist, feasibility is **PENDING**, not a passed acquisition gate.
An independent review/merge accepts this planning artifact only, not source
rights, sample availability, annotator commitments or overall M9 acceptance.

M9.0/M9.1 remain established. M7 CONDITIONAL and M8 owner overall PASS retain
their exact [risk dispositions](V2_M9_EVIDENCE_CONTRACT.md#risk-carry-forward-no-automatic-closure);
A3 integrity policy, A5 memory/cold-cache/physical low-RAM, unexplained project
availability, sync-folder behavior, Qt teardown and Review text-size remain
unclosed where recorded. M9.3 formal Windows UAT/accessibility, M9.4 owner
synthesis and M10 packaging are separate, unstarted boundaries.

## Version history

| Version | Change | Approval |
| --- | --- | --- |
| 1.0.0 | Initial role/capacity/blindness and execution-freeze feasibility plan | PENDING owner feasibility decision; no execution authorized |
