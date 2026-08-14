# Manual Acceptance Gate Standard

This is the canonical, permanent acceptance contract for the **Full
Regression and Manual Acceptance** lifecycle phase. It defines what PASS,
FAIL, and N/A mean for that phase, who may execute it, and what evidence a
decision requires. It does not itself execute or pass the gate; a specific
gate decision is recorded in
[`docs/FEATURE_COMPLETE_MANUAL_AUDIT.md`](FEATURE_COMPLETE_MANUAL_AUDIT.md)
the same way the Feature Freeze and Product Hardening closure decisions are,
and live phase/gate state remains only in
[`PROJECT_STATUS.md`](../PROJECT_STATUS.md).

Establishing this standard is not itself a gate decision. It does not start
Manual Acceptance, change the Release Candidate status, or change release
readiness.

## Two evidence streams

Full Regression and Manual Acceptance requires two independent, non-substitutable
evidence streams. Neither alone is sufficient for the final gate.

**Automated Full Regression** — machine-executed, deterministic:

- full `pytest -q`;
- `ruff check .`;
- `mypy --strict src tests`;
- `python -m compileall -q src tests`;
- `python -m pip check`;
- repository privacy/local-path hygiene checks;
- any existing focused security/contract suites (CSP/security-header,
  lifecycle-consistency, and similar targeted regressions already tracked in
  `tests/`);
- justified opt-in/real-model evidence where required (see
  [`docs/DEVELOPMENT.md`](DEVELOPMENT.md) and
  [`REAL_MODEL_CAPACITY_EVIDENCE.md`](REAL_MODEL_CAPACITY_EVIDENCE.md)).

**Interactive Manual Acceptance** — human- or agent-driven, observed:

- the real local application, started as documented, not merely imported as
  a library;
- real browser interaction against that running application;
- the canonical
  [Manual QA questionnaire](../manual-qa/manual_review_questionnaire.html);
- project-authored synthetic data only (see
  [`manual-qa/README.md`](../manual-qa/README.md));
- recorded PASS / FAIL / N/A results with evidence, per this standard.

## PASS

Full Regression and Manual Acceptance may PASS only when all of the
following hold:

- every required automated regression/quality check in the list above
  passes;
- every required current-version interactive acceptance check in the
  questionnaire has been executed, not inferred;
- no unresolved blocking defect remains (see Blocking below);
- every observed failure has an explicit, permanent disposition (fixed and
  retested, or formally accepted as documented below);
- every accepted non-blocking finding is explicitly documented as such,
  with its permanent `FCR-XXX` reference where one exists;
- every N/A / not-tested case carries a stated reason.

## FAIL and blocking

A failure is **blocking** when it materially affects at least one of:

- correctness;
- data or state integrity;
- a privacy or security boundary;
- completion of a critical workflow;
- loss or corruption of user-controlled output;
- product state or a result that is materially misleading;
- a required accessibility or recovery path;
- a reproducible crash or dead end in a current-version workflow.

Pure cosmetic, readability, or polish issues are **not** automatically
blocking. A finding may be real and worth recording without stopping the
gate; classify it as non-blocking with its rationale, mirroring how
FCR-042 and FCR-043 were adjudicated during Product Hardening closure —
re-read the actual defect, decide whether it carries one of the risks
above, and only then decide blocking or non-blocking. Do not block on a
finding's mere existence, and do not implement a fix "because it's open."

## N/A / Not tested

- a required current-version check must never be silently skipped;
- N/A is valid only when the check is genuinely inapplicable to the tested
  environment or configuration (for example, a Windows-only launcher step
  during a non-Windows session);
- every N/A must carry a reason in the item's evidence field;
- being unable to execute a required check is not automatically a PASS —
  record it as N/A with the blocking reason, or as FAIL if the inability
  itself demonstrates a defect (for example, the app refusing to start).

## Evidence

- every FAIL records observed behavior and reproduction steps sufficient
  for another reviewer or agent to reproduce it without guessing;
- important gate-relevant or complex-interaction PASS cases keep
  reviewable evidence (a short observed-behavior note, not necessarily a
  screenshot);
- screenshots are required only when they materially help verify visual or
  browser-rendered behavior — not for every ordinary PASS;
- the tested commit SHA and environment (OS/browser) are recorded once per
  session in the questionnaire's session-metadata fields;
- PASS is never inferred from source-code reading alone when the checklist
  item requires real interaction. Code inspection may explain *why* a
  behavior is expected; it does not substitute for observing it.

## Fix → Retest

When acceptance discovers a blocking defect:

1. record it (observed behavior, reproduction steps, questionnaire item);
2. classify it (permanent `FCR-XXX` if new, or the existing one it
   reconciles with — do not create a duplicate for the same root cause);
3. fix it;
4. run targeted automated regression for the fix;
5. retest the affected interactive check(s);
6. run broader regression only when the fix's blast radius actually
   warrants it — a narrow template or route fix does not require restarting
   the entire manual suite.

Do not automatically restart the entire manual questionnaire for every
local fix. Re-verify what the fix could plausibly have affected.

## Executor model

Manual Acceptance may be executed by an authorized interactive coding agent
(such as Claude Code) controlling the real local application and a real
browser environment, once the repository owner has given explicit
authorization for that session.

"Manual" in this context means *interactive end-to-end verification outside
the ordinary automated test suite*. It does not require the repository
owner to personally perform every interaction.

When an agent executes Manual Acceptance, it must:

- operate the real application and a real browser — start the actual
  server, load the actual page, click/type/submit through the actual UI;
- observe UI behavior through real interaction, the DOM, or real browser
  state (network responses, console, rendered content) — not through
  reading the source code that implements it;
- never mark a checklist item PASS merely from source-code reasoning about
  what the code should do;
- report, rather than guess or assume, anything it genuinely cannot
  execute (for example, a capability the current environment does not
  support) and record that item as N/A with a stated reason, not as a
  silent skip or an inferred PASS.

This standard governs how the agent executes Manual Acceptance once
authorized; it does not itself constitute that authorization. A specific
session still requires the repository owner's explicit go-ahead.
