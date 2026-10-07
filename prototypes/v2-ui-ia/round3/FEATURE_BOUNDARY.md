# Round 3 feature boundary

Every control in the round 3 sample sheet maps to one ID below. Anything without
an ID is out of scope and must not appear. The source of truth is the V1 code at
`main` `afda67c`:

- `interface/app.py`
- `moderation_routes.py`
- `triage_routes.py`
- templates
- `services/insights.py`
- `services/review.py`
- `services/batch.py`

V2-approved additions come only from the Product Scope Gate and the
Architecture Gate. They are tagged `V2-*` so they can be removed in one pass if
the owner wants a strict V1 surface.

## V1 features (F)

| ID | Feature (V1 behaviour) |
| --- | --- |
| F1 | **Direct analysis.** One English text; 20,000-character safety limit; tokenizer limits checked before inference (reject, never truncate). |
| F1.1 | Sentiment label, confidence, and negative / neutral / positive scores. |
| F1.2 | Dominant compact emotion, inclusive threshold (0.50), threshold-fallback explanation, secondary emotions, and the nine compact emotion scores. |
| F1.3 | "Inspect all model-native emotion scores" (28 GoEmotions labels). |
| F1.4 | Models and provenance (pinned model ids and revisions). |
| F1.5 | Missing-model-extras error ("Local model dependencies are not installed"). |
| F2 | **Batch CSV upload.** Limits: 2 MB, 500 rows, 20k characters per text, per-row token limits. |
| F2.1 | Text column selection. Recognised metadata columns: `record_id`, `source_type`, `source_label`, `language`, `timestamp`, `topic`, `community`, `parent_record_id`, `notes`. |
| F2.2 | Preview and validation: rows, valid, invalid, and per-row error code and message. |
| F2.3 | Analyze N valid rows; row-level failure isolation (failed rows kept with a reason). |
| F2.4 | Aggregates: sentiment distribution, dominant-emotion distribution, compact activation rate; analyzed and failed counts. |
| F2.5 | Results table: row, id, status, sentiment, dominant emotion, secondary emotions or error; filters for status, sentiment and dominant emotion. |
| F2.6 | Export results CSV. |
| F3 | **Human review** of each successful record. |
| F3.1 | Sentiment judgment (accept / correct / uncertain) plus a human sentiment label. |
| F3.2 | Emotion judgment (accept / correct / uncertain) plus a human dominant emotion and human secondary emotions. |
| F3.3 | Optional review note. |
| F3.4 | Navigation: position / total, Save & Next, Next Unreviewed. Queue filter: all, unreviewed, reviewed, corrected, uncertain. |
| F3.5 | Progress: reviewed / reviewable / total; corrected, uncertain and unreviewed counts; "review queue complete" state. |
| F3.6 | Agreement, not accuracy: sentiment agreement, dominant-emotion agreement and exact-set agreement, each over definitive reviews; correction distribution. |
| F3.7 | Sentiment confusion and emotion label comparison. |
| F3.8 | Confidence and disagreement: bands 0.00–0.49, 0.50–0.74, 0.75–0.89 and 0.90–1.00; disagreements / definitive; shown only after at least 5 definitive reviews. |
| F3.9 | Explicit reviewed export: all rows, the immutable AI record, separate human fields, provenance, errors and agreement; native scores optional. |
| F4 | **Insights** over the batch. |
| F4.1 | Trusted grouping by `source_type`, `source_label`, `topic`, `community`, `language` or `timestamp_month`; choose the displayed groups (comparison of 2–4). |
| F4.2 | Perspective (AI, Human or Agreement) and a metric (10 metrics: AI sentiment, AI dominant emotion, AI emotion activation, human sentiment, human dominant emotion, human emotion inclusion, sentiment / dominant / emotion-set disagreement, review coverage). |
| F4.3 | Filters: AI sentiment, AI dominant emotion, date range. |
| F4.4 | Metric and denominator panel: eligible / group rows, failed rows per group, sample-size level (insufficient below 5, small below 10, otherwise descriptive), suppressed comparative emphasis, and the "descriptive, not causal" statement. |
| F4.5 | Context notes: association (record, topic, community, source label, comparison) and value, phrase, explanation, why context matters, tags (9). List with delete. Notes never reclassify a record. |
| F4.6 | Representative cases: selection rule (highest AI score, lowest AI confidence, AI-human disagreement, human corrected, uncertain, with context notes, user-selected), compact emotion, tag; "reveal full local text"; AI and human labels per case. |
| F4.7 | Insight export CSV (optional record-level text and metadata; optional native scores). |
| F4.8 | Model and review provenance. |
| F5 | **Moderation Training** (synthetic policy; training aid only). |
| F5.1 | Case library filters: category, difficulty, ambiguity, objective, safety-sensitive. |
| F5.2 | Prepare a workspace-derived case: successful source record, excerpt, difficulty, objective, optional self-authored reference and optional mock. |
| F5.3 | Session: case with a sensitive-content notice, contextual sentiment/emotion signals (not verdicts), synthetic mock recommendation. |
| F5.4 | Decision form: disposition, primary violation, severity, escalation, secondary violations, escalation reason, unclear reasons, reasoning, reviewer note. Immutable first decision; non-blocking guidance warnings. |
| F5.5 | Frozen feedback and comparison; results with raw denominators (no composite score); category and severity alignment; restart as a new attempt. |
| F5.6 | Privacy-default CSV export with opt-in context. |
| F6 | **Support Triage** (human-led; mock is a fixture). |
| F6.1 | Work mode: independent or AI-assisted simulation. |
| F6.2 | Source & routing guide: add synthetic tickets, prepare a workspace-derived ticket. |
| F6.3 | Triage workspace: filters (status, source, source label, topic, community, intent, category, urgency, queue, escalation, mock, disagreement, warning, text search) and sort (original order, urgency, status, timestamp). |
| F6.4 | Ticket decision: primary intent, up to 2 secondary intents, issue category, urgency, recommended queue, escalation and reason, primary action, up to 2 secondary actions, unclear explanation, notes. Save draft, finalize, revise explicitly. Supporting context collapsed by default. Mock revealed after the first finalize. |
| F6.5 | Summary: coverage, distributions, human–mock comparison (first and final), follow-up reasons. Privacy-aware export with opt-in categories. |

