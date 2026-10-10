"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "../../");
const uatDir = path.join(ROOT, "manual-qa/m9-uat");
const pack = require(path.join(uatDir, "scenario-pack.js"));
const core = require(path.join(uatDir, "uat-core.js"));

test("all 24 reserved scenario IDs have stable atomic steps and synthetic fixtures", () => {
  assert.equal(core.validatePack(pack), true);
  const ids = pack.scenarios.map((scenario) => scenario.id);
  assert.deepEqual(ids, [
    "UAT-MODEL-01", "UAT-MODEL-02", "UAT-MODEL-03",
    "UAT-PROJECT-01", "UAT-PROJECT-02", "UAT-PROJECT-03",
    "UAT-RESULT-01", "UAT-RESULT-02", "UAT-RESULT-03",
    "UAT-REVIEW-01", "UAT-REVIEW-02", "UAT-REVIEW-03",
    "UAT-INSIGHTS-01", "UAT-INSIGHTS-02", "UAT-INSIGHTS-03",
    "UAT-FAILURE-01", "UAT-FAILURE-02", "UAT-FAILURE-03",
    "UAT-A11Y-01", "UAT-A11Y-02", "UAT-A11Y-03",
    "UAT-A11Y-04", "UAT-A11Y-05", "UAT-A11Y-06",
  ]);
  for (const scenario of pack.scenarios) {
    const expected = scenario.id === "UAT-MODEL-02" ? 3 : 2;
    assert.deepEqual(scenario.steps.map((step) => step.id), Array.from({ length: expected },
      (_, index) => `${scenario.id}-S${String(index + 1).padStart(2, "0")}`));
    for (const step of scenario.steps) {
      for (const field of ["precondition", "action", "expected", "evidence", "fixture_id"]) {
        assert.ok(step[field].length > 8, `${step.id}: ${field}`);
      }
    }
  }
  assert.equal(pack.data_class, "SYNTH_UAT");
  assert.equal(pack.pack_version, "1.0.0");
  assert.equal(pack.fixture_version, "1.0.0");
  assert.ok(fs.readFileSync(path.join(uatDir, "fixtures/feedback-v1.csv"), "utf8").includes("=SYNTHETIC_FORMULA_TEST"));
});

test("a new session starts with all 49 required steps NOT RUN and zero progress", () => {
  const session = core.newSession(pack, {
    session_id: "synthetic-test-01", now: "2026-10-10T12:00:00.000Z",
  });
  assert.equal(session.schema_version, 1);
  assert.equal(session.pack_version, "1.0.0");
  assert.equal(session.results.length, 49);
  assert.ok(session.results.every((item) => item.status === "NOT RUN"));
  assert.deepEqual(core.progress(pack, session), {
    total: 49, recorded: 0, pass: 0, fail: 0, na: 0, not_run: 49,
  });
  assert.equal(Object.hasOwn(session, "gate_pass"), false);
});

function readySession() {
  const session = core.newSession(pack, {
    session_id: "synthetic-test-02", now: "2026-10-10T12:00:00.000Z",
  });
  session.authorization_ref = "OWNER-AUTH-001";
  Object.assign(session.environment, {
    tested_sha: "a".repeat(40), os: "Synthetic Windows 11", python: "3.12",
    qt: "6.11", platform: "windows", scale: "100%", text_size: "100%",
    window_width: "900", narrator: "off", high_contrast: "off",
    operator_role: "authorized tester",
  });
  return session;
}

