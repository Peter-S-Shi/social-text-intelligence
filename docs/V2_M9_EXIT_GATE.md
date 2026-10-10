# M9 — Evidence & Formal Acceptance: exit gate

## Status and decision authority

This document defines gate criteria. It records no owner M9.0 Gate PASS, executed
evaluation, formal Windows UAT, accessibility acceptance or overall M9 exit.
Live decisions and next action belong to [Project Status](../PROJECT_STATUS.md).
The [evidence contract](V2_M9_EVIDENCE_CONTRACT.md) distinguishes owner-approved
strategy from proposed numerical design. Review completion or merging documents
does not automatically approve the Gate; record the owner's explicit decision
and approved revision separately.

M8 is complete by overall owner PASS, but its exploratory trial is not formal
M9 acceptance and supplies no individual trial results. M7's CONDITIONAL exit
and remaining M8 risk dispositions persist. No M9 gate is release readiness.

## Slice gates

| Gate | Required decision basis | Missing evidence |
| --- | --- | --- |
| M9.0 Evidence Design | Four committed/reviewed documents, source rights/privacy workflow, design choices, blind labeling/adjudication, metric/denominator/uncertainty rules, Windows UAT/a11y coverage, recorder schema and handoffs; explicit owner approval of design/parameters and approved commit | Owner decision remains pending; no source retrieval, sample, model score or executed UAT needed |
| M9.1 UAT Infrastructure | Deterministic synthetic pack, tested functional expectations, actual offline companion state/progress/schema round-trip and browser smoke | Infrastructure pending; never infer desktop UAT execution |
| M9.2 Representative Evaluation | Approved source sets, target eligible real sample or prospectively approved amended design, frozen manifests, blind labels/independence/adjudication, exact shipped inference, all metrics/coverage/limitations independently auditable | PENDING/BLOCK if lawful sources, sample or second annotation unavailable; escalate before amendment, never replace Q5 with synthetics |
| M9.3 Windows UAT/accessibility | Authorized observed sessions for every required scenario, justified applicability decisions, actual Narrator/high contrast/keyboard/scaling/text-size, failures classified/fixed/retested or explicitly accepted non-blocking | Required NOT RUN items block unconditional formal UAT PASS |
| M9.4 Consolidated M9 | Owner evaluates all three streams, claims and retained risks; records PASS / CONDITIONAL / FAIL with evidence and next responsible gate | No unconditional PASS from incomplete domain assessment, permissions, independent references or required Windows tests |

Design-freeze approval precedes M9.1 implementation. M9.2 execution
preregistration follows actual source approval/authorized acquisition but precedes
labels and predictions. Details are in the
[evaluation protocol](V2_M9_EVALUATION_PROTOCOL.md). Material amendments need a
visible prospective owner decision and version history; affected output exposure
must be disclosed, not relabeled as preregistration.

## Evidence package at M9.4

Each stream must have its own auditable disposition:

1. Source intake/rights/privacy decision log and lawful private/public split.
2. Design/execution freeze revisions, source/frame/sample/dual-subset manifests,
   seeds, denominator ledger, amendments and any output exposure.
3. Versioned blind guide, original references, independent-pair agreement and
   adjudication/unresolved counts, with task-specific denominators.
4. Reproducible runner, application/environment versions and exact pinned
   prediction provenance; no altered mapping/threshold to improve the score.
5. Sentiment, dominant and non-neutral-set metrics, per-channel/label support,
   uncertainty, all failures/warnings, separate challenge results and claims table.
6. Versioned synthetic UAT pack, actual authorized JSON session exports,
   summaries/evidence pointers and defect/fix/retest history.
7. Actual Windows keyboard/Narrator/high-contrast/DPI/text-size evidence,
   including every required NOT RUN and its reason.
8. Mapping of [M7](V2_M7_FEASIBILITY_GATE.md),
   [M8 Track A](V2_M8_TRACK_A_LEDGER.md) and
   [M8 Track B](V2_M8_TRACK_B_FIDELITY.md) dispositions to evidence or remaining
   owner decisions, without auto-closure.

Restricted source text/labels remain access-controlled and ignored. Public
reports include only rights-cleared privacy-safe evidence. State when reruns
require authorized restricted access; aggregate publication does not manufacture
public reproducibility.

## Blockers and honest measurement

Evidence completion and product adequacy are separate. No arbitrary F1 >= 0.80
threshold is imposed. An honest low score can complete measurement; it cannot
justify unsupported capability statements. Severe systematic misleading results
affecting core user decisions are a product-acceptance risk requiring owner
disposition, potentially FAIL or CONDITIONAL, not automatic PASS from a finished
report.

Block unconditional acceptance for insufficient source authorization, fabricated
or prediction-contaminated gold, unapproved post-hoc design changes, unfinished
representative-domain evidence or missing required interactive/accessibility
tests. Product blockers include corruption/loss, privacy breach, wrong-record
action, critical unrecoverable flow, materially misleading result, reproducible
crash and required accessibility failure. Use
[Manual Acceptance Gate](MANUAL_ACCEPTANCE_GATE.md) for classification and
Fix → Retest principles, not its historical V1 web checklist as native coverage.

Non-blocking findings require actual observed rationale and explicit accepted
disposition; do not mark a cosmetic mismatch blocking by default. Retest changes
where they can affect results; full regression is required when implementation
blast radius warrants it, not for this design-only wording delivery.

## Claims table required in the report

| Disposition | Meaning and required support |
| --- | --- |
| SUPPORTED | Narrow statement traceable to observed task, source/channel, n, coverage, support, uncertainty and limitations |
| UNSUPPORTED | Contradicted or beyond established scope; exclude from capability claims |
| INSUFFICIENT EVIDENCE | Untested, sparse/zero support, uncertain references, missing source/channel, failures or independence limits prevent the claim |

Do not infer deployment prevalence, calibration, all-domain reliability,
psychological diagnosis or automatic moderation fitness. Fixed equal-channel
sample estimates do not prove industry prevalence; high scores do not close
license, privacy, accessibility or packaging gaps. Formal UAT verifies workflows,
not model accuracy, and app Review agreement is descriptive rather than gold.

## Owner exit and remaining risks

The owner alone records the consolidated `PASS`, `CONDITIONAL` or `FAIL` from
the evidence package. PASS requires credible completed domain evidence, observed
required Windows UAT/accessibility and explicit acceptable risk dispositions.
CONDITIONAL names precise limitations, missing evidence/blocking implications for
distribution and the next responsible gate; it is not permission to claim release
readiness. FAIL records blocking findings and the bounded remediation/retest path.
Record owner role, decision date, reviewed package/application revisions, per-stream
dispositions, claims limits and remaining risks without personal identifiers.

Carry A3 integrity-check policy, A5 memory/cold-cache/physical-low-RAM, unexplained
project availability, unverified sync folders, the Qt teardown incident and
Review text-size observation forward as defined in the contract. Preserve
accepted visual deviations and already evidenced bounded fixes. Existing
OWNER DECISION/NOT VERIFIED/NOT REPRODUCED states do not disappear with M8 PASS,
M9.0 merge or a later clean test run.

M10 alone handles final Windows packaging, installer, LGPL compliance,
clean-machine verification, SmartScreen and release candidates. Any product
repair discovered later needs its own authorized scope, regression and retest;
this design does not authorize implementing it or beginning M9.1.
