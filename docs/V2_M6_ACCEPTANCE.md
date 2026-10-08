# M6 — Full Native UI Integration / Polish: acceptance record

M6 integrates existing V1 presentation into the native, project-centred desktop.
The binding feature inventory is the round-3 `FEATURE_BOUNDARY.md` identified in
the [UI/IA decision](V2_UI_IA_DECISION.md), as amended by that decision's U1–U4.
In particular, U2 requires atomic cancellation and U4 excludes F5 and F6 from
the desktop. The [M5 Functional Exit inputs](../PROJECT_STATUS.md) identify the
native presentation that M6 must add. This record is an acceptance inventory,
not a model-quality, formal accessibility, packaging, or release gate.

`tests/desktop/` exercises the real Qt widgets against synthetic project data;
the application and persistence suites cover the underlying behavior. The
[Windows visual evidence](../manual-qa/m6-visual-evidence/README.md) is produced
by the actual Windows Qt plugin, including 900px windows and 150% scaling.

| ID | Native acceptance evidence | Status |
| --- | --- | --- |
| F1 | Unsaved single-text analysis, length and token safeguards: `test_qt_navigation.py`, `test_analysis_gate.py` | Accepted |
| F1.1 | Three sentiment scores beside label and confidence: `test_qt_navigation.py`, scene 19 | Accepted in M6 |
| F1.2 | Nine compact scores, threshold explanation and secondary labels: `test_qt_navigation.py`, scene 19 | Accepted in M6 |
| F1.3 | Deliberate disclosure of model-native scores: `test_qt_navigation.py`, scene 19b | Accepted in M6 |
| F1.4 | Model identity and revisions remain visible: `test_qt_navigation.py`, `test_qt_review.py` | Accepted |
| F1.5 | Missing-model state and setup route: `test_qt_navigation.py`, scenes 21–24 | Accepted |
| F2 | One bounded CSV project; input and token limits: `test_qt_projects.py`, batch/application tests | Accepted |
| F2.1 | Text-column choice and trusted metadata: `test_qt_projects.py`, scene 03 | Accepted |
| F2.2 | Per-row validation code and reason, with counts: `test_qt_projects.py`, scenes 03 and 08 | Accepted in M6 |
| F2.3 | Analysis row failures stay visible and separate from import rejection: `test_qt_projects.py`, `test_qt_results.py`, scenes 04–08 | Accepted in M6 |
| F2.4 | Sentiment, dominant emotion and compact activation aggregates with denominators: `test_qt_results.py`, scene 05 | Accepted in M6 |
| F2.5 | Per-row status, AI labels, reason and three filters: `test_qt_results.py`, scenes 05–07 | Accepted in M6 |
| F2.6 | Separate normalized results export and safe error: `test_qt_results.py`, scenes 26–27 | Accepted in M6 |
| F3 | Human review of successful records only: `test_qt_review.py`, scene 09 | Accepted |
| F3.1 | Independent sentiment judgment and corrected label: `test_qt_review.py` | Accepted |
| F3.2 | Independent emotion judgment and corrected dominant/secondary labels: `test_qt_review.py` | Accepted |
| F3.3 | Optional note and length guard: `test_qt_review.py` | Accepted |
| F3.4 | Position, save-and-next, next-unreviewed and queue filters: `test_qt_review.py`, scene 09 | Accepted |
| F3.5 | Review progress, corrected/uncertain counts and completion state: `test_qt_review.py` | Accepted |
| F3.6 | Agreement over definitive reviews and correction distribution: `test_qt_agreement.py`, scenes 12–14 | Accepted in M6 |
| F3.7 | Sentiment confusion and emotion-label comparison: `test_qt_agreement.py`, scene 14 | Accepted in M6 |
| F3.8 | Confidence bands, disagreement denominators and minimum sample threshold: `test_qt_agreement.py`, scenes 12–14 | Accepted in M6 |
| F3.9 | Reviewed export of all rows with separate AI/human fields and optional native scores: `test_qt_review.py`, `test_qt_agreement.py` | Accepted |
| F4 | Batch insights remain project-scoped: `test_qt_insights.py`, scenes 15–18 | Accepted |
| F4.1 | Trusted groups and 2–4 group comparison: `test_qt_insights.py` | Accepted |
| F4.2 | AI, human and agreement perspectives with approved metrics: `test_qt_insights.py`, scenes 15–17 | Accepted |
| F4.3 | AI-label and date filters: `test_qt_insights.py` | Accepted |
| F4.4 | Eligible denominators, failed rows, small-sample and descriptive caveats: `test_qt_insights.py` | Accepted |
| F4.5 | Context notes, associations, tags and delete: `test_qt_insights.py`, scene 18 | Accepted |
| F4.6 | Representative cases, selection rules and local-text reveal: `test_qt_insights.py`, scene 18 | Accepted |
| F4.7 | Insights CSV with optional text, metadata and native scores: `test_qt_insights.py` | Accepted |
| F4.8 | Model and review provenance: `test_qt_insights.py` | Accepted |
| V2-1 | One persistent project per CSV, open/list/delete: `test_qt_projects.py`, persistence suites, scenes 01–03 | Accepted |
| V2-2 | First-run provisioning, offline folder, recovery and status: `test_qt_shell.py`, `test_panel.py`, scenes 21–25 | Accepted |
| V2-3 | Local language check and unsupported-language warning: `test_language_surfaces.py`, scenes 05, 20 | Accepted |
| V2-4 | Row progress, cancel and no partial commit: `test_qt_projects.py`, application/persistence suites, scene 04 | Accepted under U2 |
| F5–F6 | Moderation Training and Support Triage are absent from the V2 desktop under U4: `test_boundaries.py` | Excluded by gate |

M6-specific interaction acceptance also covers the fixed project sidebar,
separate immutable AI and human cards, error/focus return, keyboard-reachable
named controls, readable contrast, reflow at 900px, and 150% scaling. See
`test_qt_navigation.py`, `test_qt_review.py`, `test_style_contrast.py`, and the
visual evidence. The formal Windows screen-reader/high-contrast acceptance is a
later, separately scoped gate.
