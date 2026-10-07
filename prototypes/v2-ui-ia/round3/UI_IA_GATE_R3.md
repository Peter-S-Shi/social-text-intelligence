# V2 UI/IA exploration, round 3: Human Gate brief

Round 3 answers the owner's three requirements.

**1. A real re-curation of the owner's material.**

- **onepagelove.com:** 650 entries scanned, filtered to 142, then reviewed
  visually. Finalists were checked from full-page captures cut into slices.
- **motionsites.ai:** the Apps category reviewed.
- **Result:** 14 references with links and what each contributes, plus the
  ones rejected and why. See [REFERENCES.md](REFERENCES.md).

**2. A strict feature boundary.** [FEATURE_BOUNDARY.md](FEATURE_BOUNDARY.md)
inventories the V1 surface from code (routes, forms, enums, metrics) as F-IDs,
plus the four gate-approved V2 additions (V2-1 to V2-4). Every screen lists
the IDs it implements. The round 2 inventions are removed: the field scatter,
margin flags, probes, multiple sources per project, and adding Direct results
to a project.

**3. Independent of the V1 look.** There are no V1 cards-on-green and no
web-form layout.

- **Palette:** warm stone paper, graphite for the machine, ultramarine for
  you, vermilion only for disagreement and failure.
- **Type:** Instrument Serif for figures and quotes, Inter for the interface,
  IBM Plex Mono for provenance. All three are OFL, so they can be bundled with
  the Qt build.

**Deliverable.** An HTML product feature sample sheet:
[sti-v2-r3-samples.html](sti-v2-r3-samples.html). Open it in any browser;
`?only=06` shows a single screen. PNG renders are in [shots/](shots/).

## Screens and coverage

| # | Screen | Feature IDs | References |
| --- | --- | --- | --- |
| 01 | First run · models | V2-2, F1.4 | R6, R10 |
| 02 | Projects (+ delete confirmation) | V2-1, F1, F3.5 | R4, R11 |
| 03 | Analyze one text (+ language, token-limit and missing-model states) | F1–F1.5, V2-3 | R10, R5 |
| 04 | New project · import & validate (+ progress and cancel) | F2–F2.3, V2-1, V2-3, V2-4 | R9, R2 |
| 05 | Results | F2.4–F2.6 | R13, R2, R1 |
| 06 | Review | F3–F3.5, F1.3 | R6, R4, R14, R12 |
| 07 | Agreement, not accuracy | F3.6–F3.9 | R7 |
| 08 | Insights · compare groups | F4.1–F4.4, F4.7, F4.8 | R8, R7 |
| 09 | Insights · context notes & representative cases | F4.5–F4.7 | R10, R4 |
| 10 | Decision Practice · Moderation Training (pending P1/P2) | F5–F5.6 | R12 |
| 11 | Decision Practice · Support Triage (pending P1/P2) | F6–F6.5 | R2, R12 |

Every F-ID in the boundary appears on at least one screen. Four parts are
represented by a summary note on screens 10 and 11 rather than drawn as their
own screen:

- Moderation case preparation (F5.2)
- Moderation results and export (F5.5, F5.6)
- The triage source and routing guide (F6.2)
- The triage summary (F6.5)

## IA in one paragraph

A Windows window with a quiet sidebar has three areas:

- **Project.** One project is one imported CSV. Its pages are Import &
  validation, Results, Review, Agreement, Insights · compare, and Insights ·
  notes & cases.
- **Tools.** Analyze one text, which is not saved, as in V1.
- **Decision Practice.** Visibly demoted and marked pending.

The start window is the project list. First run is a separate setup window.
Model status is always in the sidebar footer. The machine record and your
judgment are separate, equal cards on every review surface.

## Decisions for the owner

1. **Adopt round 3 as the UI/IA baseline** for the implementation milestones?
   Visual polish can still change during implementation. The IA, the feature
   boundary and the AI-versus-human separation would become fixed.
2. **Moderation Training / Support Triage:** keep them demoted (P1, screens 10
   and 11 stay) or retire them from V2 (P2, both screens are deleted)?
   Recommendation unchanged: P2.

The V2-1 to V2-4 additions are already gate-approved and are kept. Remove them
only if the owner wants a strictly V1 surface.

## Scope

- Sidecar prototype; synthetic data only.
- No changes to `main`, the Application Foundation work, `src/`, tests,
  dependencies or lifecycle files; no PR.
- The HTML loads Google Fonts for the mock only. A shipped build would bundle
  the OFL font files.
- Accessibility and LGPL compliance are not assessed here.