## V2 additions approved by the gates

| ID | Addition | Gate |
| --- | --- | --- |
| V2-1 | Persistent local project = one V1 batch workspace (one CSV and everything derived from it), kept until manually deleted; open, list, delete with conservative wording | Product Scope Q1, Architecture A3/A4 |
| V2-2 | First-run model provisioning: download pinned revisions with progress and recovery, or use a pre-provisioned folder, or later | Architecture A2 |
| V2-3 | Language detection with an unsupported-language warning | Product Scope Q3 |
| V2-4 | Batch progress and cancellation (keeps finished rows) | Architecture seam S6 |

## Deliberately excluded

These appeared in rounds 1 or 2 and are now removed because they are not in
V1 or the gates.

- Several CSV sources per project, and adding texts to an existing project.
- Adding a Direct analysis result to a project. Direct stays unsaved, as in V1.
- "Mixed signal" and "low margin / unsettled" flags and margin-based headlines.
  Only V1's threshold-fallback and confidence semantics remain.
- Calibration by margin band, the scatter "field" used as navigation or
  insight, region selection, probes with overrule rates, and sarcasm-cluster
  annotations.
- A command line or palette that does anything beyond V1 actions.
- Keyboard shortcut schemes beyond normal desktop accessibility.
- Similarity, "precedents", theme discovery, and any new metric.
- Retention timers, encryption claims, accounts, sync, and sharing.

Decision Practice (F5, F6) is shown as a demoted area because its final
disposition (P1 keep and demote, or P2 retire) is still the owner's open
decision. If P2 is chosen, those two screens are deleted and nothing else
changes.