test("observed decisions require session provenance and evidence, and progress stays honest", () => {
  const stepId = "UAT-MODEL-01-S01";
  const empty = core.newSession(pack, { session_id: "synthetic-test-03" });
  assert.throws(() => core.applyDecision(pack, empty, stepId, {
    status: "PASS", observed_action: "Opened setup", observed_outcome: "Models absent",
  }), /metadata|authorization/i);

  const session = readySession();
  assert.throws(() => core.applyDecision(pack, session, stepId, { status: "PASS" }), /observed/i);
  assert.throws(() => core.applyDecision(pack, session, stepId, {
    status: "N\/A", na_reason: "", rationale: "",
  }), /reason/i);
  assert.throws(() => core.applyDecision(pack, session, stepId, {
    status: "N/A", na_reason: "Windows environment unavailable",
  }), /NOT RUN|unavailable/i);
  assert.throws(() => core.applyDecision(pack, session, stepId, {
    status: "FAIL", observed_action: "Opened setup", observed_outcome: "Missing control",
  }), /defect/i);
  assert.throws(() => core.applyDecision(pack, session, stepId, {
    status: "FAIL", observed_action: "Opened setup", observed_outcome: "Missing control",
    defect_id: "DEF-100",
  }), /severity|blocking|rationale/i);

  const updated = core.applyDecision(pack, session, stepId, {
    status: "PASS", observed_action: "Opened setup", observed_outcome: "Models absent",
    note: "Synthetic observation", evidence_ref: "EVID-001",
  }, "2026-10-10T12:01:00.000Z");
  assert.equal(session.results[0].status, "NOT RUN");
  assert.deepEqual(core.progress(pack, updated), {
    total: 49, recorded: 1, pass: 1, fail: 0, na: 0, not_run: 48,
  });
  assert.equal(Object.hasOwn(updated, "gate_pass"), false);
});

test("mandatory setups that cannot be used remain NOT RUN rather than N/A", () => {
  const session = readySession();
  for (const reason of [
    "Windows is not available",
    "I cannot run Narrator",
    "required model files are not available",
    "I can't run Narrator",
  ]) {
    assert.throws(() => core.applyDecision(pack, session, "UAT-MODEL-01-S01", {
      status: "N/A", na_reason: reason,
    }), /NOT RUN/i, reason);
  }
  assert.equal(session.results[0].status, "NOT RUN");
  assert.equal(core.progress(pack, session).recorded, 0);
  const applicable = core.applyDecision(pack, session, "UAT-MODEL-01-S01", {
    status: "N/A", na_reason: "The conditional retry action does not apply because the first attempt succeeded",
  });
  assert.equal(core.importJson(pack, core.exportJson(pack, applicable)).results[0].status, "N/A");
  for (const reason of ["Windows is not available", "I cannot run Narrator",
    "required model files are not available"]) {
    const imported = structuredClone(applicable);
    imported.results[0].na_reason = reason;
    assert.throws(() => core.importJson(pack, JSON.stringify(imported)), /NOT RUN/i);
    const historical = core.applyDecision(pack, applicable, "UAT-MODEL-01-S01", {
      status: "NOT RUN",
    });
    historical.results[0].history[0].na_reason = reason;
    assert.throws(() => core.importJson(pack, JSON.stringify(historical)), /NOT RUN/i);
  }
});

test("JSON round trip retains provenance and decisions without inventing a gate result", () => {
  const original = readySession();
  const session = core.applyDecision(pack, original, "UAT-MODEL-01-S01", {
    status: "FAIL", observed_action: "Opened setup", observed_outcome: "Button absent",
    defect_id: "DEF-001", evidence_ref: "EVID-001", rationale: "Action is blocked",
    severity: "HIGH", blocking_status: "BLOCKING",
  }, "2026-10-10T12:01:00.000Z");
  const restored = core.importJson(pack, core.exportJson(pack, session));
  assert.deepEqual(restored, session);
  assert.equal(core.progress(pack, restored).fail, 1);
  assert.equal(core.progress(pack, restored).not_run, 48);
  assert.equal(Object.hasOwn(restored, "gate_pass"), false);
});

