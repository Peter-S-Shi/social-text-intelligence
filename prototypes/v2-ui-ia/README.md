# PROTOTYPE - STI V2 UI/IA exploration (throwaway)

These files are **not production code**. They live only on the sidecar branch
`prototype/v2-ui-ia-exploration`, are not packaged, have no tests, and import
nothing from `src/`. All text and numbers are synthetic. `main` will keep only
the decision recorded at the UI/IA gate.

**Question:** what desktop-native information architecture, navigation model,
and visual hierarchy should STI V2 use, inside the fixed V2 thesis and the
Architecture Gate (Windows-first, PySide6 Qt Widgets, persistent projects,
review at the centre, AI record separate from human judgment, no Flask)?

**Plan:** three structurally different directions on one PySide6 window,
switchable from a floating bottom bar, plus a shared set of flows and states:

| Key | Direction | Structure |
| --- | --- | --- |
| A | Evidence Workbench | Menu bar + project navigator dock + record table + inspector dock + jobs dock + status bar |
| B | Guided Pipeline | Project cards; inside a project a stage rail (Import, Analyze, Review, Insights, Export), one stage and one primary action at a time |
| C | Review Desk + Report | Slim rail; desk ("what needs judgment now"), keyboard focus review of one record, written report, Ctrl+K palette |
| S | Shared | First run and model download, download failure, state board, Decision Practice options P1 (keep, demoted) and P2 (retire) |

The gate write-up is [UI_IA_GATE.md](UI_IA_GATE.md); screenshots are in
[screenshots/](screenshots/).

## Run

Needs Python 3.11+ and PySide6 in a scratch virtual environment (the project's
own dependencies are not changed):

```text
python -m venv <scratch-venv>
<scratch-venv>\Scripts\python -m pip install "PySide6-Essentials>=6.7,<6.11"
<scratch-venv>\Scripts\python prototypes/v2-ui-ia/run_prototype.py --variant A
```

- Left / Right arrow: previous / next direction (A, B, C, S)
- Page Up / Page Down or the bar's dropdown: previous / next screen
- Some in-screen navigation works (tree items in A, stage rail in B, rail in C)
- `--capture <dir>` renders every screen to PNG without showing a window

Tested with PySide6 6.10.3 on Windows 11 and Python 3.12.
