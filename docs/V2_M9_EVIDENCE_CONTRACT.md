# M9 — Evidence & Formal Acceptance: evidence contract

## Authority and scope

This contract encodes the owner's M9.0 planning specification v1.0 against
`main@45874bb4088cb0afe559c82f1c1f2d9d8bd921c4`. The substantive design received explicit owner Evidence Design Gate PASS on
2026-10-10 (reviewed PR #53 HEAD `32d8d37`). This is not an executed evaluation
or overall M9 acceptance. Live gate decisions remain in [Project Status](../PROJECT_STATUS.md).

The owner has approved English software/mobile/desktop app feedback as the
principal domain, authentic lawful feedback as primary evidence (Strategy A),
synthetic material as separate support, and Codex as the implementation agent.
M8's overall owner PASS is established. The numerical target evaluation
parameters in the [evaluation protocol](V2_M9_EVALUATION_PROTOCOL.md) received
M9.0 owner Gate approval on 2026-10-10. No named third-party source is approved
and neither sample availability nor independent second annotation is assured.

Three evidence streams must stand independently:

| Stream | Required evidence | Cannot substitute |
| --- | --- | --- |
| Q5 representative-domain model evaluation | Lawful real-domain sample, blind references, exact shipped predictions, auditable metrics and limitations | Synthetic tests, upstream benchmarks, capacity probes, app Review agreement |
| Formal native desktop UAT | Owner-operated or explicitly authorized interactive Windows Qt sessions with synthetic fixtures | Source inspection, headless tests, M8 exploratory PASS |
| Formal Windows accessibility | Observed keyboard, UI Automation, Narrator, high contrast, DPI and text-size behavior | Qt metadata assertions or offscreen screenshots alone |

The [evaluation protocol](V2_M9_EVALUATION_PROTOCOL.md) owns sample, annotation,
metric and denominator definitions. The [UAT protocol](V2_M9_UAT_PROTOCOL.md)
owns scenarios and recorder schema. The [exit gate](V2_M9_EXIT_GATE.md) owns
synthesis and approval criteria. These files define future work; they contain no
evaluation results, formal UAT session or accessibility acceptance.

## Established boundaries

Preserve [Q3–Q5 and the audience decision](V2_PRODUCT_DISCOVERY.md),
[core contracts](CONTRACTS.md), [model governance](MODEL_GOVERNANCE.md),
[sentiment audit](MODEL_AUDIT.md) and [emotion audit](EMOTION_MODEL_AUDIT.md).
English is the only approved model language. Human review remains separate from
immutable AI records. Neutral emotion is a fallback, language evidence is a
warning, and successful inference consumes the complete input without truncation.
Descriptive app agreement is not model accuracy. The historical
[capacity probe](REAL_MODEL_CAPACITY_EVIDENCE.md) measured runtime on synthetic
templates, not representative-domain performance.

M9.0 adds no product feature, model, provider, taxonomy, threshold, schema,
network surface, dataset, fixture, installer or UI redesign. Moderation Training
and Support Triage stay retired from V2. M10 owns final packaging, LGPL,
installer, clean-machine, SmartScreen and release-candidate work. No M9 gate
alone authorizes a release or changes package version `0.10.0`.

## Data classes

| Tag | Use | Counts toward Q5? |
| --- | --- | --- |
| `REAL_PRIMARY` | Authentic, authorized software/app feedback | Only after source, privacy, eligibility and labeling gates |
| `SYNTH_CHALLENGE` | Separately reported stress/error characterization | No |
| `SYNTH_UAT` | Controlled functional workflow/failure evidence | No |

Never pool these classes. The M8 29-row fixture may inform future UAT coverage;
it is not independent model-quality ground truth.

## Source Intake Gate: before retrieval or import

Public visibility is not permission to scrape, analyze or redistribute text.
Local research permission and public redistribution permission are separate.
A code license, model audit, dataset download button or hash proves neither.
M9.0 specifies the workflow without acquiring material; M9.2 cannot close Q5
without an approved real source set.

Register each proposed source before any retrieval/import:

| Field | Required content |
| --- | --- |
| Source identity | Canonical dataset/provider URL, version, original platform and collection method |
| Rights evidence | Explicit dataset/platform terms and author-rights basis; evidence URL, access date, reviewer |
| Proposed use | Local research authorization, scope, permission/consent where needed |
| Public split | Separate redistribution decision for text, source IDs, labels and derivatives; attribution/conditions |
| Fit | English/domain/channel fit, source date range, population and sampling-frame limits |
| Privacy | PII exposure, minimization/redaction, consent/takedown, retention/deletion, storage/access controls |
| Disposition | `APPROVED_LOCAL_ONLY`, `APPROVED_PUBLIC`, `REJECTED` or `PENDING`, rationale and responsible reviewer |

The recorded approval must cover the proposed use and version. `PENDING` and
`REJECTED` prohibit ingestion and evaluation. Unclear rights require an explicit
owner decision, an alternative lawful source or permission; an owner decision
cannot manufacture third-party rights. Do not accept terms on the owner's
behalf, bypass controls, autonomously scrape/bulk harvest or use unofficial
scraped mirrors. Private/user-controlled feedback also needs a documented legal
basis, permission and appropriate consent/redaction controls.

No source approval entries exist as a result of M9.0. Future source reviews must
record actual evidence rather than fill a template with assumed permissions.
Source discovery/rights review does not authorize retrieval until approval.

## Storage and reproducibility

Restricted raw text, source-record mappings and non-redistributable annotations
remain in ignored, access-controlled local storage. Existing ignored
`private_data/` and `local_data/` can hold these later; ignoring is not an access
control and does not make storage encrypted. Use record pseudonyms, minimize
identifiers, honor retention/takedown, and do not commit personal profiles,
usernames, account IDs, emails, restricted excerpts, credentials or local paths.

Public evidence can contain lawful source/dataset-level provenance, protocol
versions, sampling methods, pseudonymous IDs, model revisions and safe aggregate
metrics. Only separately approved, privacy-safe material may be public even for
`APPROVED_PUBLIC` sources. A restricted manifest maps pseudonyms to source records
for authorized reruns. State explicitly when reruns require restricted access;
do not claim public reproducibility from unavailable text or labels.

## Two-stage preregistration

1. **Design freeze (M9.0 owner Gate PASS, 2026-10-10).** The owner approved the
   versioned channel definitions, eligibility/sampling rules, numerical targets,
   blind annotation/adjudication, metric/denominator/uncertainty rules and UAT/exit
   requirements on reviewed document HEAD `32d8d37`. This decision is independent
   of the PR merge and does not approve sources or guarantee target availability.
   Prospective amendments still require separate approval.
2. **Execution preregistration (M9.2, after source approval/authorized acquisition,
   before reference labeling or any model predictions).** Bind the approved
   design to actual source versions/dates, frame and eligibility counts, dedup
   procedure, sample seed, selected pseudonymous IDs, dual-label subset, guide
   version, annotator roles, environment/model/mapping/threshold versions and
   analysis seeds. Freeze an auditable manifest and record its version/digest.
   This stage fills operational facts; it does not alter approved design choices.

This resolves the ordering: lawful acquisition can be necessary to establish a
frame, but source approval precedes acquisition, and the execution freeze
precedes human reference labels and AI outputs. Eligibility screening is blind
to both and must not pre-label sentiment/emotion. M9.0 does not pretend to know
future source dates, availability or selected IDs. Amendments must be visible,
prospective and owner-approved before affected labels/predictions are inspected.
If output exposure already occurred, disclose it and define a newly approved,
unexposed sample; never call a retrospective choice preregistered.

## Phase handoffs

| Slice | Deliverable and boundary |
| --- | --- |
| M9.0 Evidence Design Gate | **PASS, owner-approved 2026-10-10** on reviewed design HEAD `32d8d37`; no acquisition, labels, scores or executed UAT implied |
| M9.1 UAT Infrastructure | Synthetic scenario pack and tested offline companion; functional evidence recording, no formal UAT inferred |
| M9.2 Domain Evaluation | Approved sources, execution freeze, blind references/adjudication, exact inference and mandatory honest report |
| M9.3 Windows UAT/accessibility | Actual owner/authorized operator sessions, evidence and defect/retest dispositions |
| M9.4 Consolidated exit | Owner `PASS` / `CONDITIONAL` / `FAIL` from all three streams and remaining risks |

M9.1–M9.4 have not started through this design delivery. The phases are bounded
work slices, not an instruction to parallelize large implementation tasks.

## Risk carry-forward (no automatic closure)

Read the [M7 record](V2_M7_FEASIBILITY_GATE.md),
[M8 Track A ledger](V2_M8_TRACK_A_LEDGER.md) and
[M8 Track B record](V2_M8_TRACK_B_FIDELITY.md) for authoritative evidence.

| Existing item | Disposition retained | Later evidence/decision |
| --- | --- | --- |
| R-D3 transient project unavailable / A2 | Unexplained; NOT REPRODUCED in 128 rounds; adjacent fixes do not prove cause | Record recurrence, or retain limitation; do not declare resolved |
| R-D4 / A4 sync-managed folders | Disk/read-only/held-file cases fixed; actual sync environment NOT VERIFIED | Explicit environment evidence or continued limitation |
| R-I2 / A3 post-Verify corruption and re-hash cost | Measured; OWNER DECISION, no new check added | Owner integrity policy decision; separate authorized change if needed |
| R-S2 / A5 memory floor, cold cache, physical low RAM | Measured native-crash band below about 2.4 GB; OWNER DECISION; cold cache/physical low RAM NOT VERIFIED | Requirements/limitations and actual later evidence, no waiver inferred |
| Track B Python 3.12 Qt teardown incident | One-off segfault not conclusively root-caused | Preserve incident and capture recurrence; no clean-run auto-closure |
| Track B fixed-pixel Review queue | Windows text-size increase unverified, DPI captures distinct | Formal Windows text-size/accessibility observation in M9.3 |
| Track B accepted visual deviations/system fonts | Existing ACCEPTED DEVIATION dispositions; no font bundled | Preserve; any future font change needs explicit scope/notices decision |
| R-L* / R-P* | LGPL, packaging and distribution gaps untouched | M10; no compliance claim from M9 |

Already closed bounded items (scoped exclusion/actionable collision errors and
rejected-row summary count) retain their affirmative evidence; do not reopen or
erase it. M8's overall owner PASS supplies no additional item-level findings or
friction log. See the [exit gate](V2_M9_EXIT_GATE.md) for risk synthesis.
