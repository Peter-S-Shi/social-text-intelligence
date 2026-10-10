"use strict";

(function (root) {
  const reserved = ["MODEL", "PROJECT", "RESULT", "REVIEW", "INSIGHTS", "FAILURE", "A11Y"]
    .flatMap((family) => Array.from({ length: family === "A11Y" ? 6 : 3 }, (_, index) =>
      `UAT-${family}-${String(index + 1).padStart(2, "0")}`));

  function validatePack(pack) {
    if (!pack || pack.schema_version !== 1 || pack.protocol_version !== "1.0.0" ||
        pack.pack_version !== "1.0.0" ||
        pack.fixture_version !== "1.0.0" || pack.data_class !== "SYNTH_UAT" ||
        !pack.fixtures || !Array.isArray(pack.scenarios) || pack.scenarios.length !== 24) {
      throw new Error("Unsupported or incomplete scenario pack.");
    }
    if (JSON.stringify(pack.scenarios.map((item) => item.id)) !== JSON.stringify(reserved)) {
      throw new Error("Reserved scenario IDs changed.");
    }
    for (const scenario of pack.scenarios) {
      if (typeof scenario.title !== "string" || !Array.isArray(scenario.steps) ||
          scenario.steps.length !== (scenario.id === "UAT-MODEL-02" ? 3 : 2)) {
        throw new Error("Incomplete scenario.");
      }
      scenario.steps.forEach((step, index) => {
        if (step.id !== `${scenario.id}-S${String(index + 1).padStart(2, "0")}` ||
            step.required !== true || !Object.hasOwn(pack.fixtures, step.fixture_id) ||
            ["precondition", "action", "expected", "evidence", "fixture_id"]
              .some((key) => typeof step[key] !== "string" || step[key].length < 9)) {
          throw new Error(`Invalid step in ${scenario.id}.`);
        }
      });
    }
    return true;
  }

  function newSession(pack, options = {}) {
    validatePack(pack);
    const now = options.now || new Date().toISOString();
    const sessionId = options.session_id ||
      (root.crypto && root.crypto.randomUUID ? root.crypto.randomUUID() :
        `uat-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`);
    return {
      schema_version: 1, session_id: sessionId,
      protocol_version: pack.protocol_version, pack_version: pack.pack_version,
      fixture_version: pack.fixture_version,
      created_at: now, updated_at: now, authorization_ref: "",
      environment: {
        tested_sha: "", os: "", python: "", qt: "", platform: "",
        scale: "", text_size: "", window_width: "", narrator: "",
        high_contrast: "", operator_role: "",
      },
      results: pack.scenarios.flatMap((scenario) => scenario.steps.map((step) => ({
        step_id: step.id, status: "NOT RUN", observed_action: "",
        observed_outcome: "", rationale: "", na_reason: "", note: "",
        severity: "", blocking_status: "",
        defect_id: "", evidence_ref: "", history: [],
      }))),
      retests: [],
    };
  }

  function progress(pack, session) {
    const total = pack.scenarios.reduce((count, scenario) => count + scenario.steps.length, 0);
    const counts = { total, recorded: 0, pass: 0, fail: 0, na: 0, not_run: 0 };
    for (const result of session.results) {
      if (result.status === "PASS") counts.pass++;
      else if (result.status === "FAIL") counts.fail++;
      else if (result.status === "N/A") counts.na++;
      else counts.not_run++;
    }
    counts.recorded = counts.pass + counts.fail + counts.na;
    return counts;
  }

  function checkedText(value, name, limit) {
    if (typeof value !== "string" || value.length > limit ||
        /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(value) ||
        /(?:^|[\s(])(?:[A-Za-z]:[\\/]|\/(?:home|users|tmp|var|etc)\/)|file:\/\/|\\\\[^\s]+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|https?:\/\/[^\s]*[?&](?:token|key|secret|password)=/i.test(value)) {
      throw new Error(`Invalid ${name}.`);
    }
    return value;
  }

  function requireMetadata(session) {
    if (!session.authorization_ref || !/^[a-fA-F0-9]{40}$/.test(session.environment.tested_sha) ||
        Object.values(session.environment).some((value) => typeof value !== "string" ||
          !value.trim())) {
      throw new Error("Tested commit, environment metadata and authorization are required.");
    }
  }

  function validNaReason(reason) {
    return reason.trim() && !/\b(unavailable|not available|cannot (?:access|run)|can't (?:access|run)|could not run|not installed|missing setup|no windows|no model|no permission)\b/i.test(reason);
  }

  function applyDecision(pack, session, stepId, fields, now = new Date().toISOString()) {
    validateSession(pack, session);
    const known = pack.scenarios.some((scenario) => scenario.steps.some((step) => step.id === stepId));
    if (!known) throw new Error("Unknown step ID.");
    const allowed = ["status", "observed_action", "observed_outcome", "rationale",
      "severity", "blocking_status",
      "na_reason", "note", "defect_id", "evidence_ref"];
    if (!fields || Object.keys(fields).some((key) => !allowed.includes(key))) {
      throw new Error("Unknown decision field.");
    }
    const status = fields.status;
    if (!["PASS", "FAIL", "N/A", "NOT RUN"].includes(status)) {
      throw new Error("Invalid decision status.");
    }
    const result = Object.fromEntries(allowed.map((key) => [key,
      checkedText(fields[key] === undefined ? "" : fields[key], key, key === "note" ? 2000 : 500)]));
    if (status !== "NOT RUN") requireMetadata(session);
    if (["PASS", "FAIL"].includes(status) &&
        (!result.observed_action.trim() || !result.observed_outcome.trim())) {
      throw new Error("Observed action and outcome are required.");
    }
    if (status === "N/A" && !validNaReason(result.na_reason)) {
      throw new Error("An actual applicability reason is required for N/A; unavailable setup stays NOT RUN.");
    }
    if (status === "FAIL" && !result.defect_id.trim()) {
      throw new Error("A defect ID is required for FAIL.");
    }
    if (status === "FAIL" &&
        (!result.rationale.trim() || !["CRITICAL", "HIGH", "MEDIUM", "LOW"].includes(result.severity) ||
         !["BLOCKING", "NON_BLOCKING", "UNDECIDED"].includes(result.blocking_status))) {
      throw new Error("FAIL requires severity, blocking status and rationale.");
    }
    if (result.defect_id && !/^DEF-[A-Z0-9-]{1,48}$/.test(result.defect_id)) {
      throw new Error("Invalid defect ID.");
    }
    if (result.evidence_ref && !/^EVID-[A-Z0-9-]{1,48}$/.test(result.evidence_ref)) {
      throw new Error("Use an opaque evidence reference, never a path or URL.");
    }
    const updated = JSON.parse(JSON.stringify(session));
    const index = updated.results.findIndex((item) => item.step_id === stepId);
    if (index < 0) throw new Error("Step missing from session.");
    const previous = updated.results[index];
    if (previous.status !== "NOT RUN") {
      previous.history.push({ status: previous.status, observed_action: previous.observed_action,
        observed_outcome: previous.observed_outcome, rationale: previous.rationale,
        severity: previous.severity, blocking_status: previous.blocking_status,
        na_reason: previous.na_reason, note: previous.note, defect_id: previous.defect_id,
        evidence_ref: previous.evidence_ref, replaced_at: now });
    }
    Object.assign(previous, result);
    updated.updated_at = now;
    validateSession(pack, updated);
    return updated;
  }

  const decisionFields = ["status", "observed_action", "observed_outcome", "rationale",
    "severity", "blocking_status",
    "na_reason", "note", "defect_id", "evidence_ref"];
  const environmentFields = ["tested_sha", "os", "python", "qt", "platform", "scale",
    "text_size", "window_width", "narrator", "high_contrast", "operator_role"];

  function exactFields(value, fields, name) {
    if (!value || typeof value !== "object" || Array.isArray(value) ||
        Object.keys(value).length !== fields.length ||
        Object.keys(value).some((key) => !fields.includes(key))) {
      throw new Error(`Unknown or missing ${name} field.`);
    }
  }

  function timestamp(value, name) {
    checkedText(value, name, 40);
    if (!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(value) ||
        !Number.isFinite(Date.parse(value)) || new Date(value).toISOString() !== value) {
      throw new Error(`Invalid ${name}.`);
    }
  }

  function validateDecisionFields(item, name, historical = false) {
    exactFields(item, historical ? [...decisionFields, "replaced_at"] :
      ["step_id", ...decisionFields, "history"], name);
    if (!["PASS", "FAIL", "N/A", "NOT RUN"].includes(item.status)) {
      throw new Error(`Invalid ${name} status.`);
    }
    for (const field of decisionFields.slice(1)) {
      checkedText(item[field], `${name} ${field}`, field === "note" ? 2000 : 500);
    }
    if (["PASS", "FAIL"].includes(item.status) &&
        (!item.observed_action.trim() || !item.observed_outcome.trim())) {
      throw new Error(`Observed action and outcome required for ${name}.`);
    }
    if (item.status === "N/A" && !validNaReason(item.na_reason)) {
      throw new Error(`Applicability reason required for ${name}; unavailable setup stays NOT RUN.`);
    }
    if (item.status === "FAIL" && !item.defect_id.trim()) {
      throw new Error(`Defect ID required for ${name}.`);
    }
    if (item.status === "FAIL" &&
        (!item.rationale.trim() || !["CRITICAL", "HIGH", "MEDIUM", "LOW"].includes(item.severity) ||
         !["BLOCKING", "NON_BLOCKING", "UNDECIDED"].includes(item.blocking_status))) {
      throw new Error(`FAIL requires severity, blocking status and rationale for ${name}.`);
    }
    if (item.status !== "FAIL" && (item.severity || item.blocking_status)) {
      throw new Error(`Invalid failure classification for ${name}.`);
    }
    if (item.defect_id && !/^DEF-[A-Z0-9-]{1,48}$/.test(item.defect_id)) {
      throw new Error(`Invalid ${name} defect ID.`);
    }
    if (item.evidence_ref && !/^EVID-[A-Z0-9-]{1,48}$/.test(item.evidence_ref)) {
      throw new Error(`Invalid ${name} evidence reference.`);
    }
    if (historical) timestamp(item.replaced_at, `${name} replaced_at`);
  }

  function validateSession(pack, session) {
    validatePack(pack);
    exactFields(session, ["schema_version", "session_id", "protocol_version", "pack_version", "fixture_version",
      "created_at", "updated_at", "authorization_ref", "environment", "results", "retests"],
    "session");
    if (session.schema_version !== 1 || session.protocol_version !== pack.protocol_version ||
        session.pack_version !== pack.pack_version ||
        session.fixture_version !== pack.fixture_version) throw new Error("Unsupported version.");
    checkedText(session.session_id, "session_id", 64);
    if (!/^[A-Za-z0-9-]{1,64}$/.test(session.session_id)) throw new Error("Invalid session ID.");
    timestamp(session.created_at, "created_at");
    timestamp(session.updated_at, "updated_at");
    checkedText(session.authorization_ref, "authorization_ref", 120);
    exactFields(session.environment, environmentFields, "environment");
    for (const field of environmentFields) {
      checkedText(session.environment[field], `environment ${field}`, 120);
    }
    if (session.environment.tested_sha &&
        !/^[a-fA-F0-9]{40}$/.test(session.environment.tested_sha)) {
      throw new Error("Invalid tested_sha.");
    }
    const expectedIds = pack.scenarios.flatMap((scenario) => scenario.steps.map((step) => step.id));
    if (!Array.isArray(session.results) || session.results.length !== expectedIds.length) {
      throw new Error("Missing or duplicate step results.");
    }
    session.results.forEach((result, index) => {
      validateDecisionFields(result, `step ${index}`);
      if (result.step_id !== expectedIds[index]) throw new Error("Unknown or duplicate step ID.");
      if (!Array.isArray(result.history) || result.history.length > 50) {
        throw new Error("Invalid decision history.");
      }
      result.history.forEach((entry) => validateDecisionFields(entry, "history", true));
    });
    if (!Array.isArray(session.retests) || session.retests.length > 200) {
      throw new Error("Invalid retest history.");
    }
    session.retests.forEach((retest) => {
      exactFields(retest, ["step_id", "defect_id", "classification", "blocking_rationale",
        "automated_check", "fix_sha", "tested_at", "outcome", "evidence_ref", "note"], "retest");
      checkedText(retest.fix_sha, "retest fix SHA", 40);
      checkedText(retest.defect_id, "retest defect ID", 52);
      checkedText(retest.evidence_ref, "retest evidence reference", 53);
      if (!expectedIds.includes(retest.step_id)) throw new Error("Unknown retest step ID.");
      if (!/^DEF-[A-Z0-9-]{1,48}$/.test(retest.defect_id)) throw new Error("Invalid retest defect ID.");
      if (!["PRODUCT", "FIXTURE", "ENVIRONMENT", "PROTOCOL"].includes(retest.classification)) {
        throw new Error("Invalid retest classification.");
      }
      if (retest.fix_sha && !/^[a-fA-F0-9]{40}$/.test(retest.fix_sha)) {
        throw new Error("Invalid retest fix SHA.");
      }
      timestamp(retest.tested_at, "retest tested_at");
      if (!["PASS", "FAIL"].includes(retest.outcome)) throw new Error("Invalid retest outcome.");
      checkedText(retest.blocking_rationale, "retest blocking rationale", 500);
      if (!retest.blocking_rationale.trim()) throw new Error("Missing retest blocking rationale.");
      checkedText(retest.automated_check, "retest automated check", 500);
      checkedText(retest.note, "retest note", 2000);
      if (!/^EVID-[A-Z0-9-]{1,48}$/.test(retest.evidence_ref)) {
        throw new Error("Invalid retest evidence reference.");
      }
      const result = session.results.find((item) => item.step_id === retest.step_id);
      if (![result, ...result.history].some((item) => item.status === "FAIL" &&
          item.defect_id === retest.defect_id)) {
        throw new Error("Retest has no original failure or matching defect ID.");
      }
    });
    if (hasObservations(session)) {
      requireMetadata(session);
    }
    return true;
  }

  function hasObservations(session) {
    return session.retests.length > 0 || session.results.some((result) =>
      result.status !== "NOT RUN" || result.history.some((entry) => entry.status !== "NOT RUN"));
  }

  function importJson(pack, json) {
    if (typeof json !== "string" || json.length > 1024 * 1024) {
      throw new Error("Invalid JSON import size.");
    }
    let value;
    try { value = JSON.parse(json); } catch { throw new Error("Invalid JSON import."); }
    rejectDuplicateMembers(json);
    validateSession(pack, value);
    return value;
  }

  function rejectDuplicateMembers(json) {
    let offset = 0;
    const space = () => { while (/\s/.test(json[offset] || "")) offset++; };
    const string = () => {
      const start = offset++;
      while (offset < json.length) {
        if (json[offset] === "\\") { offset += 2; continue; }
        if (json[offset++] === '"') break;
      }
      return JSON.parse(json.slice(start, offset));
    };
    function value(depth) {
      if (depth > 64) throw new Error("JSON import nesting limit exceeded.");
      space();
      const first = json[offset++];
      if (first === "{") {
        const keys = new Set();
        space();
        if (json[offset] === "}") { offset++; return; }
        while (offset < json.length) {
          space();
          const key = string();
          if (keys.has(key)) throw new Error("Duplicate JSON object field.");
          keys.add(key);
          space(); offset++; // colon; JSON.parse already checked syntax
          value(depth + 1);
          space();
          if (json[offset++] === "}") return;
        }
      } else if (first === "[") {
        space();
        if (json[offset] === "]") { offset++; return; }
        while (offset < json.length) {
          value(depth + 1);
          space();
          if (json[offset++] === "]") return;
        }
      } else if (first === '"') {
        offset--;
        string();
      } else {
        while (offset < json.length && !/[\s,}\]]/.test(json[offset])) offset++;
      }
    }
    value(0);
  }

  function addRetest(pack, session, retest) {
    validateSession(pack, session);
    const known = session.results.find((item) => item.step_id === retest.step_id);
    if (!known || ![known, ...known.history].some((item) => item.status === "FAIL" &&
        item.defect_id === retest.defect_id)) {
      throw new Error("Retest must link an observed failing step and its defect ID.");
    }
    const updated = JSON.parse(JSON.stringify(session));
    updated.retests.push({ ...retest });
    updated.updated_at = retest.tested_at;
    validateSession(pack, updated);
    return updated;
  }

  function exportJson(pack, session) {
    validateSession(pack, session);
    return `${JSON.stringify(session, null, 2)}\n`;
  }

  function summaryMarkdown(pack, session) {
    validateSession(pack, session);
    const escape = (value) => String(value).replace(/[\r\n]+/g, " ").replace(/&/g, "&amp;")
      .replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/[\\`*_{}\[\]()#+.!|]/g, "\\$&");
    const counts = progress(pack, session);
    const lines = ["# STI M9 UAT working summary", "",
      "Infrastructure record only. Formal acceptance decision: not assessed.", "",
      `Protocol: ${escape(session.protocol_version)}; pack: ${escape(session.pack_version)}; fixture: ${escape(session.fixture_version)}`,
      `Session: ${escape(session.session_id)}; tested SHA: ${escape(session.environment.tested_sha || "NOT RECORDED")}`,
      `Created: ${escape(session.created_at)}; updated: ${escape(session.updated_at)}`,
      `Authorization reference: ${escape(session.authorization_ref || "NOT RECORDED")}`,
      `Recorded: ${counts.recorded}/${counts.total}; PASS: ${counts.pass}; FAIL: ${counts.fail}; N/A: ${counts.na}; NOT RUN: ${counts.not_run}`,
      "", "## Environment", ""];
    for (const [field, value] of Object.entries(session.environment)) {
      lines.push(`- ${escape(field)}: ${escape(value || "NOT RECORDED")}`);
    }
    lines.push("", "## Steps", "");
    for (const result of session.results) {
      lines.push(`- ${escape(result.step_id)}: ${escape(result.status)}`);
      if (result.defect_id) lines.push(`  - Defect: ${escape(result.defect_id)}`);
      if (result.status === "FAIL") lines.push(`  - Severity: ${escape(result.severity)}; blocking status: ${escape(result.blocking_status)}`);
      if (result.note) lines.push(`  - Note: ${escape(result.note)}`);
      if (result.na_reason) lines.push(`  - N/A reason: ${escape(result.na_reason)}`);
      if (result.observed_action) lines.push(`  - Observed action: ${escape(result.observed_action)}`);
      if (result.observed_outcome) lines.push(`  - Observed outcome: ${escape(result.observed_outcome)}`);
      if (result.rationale) lines.push(`  - Rationale: ${escape(result.rationale)}`);
      if (result.evidence_ref) lines.push(`  - Evidence: ${escape(result.evidence_ref)}`);
      for (const history of result.history) {
        lines.push(`  - Earlier decision: ${escape(history.status)}; replaced ${escape(history.replaced_at)}`);
        if (history.defect_id) lines.push(`    - Original defect: ${escape(history.defect_id)}`);
        if (history.status === "FAIL") lines.push(`    - Original severity: ${escape(history.severity)}; blocking status: ${escape(history.blocking_status)}`);
        if (history.evidence_ref) lines.push(`    - Original evidence: ${escape(history.evidence_ref)}`);
        if (history.observed_outcome) lines.push(`    - Original outcome: ${escape(history.observed_outcome)}`);
        if (history.observed_action) lines.push(`    - Original action: ${escape(history.observed_action)}`);
        if (history.rationale) lines.push(`    - Original rationale: ${escape(history.rationale)}`);
        if (history.na_reason) lines.push(`    - Original N/A reason: ${escape(history.na_reason)}`);
        if (history.note) lines.push(`    - Original note: ${escape(history.note)}`);
      }
    }
    if (session.retests.length) {
      lines.push("", "## Linked retests", "");
      for (const retest of session.retests) {
        lines.push(`- ${escape(retest.step_id)} / ${escape(retest.defect_id)}: ${escape(retest.outcome)}; fix SHA ${escape(retest.fix_sha || "not applicable")}; ${escape(retest.tested_at)}`);
        lines.push(`  - Classification: ${escape(retest.classification)}; blocking rationale: ${escape(retest.blocking_rationale)}`);
        if (retest.automated_check) lines.push(`  - Automated check: ${escape(retest.automated_check)}`);
        lines.push(`  - Evidence: ${escape(retest.evidence_ref)}; note: ${escape(retest.note)}`);
      }
    }
    return `${lines.join("\n")}\n`;
  }

  const api = { validatePack, newSession, progress, hasObservations, applyDecision, addRetest, validateSession,
    importJson, exportJson, summaryMarkdown };
  root.STI_UAT_CORE = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
