# M9.1 infrastructure validation

Implementation HEAD: `bdd3b080e4958d428d21afca080e5449b7f71456`.
Baseline: owner-approved M9.0 main `684a7fb4`.

| Check | Evidence |
| --- | --- |
| Local Python full regression | Windows, Python 3.12: 1154 passed, 4 existing opt-in integration tests skipped. Complete run on `2a41b38` source; later commits change only JS summary output and its Node assertions, plus the Node setup action |
| Recorder contract/security | Node: 11 tests passed on the final implementation head; coverage includes stable IDs, NOT RUN initialization, provenance, status validation, progress, strict JSON round-trip/rejection, duplicate members, privacy references, original failures, retests, history limits and safe Markdown |
| Fixture consistency | Two Python fixture checks passed through the existing CSV preparation contract; no model inference |
| Local quality | Ruff passed; strict MyPy passed for 230 files; compileall passed |
| Real-browser infrastructure smoke | Chrome on Windows: navigation, invalid decisions, saved progress, draft restore, hostile/valid import, cancelled replacement, unsaved-edit protection, provenance locking, dark error foreground, DOM/AX names and 375px presentation passed. Reproduction: `tests/manual_qa/browser_smoke.cjs` with an isolated profile; local ignored screenshot inspected |
| Independent review | Separate Spec and Standards reviews passed after regression-first repairs; final summary diff independently re-reviewed |
| GitHub CI | [Final implementation-head run](https://github.com/Peter-S-Shi/social-text-intelligence/actions/runs/38074145512): PASS for Python 3.11, 3.12 and 3.13 full tests, Ruff, strict MyPy and compileall; separate Node recorder job PASS |

The initial 24-scenario / 49-step pack remains entirely **NOT RUN** for formal
UAT. Synthetic decisions in recorder tests are ephemeral infrastructure checks;
they are not actual desktop execution, Narrator/high-contrast acceptance,
representative model evaluation, owner M9 PASS, or release readiness.

The M8 overall exploratory approval and M7 CONDITIONAL exit remain as recorded;
see the [M8 technical ledger](../../docs/V2_M8_TRACK_A_LEDGER.md) and
[M7 record](../../docs/V2_M7_FEASIBILITY_GATE.md). M9.2 source rights and execution
preregistration, M9.3 authorized Windows observations, M9.4 owner synthesis and
M10 packaging remain distinct future gates.

Privacy review covered the intended Git diff and staged files, synthetic content,
ignored private results/temp data and untracked prompt drafts. Product `src/`,
dependencies and the historical V1 questionnaire are unchanged from the baseline.
Current-state governance is written for the exact post-merge interpretation;
historical design-delivery statements are identified as historical.
