"use strict";

(function () {
  const pack = window.STI_UAT_PACK;
  const core = window.STI_UAT_CORE;
  const storageKey = "sti-m9-uat-schema1-pack1.0.0";
  const $ = (id) => document.getElementById(id);
  const metadataLabels = {
    authorization_ref: "Owner authorization reference", tested_sha: "Tested application full SHA",
    os: "Windows version", python: "Python version", qt: "Qt version",
    platform: "Actual platform", scale: "Windows display scale", text_size: "Windows text size",
    window_width: "Window width", narrator: "Narrator setting", high_contrast: "High contrast setting",
    operator_role: "Non-identifying operator role",
  };
  const decisionLabels = {
    status: "Decision", observed_action: "Observed action", observed_outcome: "Observed outcome",
    rationale: "Rationale", na_reason: "Actual N/A applicability reason (unavailable setup stays NOT RUN)",
    severity: "FAIL severity", blocking_status: "FAIL blocking status (owner disposition may remain undecided)",
    note: "Note", defect_id: "Defect ID (DEF-...) for FAIL",
    evidence_ref: "Opaque evidence reference (EVID-...), no paths or URLs",
  };
  let session = core.newSession(pack);
  let page = 0;
  const dirtyForms = new Set();
  document.addEventListener("input", (event) => {
    const form = event.target.closest("form");
    if (form) dirtyForms.add(form);
  });
  document.addEventListener("change", (event) => {
    const form = event.target.closest("form");
    if (form) dirtyForms.add(form);
  });
  window.addEventListener("beforeunload", (event) => {
    if (dirtyForms.size) { event.preventDefault(); event.returnValue = ""; }
  });

  function replacementPrompt(text) {
    return window.confirm(`${dirtyForms.size ? "There are unsaved form edits that will be discarded. " : ""}${text}`);
  }

  function message(id, value, error = false) {
    const target = $(id);
    target.textContent = value;
    target.classList.toggle("error", error);
  }

  function persist() {
    try {
      localStorage.setItem(storageKey, core.exportJson(pack, session));
    } catch {
      message("transfer-message", "Local draft could not be saved. Export JSON now.", true);
    }
  }

  function inputLabel(name, label, value, options = {}) {
    const wrapper = document.createElement("label");
    wrapper.textContent = label;
    const control = options.values ? document.createElement("select") :
      (options.multiline ? document.createElement("textarea") : document.createElement("input"));
    control.name = name;
    if (options.values) {
      for (const optionValue of options.values) {
        const option = document.createElement("option");
        option.value = optionValue;
        option.textContent = optionValue;
        control.append(option);
      }
    } else {
      control.maxLength = options.maxLength || 500;
      control.autocomplete = "off";
      if (options.multiline) control.rows = 2;
    }
    control.value = value;
    wrapper.append(control);
    return wrapper;
  }

  function renderMetadata() {
    const fields = $("metadata-fields");
    fields.replaceChildren();
    for (const [name, label] of Object.entries(metadataLabels)) {
      const value = name === "authorization_ref" ? session.authorization_ref : session.environment[name];
      fields.append(inputLabel(name, label, value, { maxLength: 120 }));
    }
  }

  function definitionRow(dl, term, value) {
    const dt = document.createElement("dt");
    dt.textContent = term;
    const dd = document.createElement("dd");
    dd.textContent = value;
    dl.append(dt, dd);
  }

  function renderSteps() {
    const scenario = pack.scenarios[page];
    $("scenario-heading").textContent = `${scenario.id}: ${scenario.title}`;
    $("scenario-position").textContent = `Scenario ${page + 1} of ${pack.scenarios.length}`;
    $("scenario-select").value = String(page);
    $("previous").disabled = page === 0;
    $("next").disabled = page === pack.scenarios.length - 1;
    const container = $("steps");
    container.replaceChildren();
    for (const step of scenario.steps) {
      const result = session.results.find((entry) => entry.step_id === step.id);
      const article = document.createElement("article");
      article.className = "step";
      const heading = document.createElement("h3");
      heading.id = `heading-${step.id}`;
      heading.textContent = step.id;
      const dl = document.createElement("dl");
      definitionRow(dl, "Fixture", `${step.fixture_id}: ${pack.fixtures[step.fixture_id]}`);
      definitionRow(dl, "Precondition", step.precondition);
      definitionRow(dl, "Action", step.action);
      definitionRow(dl, "Expected", step.expected);
      definitionRow(dl, "Evidence needed", step.evidence);
      const form = document.createElement("form");
      form.setAttribute("aria-labelledby", heading.id);
      form.dataset.stepId = step.id;
      for (const [name, label] of Object.entries(decisionLabels)) {
        form.append(inputLabel(name, label, result[name], {
          values: name === "status" ? ["NOT RUN", "PASS", "FAIL", "N/A"] : undefined,
          ...(name === "severity" ? { values: ["", "CRITICAL", "HIGH", "MEDIUM", "LOW"] } : {}),
          ...(name === "blocking_status" ? { values: ["", "BLOCKING", "NON_BLOCKING", "UNDECIDED"] } : {}),
          multiline: ["observed_action", "observed_outcome", "rationale", "na_reason", "note"].includes(name),
          maxLength: name === "note" ? 2000 : 500,
        }));
      }
      const save = document.createElement("button");
      save.type = "submit";
      save.textContent = `Save ${step.id}`;
      const status = document.createElement("p");
      status.id = `message-${step.id}`;
      status.setAttribute("role", "status");
      status.setAttribute("aria-live", "polite");
      status.className = "error";
      status.tabIndex = -1;
      form.append(save, status);
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        const values = Object.fromEntries(new FormData(form));
        if (values.status !== "FAIL") {
          values.severity = "";
          values.blocking_status = "";
          values.defect_id = "";
        }
        try {
          const candidate = core.applyDecision(pack, session, step.id, values);
          core.validateSession(pack, candidate);
          session = candidate;
          dirtyForms.delete(form);
          persist();
          renderProgress();
          renderRetests();
          status.textContent = `Saved ${values.status}.`;
        } catch (error) {
          status.textContent = error.message;
          status.focus();
        }
      });
      article.append(heading, dl, form);
      if (result.history.length) {
        const history = document.createElement("p");
        history.textContent = `${result.history.length} earlier decision(s) retained in JSON.`;
        article.append(history);
      }
      container.append(article);
    }
  }

  function renderProgress() {
    const counts = core.progress(pack, session);
    $("progress").textContent = `Recorded ${counts.recorded} of ${counts.total}; PASS ${counts.pass}; FAIL ${counts.fail}; N/A ${counts.na}; NOT RUN ${counts.not_run}.`;
  }

  function renderRetests() {
    const selector = $("retest-step");
    selector.replaceChildren();
    const prompt = document.createElement("option");
    prompt.value = "";
    prompt.textContent = "Select an observed FAIL";
    selector.append(prompt);
    for (const result of session.results) {
      const failures = [result, ...result.history].filter((item) => item.status === "FAIL");
      for (const defectId of new Set(failures.map((item) => item.defect_id))) {
        const option = document.createElement("option");
        option.value = result.step_id;
        option.textContent = `${result.step_id} (${defectId})`;
        option.dataset.defectId = defectId;
        selector.append(option);
      }
    }
    const list = $("retest-list");
    list.replaceChildren();
    for (const retest of session.retests) {
      const li = document.createElement("li");
      li.textContent = `${retest.step_id}: ${retest.defect_id}, ${retest.outcome}, ${retest.tested_at}, fix ${retest.fix_sha}. ${retest.note}`;
      list.append(li);
    }
  }

  function render() {
    renderMetadata();
    renderSteps();
    renderProgress();
    renderRetests();
  }

  function download(name, contents, type) {
    const url = URL.createObjectURL(new Blob([contents], { type }));
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function changePage(index) {
    const edited = [...dirtyForms].filter((form) => form.dataset.stepId);
    if (edited.length && !window.confirm("Discard unsaved step edits and change scenario?")) {
      $("scenario-select").value = String(page);
      return;
    }
    edited.forEach((form) => dirtyForms.delete(form));
    page = index;
    renderSteps();
    $("scenario-heading").focus();
  }

  core.validatePack(pack);
  for (let index = 0; index < pack.scenarios.length; index++) {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = `${pack.scenarios[index].id}: ${pack.scenarios[index].title}`;
    $("scenario-select").append(option);
  }
  try {
    const draft = localStorage.getItem(storageKey);
    if (draft) {
      session = core.importJson(pack, draft);
      message("transfer-message", "Validated local draft restored. Export JSON for durable evidence.");
    }
  } catch (error) {
    message("transfer-message", `Local draft was rejected: ${error.message}. No decisions were loaded.`, true);
  }
  render();
  $("previous").addEventListener("click", () => changePage(page - 1));
  $("next").addEventListener("click", () => changePage(page + 1));
  $("scenario-select").addEventListener("change", (event) => changePage(Number(event.target.value)));
  $("metadata-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const fields = Object.fromEntries(new FormData(event.target));
    const updated = JSON.parse(JSON.stringify(session));
    updated.authorization_ref = fields.authorization_ref.trim();
    for (const name of Object.keys(updated.environment)) updated.environment[name] = fields[name].trim();
    updated.updated_at = new Date().toISOString();
    try {
      if (core.hasObservations(session)) {
        if (updated.authorization_ref !== session.authorization_ref ||
            Object.keys(updated.environment).some((name) =>
              updated.environment[name] !== session.environment[name])) {
          throw new Error("Session provenance is locked after the first observed decision. Export this session and start a new one for another application SHA or environment.");
        }
      }
      core.validateSession(pack, updated);
      session = updated;
      dirtyForms.delete(event.target);
      persist();
      message("metadata-message", "Session metadata saved.");
    } catch (error) { message("metadata-message", error.message, true); }
  });
  $("export-json").addEventListener("click", () => {
    if (dirtyForms.size && !window.confirm("Export saved evidence only? Unsaved form edits are not included and remain on this page.")) return;
    download("sti-m9-uat-session.json", core.exportJson(pack, session), "application/json");
    message("transfer-message", "JSON export prepared locally. Review privacy before sharing.");
  });
  $("export-summary").addEventListener("click", () => {
    if (dirtyForms.size && !window.confirm("Export saved evidence only? Unsaved form edits are not included and remain on this page.")) return;
    download("sti-m9-uat-summary.md", core.summaryMarkdown(pack, session), "text/markdown");
    message("transfer-message", "Markdown summary prepared locally. Review privacy before sharing.");
  });
  $("new-session").addEventListener("click", () => {
    if (!replacementPrompt("Start a new NOT RUN session? Export the current draft first; this replaces its local copy.")) return;
    dirtyForms.clear();
    session = core.newSession(pack);
    page = 0;
    persist();
    render();
    message("transfer-message", "New session started with every step NOT RUN. Previous local draft was replaced.");
  });
  $("import-file").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      if (file.size > 1024 * 1024) throw new Error("Import exceeds 1 MiB.");
      const candidate = core.importJson(pack, await file.text());
      if (!replacementPrompt("Replace the current local draft with this validated JSON session? Export the current draft first if needed.")) {
        message("transfer-message", "Import cancelled; current draft retained.");
        return;
      }
      session = candidate;
      dirtyForms.clear();
      page = 0;
      persist();
      render();
      message("transfer-message", "Validated session restored. Progress recomputed from steps.");
    } catch (error) {
      message("transfer-message", `Import rejected: ${error.message}. Current draft retained.`, true);
    } finally { event.target.value = ""; }
  });
  $("retest-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.target));
    const selected = $("retest-step").selectedOptions[0];
    if (selected && selected.dataset.defectId) values.defect_id = selected.dataset.defectId;
    values.tested_at = new Date().toISOString();
    try {
      session = core.addRetest(pack, session, values);
      dirtyForms.delete(event.target);
      persist();
      renderRetests();
      event.target.reset();
      message("retest-message", "Linked retest saved; original FAIL retained.");
    } catch (error) { message("retest-message", error.message, true); }
  });
})();
