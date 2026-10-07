# M5.1 — Model Provisioning UI/UX Design: Human Gate brief

**Status: M5.1 Human Gate PASS (2026-10-07).** The owner approved both
decisions, H1 and H2 (section 8). They are now binding for M5.2.

This is **throwaway design evidence** on the sidecar branch
`prototype/m5-1-model-provisioning-uiux`, branched from `main` `36440dd`.

- It must **not be merged into `main`** or copied into production.
- It contains no production code, changes no backend behaviour, and changes
  nothing in the M5.0 contract on `main`.

**Next step:** a separate governance closeout on `main` records this gate.
That closeout includes the contract amendment H2 requires, described in
section 8. After it, **M5.2** (implementation of this design) is the next
development step. M5.2 has not started.

**Binding inputs:**

- [`docs/MODEL_PROVISIONING.md`](../../docs/MODEL_PROVISIONING.md), the M5.0
  contract. This is product truth.
- [`docs/V2_UI_IA_DECISION.md`](../../docs/V2_UI_IA_DECISION.md) (U1–U4).
- The approved Round 3 exploration on `prototype/v2-ui-ia-exploration`
  (`prototypes/v2-ui-ia/round3/`).

## 1. How to review

1. **Open the prototype.** Open
   [`model-provisioning-prototype.html`](model-provisioning-prototype.html) in
   a browser. The dark bar at the top belongs to the prototype, not the
   product:
   - **Scenario buttons:** 1 First run, 2 Downloading, 3 Stopped → resume,
     4 Later, 5 Offline folder, 6 Silent damage → Verify, 7 Durable damage +
     restart, 8 Different version, 9 Ready, 10 Damage found mid-session
     (H2).
   - **Fault for the next operation:**
     - a connection drop at 40% of a weights file;
     - the server refusing the file;
     - a checksum failure;
     - the disk filling up;
     - another operation already running;
     - Verify being unable to read a file.
   - **Restart app:** keeps the simulated disk and resets the session. Use it
     to check what survives a restart.
   - **Speed:** 1× or 4×.
2. **Or read the screenshots.** [`shots/`](shots/) holds 29 captures at
   1400×900. Each one is a deterministic state, and `?shot=<name>` reproduces
   it.