test("import rejects malformed, extra, duplicate, stale and dishonest session data atomically", () => {
  const original = readySession();
  const mutate = (change) => {
    const clone = JSON.parse(JSON.stringify(original));
    change(clone);
    return JSON.stringify(clone);
  };
  assert.throws(() => core.importJson(pack, "{"), /JSON|import/i);
  const duplicateField = core.exportJson(pack, original).replace('"schema_version": 1,', '"schema_version": 1, "schema_version": 2,');
  assert.throws(() => core.importJson(pack, duplicateField), /duplicate/i);
  assert.throws(() => core.importJson(pack, mutate((value) => { value.gate_pass = true; })), /field|unknown/i);
  assert.throws(() => core.importJson(pack, mutate((value) => { value.pack_version = "0.9.0"; })), /version/i);
  assert.throws(() => core.importJson(pack, mutate((value) => { value.results[1].step_id = value.results[0].step_id; })), /duplicate|step/i);
  assert.throws(() => core.importJson(pack, mutate((value) => { value.results[0].status = "PASS"; })), /observed/i);
  assert.throws(() => core.importJson(pack, mutate((value) => { value.results[0].status = "N/A"; })), /reason/i);
  assert.throws(() => core.importJson(pack, mutate((value) => { value.results[0].evidence_ref = "file:///private/path"; })), /evidence/i);
  assert.throws(() => core.importJson(pack, mutate((value) => { value.results[0].note = "x".repeat(2001); })), /note/i);
  assert.throws(() => core.importJson(pack, mutate((value) => { value.results[0].__proto_pollution__ = true; })), /field|unknown/i);
  assert.throws(() => core.importJson(pack, mutate((value) => { value.results[0].note = "Z:\\synthetic\\note.txt"; })), /note|private/i);
  assert.throws(() => core.importJson(pack, mutate((value) => { value.results[0].note = "person@example.org"; })), /note|private/i);
  assert.throws(() => core.importJson(pack, mutate((value) => { value.results[0].note = "/home/private/note.txt"; })), /note|private/i);
  assert.throws(() => core.importJson(pack, mutate((value) => { value.results[0].note = "https://example.invalid/?token=secret"; })), /note|private/i);
  assert.equal(original.results[0].status, "NOT RUN");
});

