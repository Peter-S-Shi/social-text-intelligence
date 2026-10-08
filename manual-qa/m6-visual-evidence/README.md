# M6 actual-Qt visual evidence

These are synthetic, application-widget captures from the real Windows Qt
platform plugin. Both directories contain the complete 44-image scene set from
`tests/visual/capture.py`: `windows-100/` at normal scale and `windows-150/`
with `QT_SCALE_FACTOR=1.5`. The captures use throwaway project data and
synthetic model outputs; they are visual and interaction evidence, not model
quality measurements or formal assistive-technology acceptance.

| Scenes | What to inspect |
| --- | --- |
| 01–03 | Empty/list projects and per-row import validation |
| 04–08 | Analysis progress, cancellation, results, filters, and failed rows |
| 09–11 | Partial Review, AI/human separation, unsaved draft and discard confirmation |
| 12–14 | Agreement thresholds, confusion, emotion comparison and confidence bands |
| 15–18 | Insights perspectives, notes and representative cases |
| 19–20 | Single-text scores, native-score disclosure and language warning |
| 21–25 | First run, missing/corrupt/ready models |
| 26–27 | Results export success and safe failure |
| 28–30 | Keyboard focus on table, sidebar and filter |
| 31–34 | 900px windows: Results, Review, Agreement and Insights |
| 35 | Unreadable local project entry |

For a fresh capture on Windows with the `dev` extra installed, set a writable
temporary directory and run `python tests/visual/capture.py <output-directory>`.
Set `QT_SCALE_FACTOR=1.5` for the second run. The script prints
`platform: windows`; an `offscreen` capture is not equivalent. Every screenshot
comes from `QWidget.grab()` of the app or its own dialog, never a desktop-wide
screen capture.