| Shot | What to look at |
| --- | --- |
| `01_first-run` | Launch with nothing installed: three choices (Download, Use a models folder, Later), the size before starting, and the pinned versions and licences |
| `02_downloading` | Progress at three levels (file, model, all), the current file, Stop, the other model "Queued", and "Continue while this runs" |
| `03_stopped` | After Stop: the partial file is kept and its size is shown. **Download** resumes it (the same action, no paused state). **Discard partial download** is offered |
| `04_later-blocked` | After Later: Analyze one text is blocked with the contract message, the models that aren't ready, and one route to fix it |
| `05_projects-not-ready` | Projects stay fully usable. A quiet notice explains why analysis is off |
| `06_new-project-blocked` | CSV validation and project creation work without models; only analysing is blocked |
| `07_folder-pick` … `10_folder-unreadable` | Offline path: pick a folder, then a read-only inspection showing per-model findings (`found`, `incomplete`, `mismatched`, `wrong_revision`, `not_found`), unsupported folders, and `source_unreadable` |
| `11_importing` | Import with copying-and-checking progress and Stop |
| `12_import-checksum` | Import stopped by `checksum_mismatch`: the earlier model stays installed and the folder is untouched |
| `13_download-network-failed` | `network_unavailable`: the partial file is kept, and "Download again · resumes" |
| `14_storage-failed` | `storage_failed`, with Try again and Open models folder |
| `15_busy` | `provisioning_in_progress` |
| `16_load-failed` | Same-size damage that the quick status can't see. Loading fails, and the UI offers **Verify files** (contract §4) |
| `17_verifying` | Explicit Verify: all three counts advance and there is no Stop (Verify can't be cancelled) |
| `18_verify-found` | A durable corruption finding, with Download replacement, Use a models folder and Verify again |
| `19_corrupt-relaunch` | After a restart the finding persists. The launch window says why analysis is unavailable |
| `20_corrupt-blocked` | Analysis blocked by the durable finding |
| `21_wrong-revision` | A different version was found. It is never used and left alone; download the approved version |
| `22_ready` · `23_models-ready` · `24_models-details` | Steady state: the sidebar reads "Models ready", the Models window lets you manage the models, and details show provenance (full id, revision, licence, files) |
| `25_discard` | Confirming Discard partial download |
| `26_session-verify-found` | **H2:** analysis had already run this session, then Verify confirms damage. The result says analysis is now off for the rest of this session, and the sidebar reads "Analysis off until restart" |
| `27_session-blocked` | **H2:** Analyze one text is disabled for the rest of the session, with "Open models…" as the only route |
| `28_session-repaired` | **H2:** after a successful repair download, analysis **stays off** in this session. The panel and the sidebar ("Analysis off until restart" / "models repaired · restart to analyse") say so; the earlier result stays visible, as decision 11 states |
| `29_session-repaired-models` | **H2:** the Models window after the repair. Both models are ready, but the header chip reads "Analysis off until restart · models ready" and the result says to restart |

## 2. The design in one paragraph

Provisioning has four surfaces, all in the Round 3 visual language: warm paper,
serif headlines, mono provenance, and status chips that combine an icon with a
word.

1. **The launch "Set up models" window.** This is the Round 3 separate setup
   window. It appears at start whenever overall readiness is not ready, and
   its headline adapts to the worst state.
2. **The persistent Models status at the foot of the sidebar.** This is where
   Round 3 and the contract put it. It is a button showing the state, a short
   line, and a meter while something is running.
3. **The Models window.** It opens from that status, and from every "Set up
   models…" link. This is the post-setup management entry point. It has the
   same model cards as the launch window, plus Verify, Open models folder,
   and details and provenance.
4. **"Use a models folder", a dialog in two steps:** pick a folder, then the
   read-only findings and Import.

Analysis surfaces (Analyze one text, project analysis) show an inline,
non-modal blocked panel and disable only the Analyze action. Everything else
in the app stays usable.

There are two reasons analysis can be blocked, with separate panels:

- **The models are not ready** (`models_not_ready`). This panel offers "Set
  up models…".
- **H2.** Verify confirmed damage after analysis had already loaded in this
  session, so analysis is off until the app restarts. Every surface says so
  from one shared text: the analysis pages, the Projects notice, the Models
  window chip and result, the sidebar status, and the screen-reader
  announcement.

## 3. Contract mapping

### Readiness states (§4)

| State | Chip (icon + word) | Model card sentence | Card actions (exactly the §4 list) |
| --- | --- | --- | --- |
| `ready` | ✓ Ready | All files installed and checksum-verified when installed | None on the card. Window level: Verify files, Open models folder |
| `not_installed` | dashed ○ Not installed | Not downloaded yet, with size | Download this model · size. Window level: Use a models folder |
| `incomplete` | ◆! Incomplete | Interrupted: X kept, Y left; **or** N of M files missing | Download · resume, Y left (or Download missing files). Discard partial download only when `resumable_bytes > 0`. Use a models folder |
| `corrupt` | ✕ Damaged | Wrong size; **or** a Verify finding that is "remembered, also after restarting, until replaced or verified again" | Download replacement · N files, size. Verify again (only for a Verify finding). Use a models folder |
| `wrong_revision` | ◆! Different version | Shows the other version's short hash; it is never used and left alone; also the approved version | Download approved version · size. Use a models folder |

- **Other revisions beside a ready model:** the card says "Also found: version
  d616e2b — never used, left alone" (`other_revisions`).
- **Problem files:** listed in mono for `incomplete` and `corrupt` only.
  For `not_installed` and `wrong_revision` every file would be listed, which
  is noise.

### Actions (§10): only these, nothing added

| Contract action | Where it lives |
| --- | --- |
| Show model status | Sidebar foot (always); launch window; Models window |
| Download (all non-ready, or one model) | Launch-window primary; Models-window header; per-model card button. The label always carries the size, or "resume, X left" |
| Stop / cancel a download or import | Stop in the progress panel. The note under it says what is kept |
| Resume | The same Download action (labelled "Download · resume, X left"). There is **no paused state** |
| Discard partial download | Card and stopped-result buttons, with a confirmation dialog that states the size (`25_discard`) |
| Use a models folder: inspect | The folder dialog's "Check this folder". It states "read-only check, nothing was copied" |
| Use a models folder: import | "Import both models" / "Import emotion model", for `found` models only |
| Verify files | Models-window header, shown only when some model is `ready` or `corrupt`; "Verify again" on damaged cards; "Verify files" after `model_load_failed` |
| Open models folder | Models-window header; `storage_failed` recovery. The note says the app manages this folder: Download, Import, Verify and Discard can add, replace or tidy up files in it, and changing files by hand can make a model not ready |
| Model details and provenance | The "Details and provenance" disclosure on each card |

### Flows

- **Explicit download only (§5.4):** nothing starts until the user presses a
  button whose label states the size.
- **Progress (§6):**
  - Every byte figure and the "All selected" total come from the manifest.
  - Re-checking a kept or just-downloaded file moves only "This file", so
    model and overall bars never move backwards.
  - During Verify, every bar advances.
  - The launch window shows the model and overall bars only. The Models
    window adds the file bar.
- **Continue while it runs:** the operation keeps going after the launch
  window closes, and its progress moves to the sidebar foot. A user can
  browse projects meanwhile.
- **One operation at a time (§6, §8):** while anything runs, the other
  provisioning buttons are disabled, with a visible sentence explaining why.
  The `provisioning_in_progress` result is still designed (`15_busy`) for the
  cross-window or cross-process cases the UI cannot prevent.
- **Import (§7):**
  - Only `found` models are importable.
  - The copy is checked while copying.
  - A checksum failure stops the import. Models imported earlier stay, later
    ones are not attempted, and the source folder is untouched; all of this is
    stated in the result.
  - Stopping an import keeps nothing partial.
- **Verify (§4, §10):**
  - Not cancellable; the panel says so instead of showing Stop.
  - A finding is shown as durable, including after a restart (`19`, `20`).
  - Repair is Download replacement, a models folder, or Verify again.
  - The quick status can't see same-size damage, so after `model_load_failed`
    the error offers Verify (`16`).
  - **H2, binding:** if analysis had already loaded in this session and an
    explicit Verify confirms damage, analysis is blocked at once for the rest
    of the session (`26`–`28`).
    - A successful repair by download, import or a matching Verify makes the
      models `ready`, but it does **not** re-enable analysis in this process.
    - The user restarts the app. On start, readiness is checked again and the
      verified models are loaded fresh.
    - Nothing is reloaded or unloaded in-process.

### Error codes (§8)

The UI writes a short title and recovery actions for each code, and shows the
backend's **fixed message verbatim** as the body, followed by the code in mono.

| Code | Title | Actions |
| --- | --- | --- |
| `network_unavailable` | Connection lost | Download again · resumes; Use a models folder |
| `download_rejected` | The download was refused | Download again; Use a models folder |
| `checksum_mismatch` | A file failed its checksum and was discarded | Download again (or "Choose a different folder" after an import); Use a models folder |
| `storage_failed` | The models folder could not be read or written (Verify: "Verify could not read a model file", noting that nothing was recorded for that file) | Try again; Open models folder |
| `source_unreadable` | Couldn't read that folder | Choose another folder |
| `provisioning_in_progress` | Another model operation is running | OK (wait) |
| `models_not_ready` | Analysis is unavailable | Set up models… (also lists the non-ready models and their states) |
| H2 session block (UI rule, no backend code) | Analysis is off until you restart the app | Open models…, for repair. The text says repairing does not turn analysis back on in this session, and to close and reopen the app |
| `model_load_failed` (existing) | The model files could not be loaded | Verify files; Open models |

## 4. Design decisions and assumptions

1. **The launch window appears on every start while models are not ready.**
   Contract §5 applies to every start, not only the first. Its headline
   changes with the worst state: interrupted, missing files, damaged, or
   different version.
2. **No new sidebar entry.** The management entry point is the existing
   Models status at the sidebar foot (U1 fixes the IA and puts model status
   there), plus "Set up models…" links wherever analysis is blocked. No
   Settings page or keyboard shortcut scheme is added.
3. **The Models window is a modal sub-window.** Closing it never stops an
   operation.
4. **Sizes use binary units with Windows labels** (479.1 MB, 0.94 GB),
   matching Explorer. The contract's 1,004,464,932 bytes appears as "0.94 GB".
5. **No speed or time-remaining estimate.** Progress events carry bytes only.
   An estimate would be invented precision on a variable network.
6. **The download button labels carry the size.** That satisfies "shows the
   size before starting" without an extra confirmation dialog. Destructive
   Discard is the only action that confirms.
7. **Analysis blocking is visible, not hidden.** Analyze is disabled and
   `aria-describedby` points to an always-visible reason panel, so the reason
   never depends on hovering.
8. **Error copy is chosen by code.** The backend's fixed messages are shown
   unchanged, and the UI adds a title, an extra sentence where the contract's
   "state afterwards" column needs it, and the actions.
   - **Follow-up for M5.2:** `provisioning_in_progress`'s fixed text says
     "download or import" although Verify is also exclusive.
   - **Follow-up for M5.2:** `model_load_failed`'s V1 text mentions "offline
     mode". The desktop shows its own title and the Verify route instead.
   - Neither follow-up requires a contract change.
9. **Steady state is quiet.** A ready app shows only "✓ Models ready" in the
   sidebar foot. No banners appear unless something needs attention.
10. **Project screens are not redesigned.** Projects, Analyze one text and New
    project appear only as the context in which provisioning shows up. They
    keep Round 3's layout, and they drop Decision Practice (U4).
11. **The H2 session block is one flag for the whole session.** It is set only
    when Verify confirms damage after the analysis service has been built. It
    is checked by the single analysis gate that every analysis surface uses.
    Nothing in the session clears it; a restart is the only way out.
    - The UI offers no "restart now" button. That would be a new app-level
      action, so the copy tells the user to close and reopen the app.
    - A Direct result produced before the finding stays on screen as it was.
      It was computed from models loaded before the damage was confirmed.
12. **Wording for the models folder is conservative.** The UI no longer claims
    the app never deletes files there. It says the folder is managed by the
    app through Download, Import, Verify and Discard, and lists no internal
    file types.

## 5. Accessibility, designed in (not audited)

- **Keyboard:** every action is a real button or control, and dialogs and the
  Models window close with Esc.
- **Focus:**
  - Focus goes to the dialog heading on open and returns to the invoker on
    close.
  - Progress re-renders keep focus on the same control (verified: Stop keeps
    focus during a download).
  - Focus rings are visible (`:focus-visible`).
- **Status without colour:** every state chip pairs a distinct icon shape with
  a word: ✓, dashed ○, diamond !, square ✕, or ring ↓.
- **Screen readers:**
  - The sidebar status button has one combined spoken label (for example,
    "Emotion model damaged. 1 of 2 models ready. Analysis unavailable. Open
    models.").
  - Progress bars are `role="progressbar"` with text values.
  - A polite live region announces each 10% step and phase changes.
  - Errors are announced assertively.
- **Readable text:** progress and errors are written out ("414.4 MB of 957.9 MB",
  the fixed message, the code), never shown by the bar alone.
- **Reduced motion:** there are no animations; under
  `prefers-reduced-motion`, the striped "partial" fill becomes flat.
- **Not done here:** the real Qt accessibility audit (UI Automation names and
  roles, high-contrast themes, screen-reader runs) remains an implementation
  and release gate, as the UI/IA decision says.

## 6. Explicitly not included

- Model removal or relocation, provider or model switching, or choosing an
  alternative model or revision.
- Silent or background download, automatic repair, and a separate paused
  state.
- Proxy or bandwidth settings, accounts, cloud, sync, or update checks.
- Any change to M5.0 semantics.
- Language detection (V2-3), batch progress UI (V2-4), and Decision Practice.

## 7. Round 3 differences, resolved by the contract (not gate questions)

- **Pause:** Round 3's first-run screen had "Pause" and "Resume". The contract
  has no paused state (U3 left pause and resume non-binding; M5.0 bound it as
  Stop plus Download again). The design uses Stop and Download · resume.
- **Folder use:** Round 3's folder dialog said "Use these models", in place.
  The contract only copies into the managed folder after inspection. The
  design uses Check this folder, then Import.
- **Download granularity:** Round 3 showed one combined download. The design
  adds per-model Download buttons, because §10 allows "a single model".

None of these contradicts U1. The IA, the feature boundary and the
AI-versus-human separation are untouched.

## 8. Owner decisions: Human Gate PASS (2026-10-07)

Both decisions below are owner-approved and binding for M5.2.

### H1 — APPROVED: this design is the M5.2 implementation baseline

The following are binding:

- the surfaces, readiness states and action set;
- the recovery routes and the sidebar Models entry;
- the first-run flow and the offline inspect/import flow;
- the error and recovery structure, and the copy hierarchy.

M5.2 may polish the visuals at the implementation level, but must not
reinvent the product interaction model.

### H2 — APPROVED: a confirmed corruption mid-session blocks analysis for the rest of the session

If the analysis service has already loaded and a later explicit Verify
confirms corruption, all further analysis is blocked immediately for the
remainder of that app session.

- Repairing or replacing the files on disk does not re-enable analysis in the
  current process.
- The user must restart the app, pass readiness again, and load the verified
  models fresh.
- Providers are never silently reloaded in-process, and no unload or rebuild
  mechanism is introduced.
- The earlier design text ("this session keeps using the loaded models until
  the next start") is withdrawn.

**Consequence for `main`:** H2 is stricter than M5.0 contract §9 as merged,
which says a later Verify finding "takes effect for analysis on the next
start". The separate governance closeout on `main` should amend §9 to H2
before M5.2 implements it. This sidecar does not change `main`.

## 9. Files

- [`model-provisioning-prototype.html`](model-provisioning-prototype.html):
  the interactive prototype. It is self-contained apart from web fonts for
  the mock; a shipped build bundles OFL fonts after the licence check noted in
  the UI/IA decision.
- [`shots/`](shots/): 29 deterministic state captures, and only these.
  Use `?shot=<name>` to reproduce one. The duplicate files named
  `shots${n}_*.png` that were committed by mistake in the prototype root have
  been removed.
- This brief.

**Closeout regeneration (after H1 and H2):** 19 existing captures were
regenerated and 4 added, for 23 in total.

- **Regenerated:** `01`–`03`, `07`–`15`, `17`–`19`, `21`, and `23`–`25`.
  These are all the captures that show the setup or Models window, where the
  models-folder wording changed.
- **Added:** the H2 captures `26`–`29`.

`04`–`06`, `16`, `20` and `22` are unchanged.

**Verification performed:**

- All 28 shot states render with no script errors in headless Edge.
- These live click-through runs passed in the browser pane:
  - Download, Stop (partial kept), resume to ready, Start, Analyze, Verify;
  - an offline import from a damaged copy that stops with `checksum_mismatch`
    while the earlier model stays installed;
  - silent damage leading to `model_load_failed`, then Verify, then a durable
    finding across a restart, then repair by download;
  - focus retained on Stop during progress updates;
  - the H2 path: analysis loaded, then Verify finds damage and analysis is
    blocked, then a repair download makes the models ready while Analyze
    stays disabled and the sidebar reads "Analysis off until restart" with
    "models repaired · restart to analyse", then a restart and analysis works
    again;
  - the new Open models folder wording.
