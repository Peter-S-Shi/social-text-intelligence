# M8 Track B visual evidence: Reference, Before, After

Synthetic, application-widget captures from the real Windows Qt platform plugin
(`platform: windows`), taken with `tests/visual/fidelity.py` as `QWidget.grab()` of the
app's own window on throwaway data with synthetic model stand-ins. They are visual and
interaction evidence only. They are not model-quality measurements, not an
accessibility acceptance, and **not an acceptance of the design: that judgment is
PENDING OWNER**. The screen map, the delta register and the capture steps are in
[`docs/V2_M8_TRACK_B_FIDELITY.md`](../../docs/V2_M8_TRACK_B_FIDELITY.md).

The reference pictures are not copied here. They live on the sidecar branch
`prototype/v2-ui-ia-exploration` at commit `9543c9eb637475e3f87dad1110460f08eaba5200`
under `prototypes/v2-ui-ia/round3/shots/`:

```powershell
git show 9543c9eb637475e3f87dad1110460f08eaba5200:prototypes/v2-ui-ia/round3/shots/demo_review.png > demo_review.png
```

Directories (all PNG, shrunk to 1000 px wide):

| Directory | What it is |
| --- | --- |
| `before/` | the baseline `53a5c27` (M7 merged), 1358 × 803 content area, 100% scale |
| `after/` | this branch's final behavioural head (Round 2 included: project counts and tabs, the import row preview, the Results text column, the Analyze columns chart), same frame and data |
| `before-900/`, `after-900/` | the same screens at the 900 px minimum window width |
| `after-150/` | Review (and its unsupported-language record), Projects, Analyze one text (and its fallback state), Import and Results at 150% scaling, logical 1100 × 700 |

## Reference → Before → After index

| Reference | Native screen | Before | After | At 900 px (before / after) |
| --- | --- | --- | --- | --- |
| `demo_setup.png` | First-run setup | [before](before/demo_setup.png) | [after](after/demo_setup.png) | [before](before-900/demo_setup.png) / [after](after-900/demo_setup.png) |
| | Models window, both ready | [before](before/demo_setup-ready.png) | [after](after/demo_setup-ready.png) | [before](before-900/demo_setup-ready.png) / [after](after-900/demo_setup-ready.png) |
| `demo_projects.png` | Projects | [before](before/demo_projects.png) | [after](after/demo_projects.png) | [before](before-900/demo_projects.png) / [after](after-900/demo_projects.png) |
| `demo_direct.png` | Analyze one text | [before](before/demo_direct.png) | [after](after/demo_direct.png) | [before](before-900/demo_direct.png) / [after](after-900/demo_direct.png) |
| | threshold-fallback state | [before](before/demo_direct-fallback.png) | [after](after/demo_direct-fallback.png) | [before](before-900/demo_direct-fallback.png) / [after](after-900/demo_direct-fallback.png) |
| `demo_import.png` | Import & validation | [before](before/demo_import.png) | [after](after/demo_import.png) | [before](before-900/demo_import.png) / [after](after-900/demo_import.png) |
| `demo_results.png` | Results (cards) | [before](before/demo_results.png) | [after](after/demo_results.png) | [before](before-900/demo_results.png) / [after](after-900/demo_results.png) |
| | Results, table with the TEXT column | [before](before/demo_results.png) | [after](after/demo_results-table.png) | [after](after-900/demo_results-table.png) |
| `demo_review.png` | Review, unreviewed queue | [before](before/demo_review.png) | [after](after/demo_review.png) | [before](before-900/demo_review.png) / [after](after-900/demo_review.png) |
| | Review, unsupported-language record | [before](before/demo_review-language.png) | [after](after/demo_review-language.png) | [before](before-900/demo_review-language.png) / [after](after-900/demo_review-language.png) |
| `demo_agreement.png` | Agreement | [before](before/demo_agreement.png) | [after](after/demo_agreement.png) | [before](before-900/demo_agreement.png) / [after](after-900/demo_agreement.png) |
| `demo_compare.png` | Insights · compare | [before](before/demo_compare.png) | [after](after/demo_compare.png) | [before](before-900/demo_compare.png) / [after](after-900/demo_compare.png) |
| `demo_notes.png` | Insights · notes & cases | [before](before/demo_notes.png) | [after](after/demo_notes.png) | [before](before-900/demo_notes.png) / [after](after-900/demo_notes.png) |

`demo_mod.png` and `demo_tri.png` have no row: Moderation Training and Support Triage
were retired from the V2 surface by U4.

At 150% scaling: [Review](after-150/demo_review.png),
[Review, unsupported language](after-150/demo_review-language.png),
[Projects](after-150/demo_projects.png), [Analyze one text](after-150/demo_direct.png),
[Analyze one text, fallback](after-150/demo_direct-fallback.png),
[Import](after-150/demo_import.png), [Results](after-150/demo_results.png),
[Results table](after-150/demo_results-table.png).

Not shown: the datasets here are invented and differ from the prototype's scripted
numbers, and the operating-system window frame is not part of a widget grab.
