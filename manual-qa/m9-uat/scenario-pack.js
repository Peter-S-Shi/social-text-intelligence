"use strict";

// This pack defines instructions, never observed results or model gold labels.
(function (root) {
  const definitions = [
    ["UAT-MODEL-01", "First-run readiness", [
      ["EMPTY_MODELS", "Use a disposable app-data root without installed models.", "Open the native desktop and inspect both model cards.", "Each missing model is identified and analysis is blocked without a download.", "Record visible readiness and blocked action."],
      ["EMPTY_MODELS", "Keep the same first-run setup and do not authorize download.", "Inspect provenance and the explicit download control without pressing it.", "Model identity and revision remain discoverable; no network transfer begins.", "Record setup controls and absence of automatic transfer."],
    ]],
    ["UAT-MODEL-02", "Offline import and recovery", [
      ["OWNED_MODELS", "Have an authorized local folder containing the pinned models.", "Import that folder offline and run Verify.", "Only verified exact revisions become ready; progress and recovery are clear.", "Record readiness and Verify outcome without copying model files."],
      ["OWNED_MODELS", "Use a controlled disposable incomplete or damaged copy.", "Attempt Verify and then inspect the explicit recovery choices.", "Damaged or wrong revisions stay blocked until verified recovery; no substitution occurs.", "Record the error, recovery choice and final state."],
      ["EMPTY_MODELS", "Use an authorized disposable model location and explicitly permit the pinned download.", "Start download, observe progress, cancel, then resume the same approved revision.", "Cancellation and resumed progress are truthful; only a complete verified revision becomes ready.", "Record revision, progress, cancellation and resumed Verify outcome without model files."],
    ]],
    ["UAT-MODEL-03", "Language evidence", [
      ["FEEDBACK_CSV", "Load the synthetic English and French rows from feedback-v1.csv.", "Analyze and inspect the supplied language beside the language check.", "Warnings and detector evidence are distinct from supplied tags and model labels.", "Record both language fields and warning text on the selected rows."],
      ["SHORT_TEXT", "Use the short synthetic factual row SYN-006.", "Inspect an undetermined or low-evidence language state when it occurs.", "An undetermined check is reported as evidence, not as a forced language label.", "Record the actual detector state; do not demand a particular score."],
    ]],
    ["UAT-PROJECT-01", "CSV selection and validation", [
      ["FEEDBACK_CSV", "Open feedback-v1.csv with its message column.", "Select message as the text column and preview import.", "Column choice is explicit and synthetic metadata is reported truthfully.", "Record chosen column and preview counts."],
      ["FEEDBACK_CSV", "Keep the same CSV containing a blank message and duplicate ID.", "Complete import and inspect the affected rows.", "Invalid and duplicate rows have distinct reasons; row identities remain stable.", "Record source row IDs and displayed validation reasons."],
    ]],
    ["UAT-PROJECT-02", "Progress and cancellation", [
      ["FEEDBACK_CSV", "Create a disposable project from feedback-v1.csv with ready models.", "Start batch analysis and observe row progress and Cancel.", "Progress names the current work while controls remain usable.", "Record progress and control responsiveness."],
      ["FEEDBACK_CSV", "Use a disposable project with a still-running analysis.", "Cancel before commit and then reopen the project.", "Cancellation leaves no partial committed analysis; retry follows the existing workflow.", "Record before/after project stage and retry path."],
    ]],
    ["UAT-PROJECT-03", "Persistence and conservative deletion", [
      ["FEEDBACK_CSV", "Keep a disposable analyzed project with a review and a note.", "Close the app and reopen the same project.", "Stored AI records, review and notes remain available after restart.", "Record project identity and visible persisted fields."],
      ["FEEDBACK_CSV", "Use a disposable project that can safely be deleted.", "Read the delete wording, cancel once, then confirm deletion.", "The warning is conservative and the project is removed from app data files only.", "Record confirmation wording and list state before/after."],
    ]],
    ["UAT-RESULT-01", "Results record identity", [
      ["FEEDBACK_CSV", "Select an analyzed synthetic row visible in Results.", "Apply a filter that moves the same row and use Review this row.", "The visibly selected original record remains selected and Review opens that record.", "Record visible record ID before and after navigation."],
      ["TWO_PROJECTS", "Create two disposable synthetic projects with overlapping row positions.", "Filter out the selected row, then switch projects.", "Selection clears and Review is disabled when identity is absent or project changes.", "Record selection and action state on both projects."],
    ]],
    ["UAT-RESULT-02", "Scores and failure categories", [
      ["FEEDBACK_CSV", "Analyze the synthetic CSV with approved pinned models.", "Inspect a successful row's sentiment, compact scores and native detail.", "Threshold, independent activations and neutral fallback are explained without a quality claim.", "Record score labels, threshold and displayed fallback rule."],
      ["FEEDBACK_CSV", "Use the blank or duplicate row and a controlled inference failure.", "Compare import-invalid and analysis-failed row details.", "The two failure categories and reasons remain distinct and no missing row looks successful.", "Record each row ID and its visible status/reason."],
    ]],
    ["UAT-RESULT-03", "Result and reviewed exports", [
      ["FEEDBACK_CSV", "Analyze the synthetic project, keeping failed source rows.", "Export normalized Results with selected options.", "All contracted rows, errors, model identities and selected fields are represented safely.", "Record export options and sanitized column/count checks."],
      ["FEEDBACK_CSV", "Complete a synthetic human review on one row.", "Export reviewed CSV with and without optional native scores.", "AI and human fields remain separate; options change only intended columns.", "Record header and safe count comparisons, not private content."],
    ]],
    ["UAT-REVIEW-01", "Independent human judgments", [
      ["FEEDBACK_CSV", "Open one analyzed synthetic record in Review.", "Accept one task and leave the other unresolved, then save.", "AI data is immutable and partial review is not whole-record complete.", "Record independent judgment states and immutable AI fields."],
      ["FEEDBACK_CSV", "Keep that record and its original AI evidence.", "Correct one task and mark the other uncertain.", "Valid human labels stay separate; uncertain clears that task's human label.", "Record correction, uncertainty and Agreement denominator behavior."],
    ]],
    ["UAT-REVIEW-02", "Unsaved changes and conflicts", [
      ["FEEDBACK_CSV", "Edit a synthetic review without saving.", "Navigate away, cancel the prompt, then explicitly save or discard.", "Unsaved work is not silently lost and focus returns to a usable control.", "Record prompt and selected outcome."],
      ["TWO_PROCESSES", "Open the same disposable project in two controlled app processes.", "Make competing review mutations and inspect the stale writer's result.", "Conflict is explicit and no wrong-record or overwritten review is reported as saved.", "Record project/record IDs and the conflict message."],
    ]],
    ["UAT-REVIEW-03", "Queue and progress", [
      ["FEEDBACK_CSV", "Analyze the synthetic rows and open the Review queue.", "Apply a queue filter and navigate to the next reviewable row.", "Queue counts and next target match the visible filtered project scope.", "Record queue count and selected record ID."],
      ["FEEDBACK_CSV", "Leave a record partially or uncertainly reviewed.", "Inspect review progress and Agreement eligibility.", "Partial or uncertain work is not reported as definitive completion.", "Record progress and denominator labels."],
    ]],
    ["UAT-INSIGHTS-01", "Group metrics and denominators", [
      ["FEEDBACK_CSV", "Analyze synthetic rows with approved source metadata.", "Choose one then multiple groups and compare AI and human perspectives.", "Only trusted metadata groups rows; raw numerators, denominators and warnings are visible.", "Record selected groups, metric and raw denominators."],
      ["FEEDBACK_CSV", "Keep invalid source rows and reviewed/uncertain rows present.", "Inspect Agreement and failed-row group context.", "Failed rows stay outside metric denominators and warnings identify small samples.", "Record separate success, failure and definitive counts."],
    ]],
    ["UAT-INSIGHTS-02", "Notes and representative cases", [
      ["FEEDBACK_CSV", "Open an analyzed synthetic project in Insights.", "Add a context note with a safe synthetic phrase and tag.", "The note is separate from AI and review data and persists as documented.", "Record note association and unchanged AI labels."],
      ["FEEDBACK_CSV", "Keep existing synthetic notes and analysis rows.", "Select a representative case rule and inspect local-text display.", "Selection follows the documented rule and does not invent a model conclusion.", "Record selected case ID, rule and visibility state."],
    ]],
    ["UAT-INSIGHTS-03", "Exports and spreadsheet safety", [
      ["FEEDBACK_CSV", "Use an analyzed project with synthetic metadata only.", "Export Insights with chosen optional text/native fields.", "Audit row contains UTC time, definition, provenance, counts and chosen options.", "Record sanitized audit header and denominator checks."],
      ["FEEDBACK_CSV", "Use SYN-011 with the synthetic formula-leading source label.", "Export normalized, reviewed and Insights CSV as applicable.", "Formula-leading cells are escaped and never execute in a spreadsheet.", "Record safe exported cell prefix without opening untrusted formulas."],
    ]],
    ["UAT-FAILURE-01", "Cross-process contention", [
      ["TWO_PROCESSES", "Use two controlled app processes on one disposable project.", "Start competing analysis or project mutations.", "The second process gets an actionable busy/conflict state without partial commit.", "Record both process roles and visible messages."],
      ["TWO_PROCESSES", "Use two controlled app processes sharing disposable model storage.", "Attempt concurrent model import and inspect both results.", "Scoped model lock prevents collision and gives a recoverable message.", "Record readiness and action feedback for both processes."],
    ]],
    ["UAT-FAILURE-02", "Storage failure recovery", [
      ["SAFE_FAULTS", "Use a disposable read-only or held-open file setup, not a real user folder.", "Attempt one project mutation and inspect recovery.", "An actionable error occurs with no partial committed state.", "Record fault setup, message and unchanged project revision."],
      ["SAFE_FAULTS", "Use a bounded disposable disk-full simulation only if safely available.", "Attempt analysis and reopen the project after failure.", "No false success or corruption is shown; unavailable setup remains NOT RUN.", "Record setup limits, observed message and reopened state."],
    ]],
    ["UAT-FAILURE-03", "Input capacity and recovery", [
      ["LONG_TEXT", "Generate the synthetic long text with the tracked deterministic recipe.", "Attempt complete-input analysis and inspect the error.", "A model-capacity refusal identifies no truncation or partial result.", "Record length, refusal code and empty result state."],
      ["LONG_TEXT", "Keep the refused synthetic row and a disposable project.", "Reopen and retry a valid short row; note any shutdown warning.", "A refused row is not success, valid retry is recoverable, and crashes remain visible.", "Record row states and any actual crash or teardown signal."],
    ]],
    ["UAT-A11Y-01", "Keyboard-only workflow", [
      ["WINDOWS_A11Y", "Use the real Windows desktop with keyboard only and synthetic data.", "Traverse Setup, Projects, Analyze, Results and Review.", "Controls are reachable in logical order, focus visible and no trap blocks the flow.", "Record keyboard path and focus observations."],
      ["WINDOWS_A11Y", "Keep the same keyboard-only setup.", "Traverse Agreement, Insights/notes, export and failure recovery.", "Actions remain operable and navigation/focus behavior is understandable.", "Record keyboard path and any unreachable control."],
    ]],
    ["UAT-A11Y-02", "UI Automation and Narrator", [
      ["WINDOWS_A11Y", "Enable actual Windows Narrator on the native desktop.", "Inspect names, roles and states across main pages and dialogs.", "Narrator exposes meaningful controls and state without a source-only inference.", "Record actual speech/interaction observations and UI Automation names."],
      ["WINDOWS_A11Y", "Keep Narrator running on synthetic Results and Review.", "Navigate scores, warnings, record selection and progress.", "Important record and result information is read and actionable.", "Record spoken labels, selected ID and missing announcements."],
    ]],
    ["UAT-A11Y-03", "Focus return", [
      ["WINDOWS_A11Y", "Use a keyboard-operated native dialog and validation error.", "Dismiss dialog and submit one invalid synthetic value.", "Focus returns to a relevant visible control or error.", "Record focused control before and after both actions."],
      ["WINDOWS_A11Y", "Use loading/cancel and an unsaved-change prompt.", "Cancel loading and choose a prompt action.", "Focus remains visible and moves to a useful control after each transition.", "Record focus target after both transitions."],
    ]],
    ["UAT-A11Y-04", "Windows high contrast", [
      ["WINDOWS_A11Y", "Enable a real Windows high-contrast theme.", "Inspect navigation, focus, controls and status in the native app.", "Critical text and state remain discernible in the actual theme.", "Record theme and legibility/focus observations."],
      ["WINDOWS_A11Y", "Keep high contrast enabled with synthetic project data.", "Operate Review, export and an error recovery path.", "Actions and error state remain usable without color-only cues.", "Record actual controls and any invisible state."],
    ]],
    ["UAT-A11Y-05", "Windows DPI", [
      ["WINDOWS_A11Y", "Set Windows scaling to 100% at the supported minimum width.", "Inspect Results, Review, Agreement and Insights scroll/reflow.", "Critical actions remain reachable with intended scrolling.", "Record scale, width and reachable action observations."],
      ["WINDOWS_A11Y", "Set Windows scaling to 150% at the supported minimum width.", "Repeat the same page and action route.", "Critical content and actions remain accessible without clipping loss.", "Record scale, width and any clipped control."],
    ]],
    ["UAT-A11Y-06", "Windows text-size increase", [
      ["WINDOWS_A11Y", "Increase Windows text size and use the minimum app width.", "Inspect the Review queue's fixed-pixel geometry.", "Visible text and row actions remain readable or an actual defect is recorded.", "Record text-size setting, width and queue observations."],
      ["WINDOWS_A11Y", "Keep the enlarged text size with synthetic project data.", "Operate selection, Review action and adjacent critical controls.", "No wrong-record action or inaccessible critical control occurs.", "Record selected record ID, focus and action reachability."],
    ]],
  ];

  const fixtures = {
    FEEDBACK_CSV: "Project-authored feedback-v1.csv; choose the message column; contains deliberate invalid rows and a formula-leading marker.",
    SHORT_TEXT: "The short factual row SYN-006 from feedback-v1.csv; detector outcome must be observed rather than assumed.",
    EMPTY_MODELS: "Disposable empty app-data location; do not delete existing personal model storage.",
    OWNED_MODELS: "Authorized local pinned models or controlled disposable copies; no model files are supplied by this pack.",
    TWO_PROJECTS: "Two disposable projects made from the same tracked synthetic CSV; keep project identity explicit.",
    TWO_PROCESSES: "Two controlled native app processes on a disposable project/model location.",
    SAFE_FAULTS: "Disposable bounded read-only, held-open or simulated disk-full setup; never exhaust the host disk.",
    LONG_TEXT: "Generated locally by the tracked make_long_text.py recipe; no model output is prefilled.",
    WINDOWS_A11Y: "Real Windows desktop and assistive settings; no offscreen substitute.",
  };
  const scenarios = definitions.map(([id, title, rows]) => ({
    id, title,
    steps: rows.map(([fixture_id, precondition, action, expected, evidence], index) => ({
      id: `${id}-S${String(index + 1).padStart(2, "0")}`,
      fixture_id, precondition, action, expected, evidence, required: true,
    })),
  }));
  const pack = { schema_version: 1, protocol_version: "1.0.0", pack_version: "1.0.0", fixture_version: "1.0.0", data_class: "SYNTH_UAT", fixtures, scenarios };
  root.STI_UAT_PACK = pack;
  if (typeof module !== "undefined" && module.exports) module.exports = pack;
})(typeof window !== "undefined" ? window : globalThis);
