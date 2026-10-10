"use strict";
// Recorder infrastructure smoke only. Use an isolated temporary Chrome profile.
const assert = require("node:assert/strict");

(async () => {
  const pages = await (await fetch("http://127.0.0.1:9223/json/list")).json();
  const page = pages.find((item) => item.type === "page" && item.url === "http://127.0.0.1:8765/");
  assert.ok(page, "local companion page exists");
  const socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let id = 0;
  const pending = new Map();
  socket.onmessage = (event) => {
    const packet = JSON.parse(event.data);
    if (packet.id && pending.has(packet.id)) {
      pending.get(packet.id)(packet);
      pending.delete(packet.id);
    }
  };
  const send = (method, params = {}) => new Promise((resolve) => {
    const callId = ++id;
    pending.set(callId, resolve);
    socket.send(JSON.stringify({ id: callId, method, params }));
  });
  const evaluate = async (expression) => {
    const packet = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    if (packet.result.exceptionDetails) throw new Error(packet.result.exceptionDetails.text);
    return packet.result.result.value;
  };
  await send("Page.navigate", { url: "http://127.0.0.1:8765/" });
  await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }] });
  await new Promise((resolve) => setTimeout(resolve, 700));
  await evaluate("localStorage.clear()");
  await send("Page.reload", { ignoreCache: true });
  await new Promise((resolve) => setTimeout(resolve, 700));
  assert.match(await evaluate("document.body.innerText"), /Recorded 0 of 49/);
  assert.equal(await evaluate("document.querySelectorAll('select#scenario-select option').length"), 24);
  assert.equal(await evaluate("document.querySelectorAll('.step').length"), 2);
  await evaluate("document.getElementById('next').click()");
  assert.match(await evaluate("document.getElementById('scenario-heading').textContent"), /UAT-MODEL-02/);
  await evaluate("document.getElementById('previous').click()");
  assert.match(await evaluate("document.getElementById('scenario-heading').textContent"), /UAT-MODEL-01/);
  await evaluate(`(() => { const form=document.getElementById('metadata-form'); const fields={authorization_ref:'OWNER-AUTH-SYNTH',tested_sha:'${"a".repeat(40)}',os:'Synthetic Windows',python:'3.12',qt:'6.11',platform:'windows',scale:'100%',text_size:'100%',window_width:'900',narrator:'off',high_contrast:'off',operator_role:'authorized tester'}; for (const [key,value] of Object.entries(fields)) form.elements.namedItem(key).value=value; form.requestSubmit(); })()`);
  assert.match(await evaluate("document.getElementById('metadata-message').textContent"), /saved/i);
  await evaluate("document.querySelector('.step form').elements.namedItem('status').value='FAIL'; document.querySelector('.step form').requestSubmit()");
  assert.match(await evaluate("document.getElementById('message-UAT-MODEL-01-S01').textContent"), /Observed/i);
  assert.match(await evaluate("document.getElementById('progress').textContent"), /Recorded 0 of 49/);
  await evaluate("(() => { const form=document.querySelector('.step form'); form.elements.namedItem('observed_action').value='Opened setup'; form.elements.namedItem('observed_outcome').value='Synthetic button absent'; form.elements.namedItem('defect_id').value='DEF-001'; form.elements.namedItem('severity').value='HIGH'; form.elements.namedItem('blocking_status').value='BLOCKING'; form.elements.namedItem('rationale').value='Setup is blocked'; form.requestSubmit(); })()");
  assert.match(await evaluate("document.getElementById('progress').textContent"), /FAIL 1; N\/A 0; NOT RUN 48/);
  await evaluate("(() => { const field=document.querySelector('.step form [name=note]'); field.value='Unsaved synthetic note'; field.dispatchEvent(new Event('input', {bubbles:true})); window.confirm=()=>false; document.getElementById('next').click(); })()");
  assert.match(await evaluate("document.getElementById('scenario-heading').textContent"), /UAT-MODEL-01/);
  assert.equal(await evaluate("document.querySelector('.step form [name=note]').value"), "Unsaved synthetic note");
  await evaluate("document.getElementById('new-session').click()");
  assert.equal(await evaluate("document.querySelector('.step form [name=note]').value"), "Unsaved synthetic note");
  await evaluate("(async () => { const json=STI_UAT_CORE.exportJson(STI_UAT_PACK, STI_UAT_CORE.newSession(STI_UAT_PACK)); const dt=new DataTransfer(); dt.items.add(new File([json], 'cancelled.json')); const input=document.getElementById('import-file'); input.files=dt.files; input.dispatchEvent(new Event('change')); await new Promise(r=>setTimeout(r,100)); })()");
  assert.match(await evaluate("document.getElementById('transfer-message').textContent"), /cancelled/i);
  assert.equal(await evaluate("document.querySelector('.step form [name=note]').value"), "Unsaved synthetic note");
  await evaluate("window.confirm=()=>true; document.getElementById('next').click(); document.getElementById('previous').click()");
  assert.notEqual(await evaluate("document.querySelector('.step form [name=note]').value"), "Unsaved synthetic note");
  await evaluate("document.getElementById('metadata-form').elements.namedItem('tested_sha').value='" + "b".repeat(40) + "'; document.getElementById('metadata-form').requestSubmit()");
  assert.match(await evaluate("document.getElementById('metadata-message').textContent"), /locked/i);
  assert.equal(await evaluate("getComputedStyle(document.getElementById('metadata-message')).color"),
    await evaluate("getComputedStyle(document.body).color"));
  assert.equal(await evaluate("document.querySelectorAll('#retest-step option').length"), 2);
  const ax = await send("Accessibility.getFullAXTree");
  assert.ok(ax.result.nodes.some((node) => node.role?.value === "heading" && node.name?.value.includes("UAT-MODEL-01")));
  await send("Page.reload", { ignoreCache: true });
  await new Promise((resolve) => setTimeout(resolve, 700));
  assert.match(await evaluate("document.getElementById('progress').textContent"), /FAIL 1; N\/A 0; NOT RUN 48/);
  assert.match(await evaluate("document.getElementById('transfer-message').textContent"), /restored/i);
  await evaluate("(() => { const field=document.querySelector('.step form [name=note]'); field.value='<img src=x onerror=alert(1)>'; document.querySelector('.step form').requestSubmit(); })()");
  assert.equal(await evaluate("document.querySelector('.step img') === null"), true);
  assert.match(await evaluate("document.getElementById('progress').textContent"), /FAIL 1; N\/A 0; NOT RUN 48/);
  await evaluate("(async () => { const file=new File(['{bad'], 'malformed.json', {type:'application/json'}); const dt=new DataTransfer(); dt.items.add(file); const input=document.getElementById('import-file'); input.files=dt.files; input.dispatchEvent(new Event('change')); await new Promise(r=>setTimeout(r,100)); })()");
  assert.match(await evaluate("document.getElementById('transfer-message').textContent"), /Import rejected/);
  assert.match(await evaluate("document.getElementById('progress').textContent"), /FAIL 1; N\/A 0; NOT RUN 48/);
  await evaluate("(async () => { window.confirm=()=>true; const json=window.STI_UAT_CORE.exportJson(window.STI_UAT_PACK, window.STI_UAT_CORE.newSession(window.STI_UAT_PACK)); const file=new File([json], 'fresh.json', {type:'application/json'}); const dt=new DataTransfer(); dt.items.add(file); const input=document.getElementById('import-file'); input.files=dt.files; input.dispatchEvent(new Event('change')); await new Promise(r=>setTimeout(r,100)); })()");
  assert.match(await evaluate("document.getElementById('progress').textContent"), /Recorded 0 of 49/);
  await send("Emulation.setDeviceMetricsOverride", { width: 375, height: 800, deviceScaleFactor: 1, mobile: true });
  assert.equal(await evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2"), true);
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  require("node:fs").mkdirSync("_local", { recursive: true });
  require("node:fs").writeFileSync("_local/m9-companion-narrow.png", Buffer.from(screenshot.result.data, "base64"));
  await send("Emulation.clearDeviceMetricsOverride");
  console.log("Chrome interaction smoke PASS: 24 pages, validation, progress, draft restore, hostile/valid import, AX tree, hostile note containment, narrow viewport");
  socket.close();
})().catch((error) => { console.error(error); process.exit(1); });