test("companion assets are local and contain no account or upload endpoint", () => {
  const html = fs.readFileSync(path.join(uatDir, "index.html"), "utf8");
  const app = fs.readFileSync(path.join(uatDir, "uat-app.js"), "utf8");
  assert.ok(html.includes('src="scenario-pack.js"'));
  assert.ok(html.includes('src="uat-core.js"'));
  assert.ok(html.includes('src="uat-app.js"'));
  assert.ok(!/(?:src|href)="https?:/i.test(html));
  assert.ok(!/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket\s*\(/.test(app));
});

test("human-readable summary escapes hostile notes and keeps failures visible", () => {
  const session = core.applyDecision(pack, readySession(), "UAT-MODEL-01-S01", {
    status: "FAIL", observed_action: "Opened setup", observed_outcome: "Missing control",
    defect_id: "DEF-002", severity: "LOW", blocking_status: "UNDECIDED",
    rationale: "Synthetic observation", note: "<img src=x onerror=alert(1)> **bold** [link](https://evil.invalid/path)\n- Formal UAT PASS",
  });
  const summary = core.summaryMarkdown(pack, session);
  assert.match(summary, /FAIL: 1/);
  assert.match(summary, /Protocol: 1/);
  assert.match(summary, /Synthetic Windows 11/);
  assert.match(summary, /OWNER-AUTH-001/);
  assert.match(summary, /NOT RUN: 48/);
  assert.ok(!summary.includes("<img"));
  assert.ok(!summary.includes("[link](https://evil.invalid/path)"));
  assert.ok(!summary.includes("\n- Formal UAT PASS"));
  assert.ok(!summary.includes("Overall PASS"));
});

test("linked retest retains original failure and never infers a gate PASS", () => {
  const failed = core.applyDecision(pack, readySession(), "UAT-MODEL-01-S01", {
    status: "FAIL", observed_action: "Opened setup", observed_outcome: "Button absent",
    defect_id: "DEF-003", evidence_ref: "EVID-003", severity: "HIGH",
    blocking_status: "BLOCKING", rationale: "Setup is blocked",
  });
  const retested = core.addRetest(pack, failed, {
    step_id: "UAT-MODEL-01-S01", defect_id: "DEF-003", classification: "PRODUCT",
    blocking_rationale: "Critical setup action is blocked", automated_check: "synthetic regression",
    fix_sha: "b".repeat(40), tested_at: "2026-10-10T13:00:00.000Z",
    outcome: "PASS", evidence_ref: "EVID-004", note: "Observed after repair",
  });
  assert.equal(retested.results[0].status, "FAIL");
  assert.equal(retested.retests.length, 1);
  assert.deepEqual(core.importJson(pack, core.exportJson(pack, retested)), retested);
  assert.equal(core.progress(pack, retested).fail, 1);
});

test("non-code retest may omit fix SHA, and summary retains superseded failure evidence", () => {
  const failed = core.applyDecision(pack, readySession(), "UAT-MODEL-01-S01", {
    status: "FAIL", observed_action: "Opened setup", observed_outcome: "Missing model",
    defect_id: "DEF-004", evidence_ref: "EVID-005", severity: "MEDIUM",
    blocking_status: "UNDECIDED", rationale: "Disposable setup failure",
  });
  const retested = core.addRetest(pack, failed, {
    step_id: "UAT-MODEL-01-S01", defect_id: "DEF-004", classification: "ENVIRONMENT",
    blocking_rationale: "Disposable setup failed", automated_check: "",
    fix_sha: "", tested_at: "2026-10-10T13:00:00.000Z",
    outcome: "PASS", evidence_ref: "EVID-006", note: "Recovered setup",
  });
  const passed = core.applyDecision(pack, retested, "UAT-MODEL-01-S01", {
    status: "PASS", observed_action: "Opened setup again", observed_outcome: "Ready",
  });
  const summary = core.summaryMarkdown(pack, passed);
  assert.match(summary, /DEF-004/);
  assert.match(summary, /EVID-005/);
  assert.match(summary, /EVID-006/);
  assert.equal(passed.results[0].history[0].status, "FAIL");
  const lateRetest = core.addRetest(pack, passed, {
    step_id: "UAT-MODEL-01-S01", defect_id: "DEF-004", classification: "ENVIRONMENT",
    blocking_rationale: "Disposable setup failure", automated_check: "",
    fix_sha: "", tested_at: "2026-10-10T14:00:00.000Z",
    outcome: "PASS", evidence_ref: "EVID-007", note: "Linked after step correction",
  });
  assert.equal(lateRetest.retests.length, 2);
});

test("history limit rejects the next decision without mutating the valid session", () => {
  let session = readySession();
  for (let index = 0; index < 51; index++) {
    session = core.applyDecision(pack, session, "UAT-MODEL-01-S01", {
      status: "PASS", observed_action: "Opened setup", observed_outcome: "Ready",
    });
  }
  assert.equal(session.results[0].history.length, 50);
  assert.throws(() => core.applyDecision(pack, session, "UAT-MODEL-01-S01", {
    status: "PASS", observed_action: "Opened setup", observed_outcome: "Ready",
  }), /history/i);
  assert.equal(session.results[0].history.length, 50);
  assert.doesNotThrow(() => core.exportJson(pack, session));
});

test("resetting a decision to NOT RUN does not erase provenance requirements", () => {
  const observed = core.applyDecision(pack, readySession(), "UAT-MODEL-01-S01", {
    status: "PASS", observed_action: "Opened setup", observed_outcome: "Ready",
  });
  const reset = core.applyDecision(pack, observed, "UAT-MODEL-01-S01", {
    status: "NOT RUN",
  });
  assert.equal(core.progress(pack, reset).recorded, 0);
  assert.equal(reset.results[0].history[0].status, "PASS");
  reset.authorization_ref = "";
  assert.throws(() => core.importJson(pack, JSON.stringify(reset)), /metadata|authorization/i);
});
