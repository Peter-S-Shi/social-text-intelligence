# V2 M10 — Core + Optional Components distribution plan

Status: **PLAN — awaiting owner approval of the steps below.** Documentation only.
Nothing is implemented, built, published or merged by this record, and no release
gate changes. The owner's overriding goal is unchanged: a legally distributable
Windows installer, not a source-only portfolio.

Baseline: M10-E2 (PR #61, head `6179aa5`). The draft R2 work in PR #62 is parked
(§2).

## 1. Owner strategy (2026-10-11)

- **Core.** The main installer keeps every essential dependency whose
  redistribution obligations can be met, including the Qt/PySide6 stack under a
  completed LGPL route.
  - Qt is not externalized.
  - The desktop architecture is not redesigned because B1/B6 are still open.
- **Visual C++ runtime: R1.**
  - No Microsoft runtime binary is shipped.
  - A missing prerequisite sends the user to Microsoft's official download. That
    may need administrator help, which the owner accepts.
- **Optional components.**
  - py3langid is the only immediate candidate.
  - Model weights stay on the existing user-authorized provisioning path.
  - A separately downloadable add-on that STI packages or hosts still needs its own
    verified distribution rights; it moves no liability to users.
- **B1, B4 and B6** are finished through narrow, established tasks. No new
  installers are made for essential libraries.

## 2. Component disposition

| Component | Disposition | Open item |
| --- | --- | --- |
| Qt 6.11.2 / PySide6 / shiboken6 (LGPL-3.0) | **Core**: unchanged, replaceable loose binding layer | B1 owner/legal position; B6 E4 rebuild (§4) |
| Official CPython 3.13.16 (PSF) | **Core**: checked file by file | None (B3 closed in M10-E2) |
| PyTorch, transformers, tokenizers, safetensors, huggingface_hub, NumPy and other Python packages | **Core** | B4 notice texts (§4) |
| Intel OpenMP `libiomp5md.dll` / `libiompstubs5md.dll` (inside PyTorch) | **Core**: `torch_cpu.dll` imports it statically, so it cannot be optional | B4: the Intel licence text (§4) |
| Microsoft Visual C++ runtime | **External prerequisite (R1)**: not shipped; the installer stops and links to Microsoft | Clean-machine run of the missing-runtime branch |
| Route R2 (app-local runtime) | **Parked** in draft PR #62; no further work unless a concrete requirement reopens it | — |
| py3langid 0.4.0 (code BSD-3-Clause; bundled model with unverified corpus terms, B5) | **Leaves Core** (§3) | Owner choice between O1 and O2 |
| Sentiment and emotion model weights | **Unchanged**: downloaded only after user authorization; never bundled | — |

Intel OpenMP was checked for this table. The binary is Intel-signed, and its
version resource reads "Copyright (C) 1997, Intel Corporation. All rights
reserved". PyTorch's shipped `llvm-openmp` notice says it covers the macOS
`libomp`, not this Windows binary. So the Intel licence text really is missing.

## 3. py3langid evaluation

**The existing contract already covers absence.** py3langid is an optional extra
in source installs. When it is absent, the detector reports *unavailable*
(`not_assessed` / `detector_unavailable`). The warning headline is "Language check
unavailable"; it warns, never treats a text as supported, and analysis continues
(`docs/LANGUAGE_DETECTION.md`, States). Service, analysis, export and training-snapshot tests already cover this state.

**One real obstacle.** The frozen runtime preflight
`src/social_text_intelligence/desktop/packaging.py` lists `py3langid.langid` as a
required module. So a frozen app without it refuses to start, both in
`gui_main` and in `sti-check --verify-runtime`.

| Option | What ships | Distribution rights | Effort |
| --- | --- | --- | --- |
| **O1 — leave it out of the installer** | Nothing from py3langid | Nothing to clear: B5 closes by removal, as B2 did | Small (§5, S1) |
| **O2 — optional, user-authorized model provisioning** | py3langid code (BSD-3-Clause) only. The model file is fetched from its upstream publisher, pinned by SHA-256, on the user's explicit request, like the model weights | STI neither packages nor hosts the model; it stays on upstream. The corpus question is not answered, only not redistributed by STI | Moderate: a new provisioning entry, an adapter that loads from the models folder, UI and tests. Proposed only as a follow-up after O1 |
| O3 — retrain on accepted corpora (M10-E2 §2.5) | A new model | Needs a legal review of each source | Not now: an open-ended legal task |
| O4 — another detector | A new dependency | Every candidate in the M5.6 spike also embeds corpus-trained data | Not now: same class of question plus a new evaluation |

**Recommendation:**

- Do O1 now. It is the smallest change, keeps the established unavailable-state UX
  and warning contract, and removes B5 from the installer.
- Consider O2 only if the owner wants language detection back in installed builds.
  It would be a separate, approved step.

## 4. Narrow tasks for B1, B4 and B6

- **B1 (owner/legal position, then small engineering).**
  - The bindings are unmodified upstream binaries built by The Qt Company.
  - The delivered `pyside-setup` source equals the `v6.11.2` tag: 4,600 of 4,602
    files are identical, and the other 2 are symlinks stored as file copies.
  - All 121 Qt files are verified against the official SBOMs.
  - Decision needed: accept that tag's source and build scripts as the
    Corresponding Source, and confirm the same-page source route.
  - **Recommendation:** accept. It is the standard practice for unmodified upstream
    binaries, and the heavier alternative (rebuilding the bindings) needs the same
    toolchain as B6.
  - Engineering afterwards: the packet records the decision, and the release page
    hosts the five source archives beside the installer.
- **B4 (engineering, with download approval).**
  - Fetch the licence texts of the 149 crates in the exact tokenizers `Cargo.lock`
    receipt (crates.io, pinned versions) into the packet.
  - Obtain the Intel OpenMP licence that matches the shipped `libiomp5md.dll`
    (build 20260213).
  - PyTorch's static third-party content stays at the upstream-notice level
    recorded in M10-E2.
- **B6 (owner toolchain, then the prepared run).**
  - The owner installs Visual Studio 2022 Build Tools (MSVC v143 14.44) with a
    Windows 11 SDK and accepts its licence.
  - Engineering then runs `tools/m10/e4_modified_qt.ps1` unchanged and records the
    receipt.
  - B6 closes only if the modified-source replacement passes.

## 5. Minimal executable change plan

| Step | Change | Files | Tests and evidence | CI |
| --- | --- | --- | --- | --- |
| **S1 — py3langid out of the installer (O1)** | Drop py3langid from the frozen spec (data, hidden import, metadata; add it to `excludes`). Make the preflight treat the language check as optional: it reports availability instead of failing. Derive B5 only when py3langid is actually in the bundle. Remove its register entry | `src/.../desktop/packaging.py`, `tools/m10/sti_desktop.spec`, `tools/m10/compliance.py`, `distribution/component-register.json`, notices and records | Update the preflight tests (absent py3langid is ready, and its absence is reported). Keep the existing unavailable-state tests. Rebuild the real frozen bundle: py3langid is absent; `--verify-runtime` and `--smoke` exit 0; a frozen analysis shows "Language check unavailable"; the packet derives B1 and B4 only | Yes (code) |
| S2 — B4 notices | Add the crate licence texts and the Intel OpenMP licence to the packet; narrow the B4 derivation to what is still missing | `tools/m10/compliance.py`, `distribution/`, records | Packet test; rebuild | Yes |
| S3 — B6 E4 run | No code change expected | Receipt and records | E4 receipt; frozen checks on the modified bundle | Docs-only: no |
| S4 — B1 closure | Record the owner/legal position; the packet derives B1 from it | `tools/m10/compliance.py`, records | Packet test | Yes |
| S5 — clean-machine matrix (R1) | No code change expected | Evidence | `validate_installer.ps1 -EnvironmentKind DisposableVM`, including the missing-runtime prompt and a real model download and inference. Needs a VM or second PC: this host is Windows 11 Home, without Sandbox or Hyper-V | Docs-only: no |

- **Order:** S1 first, because it needs no owner input. S2 follows download
  approval, S3 the toolchain, S4 the B1 decision, and S5 a VM.
- **Lifecycle records** are updated with each step. Documentation-only commits use
  `[skip ci]`.

## 6. Real functional degradation

1. **Installed app, language check (S1/O1).**
   - Every fresh analysis shows "Language check unavailable".
   - The unsupported-language and undetermined warnings no longer appear.
   - The project summary counts all analysed texts as not confirmed to be in a
     supported language.
   - Exports carry `not_assessed` / `detector_unavailable`.
   - Labels, metrics and analysis are unchanged.
   - Results stored earlier keep their recorded evidence.
   - Source installs with the `language` extra are unaffected.
   - O2 would restore detection after the user opts in.
2. **Installation without the VC++ runtime (R1).** On a machine without the
   Visual C++ 2015–2022 x64 runtime 14.44+, the user must first install
   Microsoft's redistributable, usually with administrator rights. The app itself
   is unaffected.
3. **Nothing else.** Qt, models and analysis behaviour are unchanged.

## 7. Not done by this plan

- No new installers for essential libraries.
- No Qt externalization.
- No further R2 work.
- No new open-ended legal investigation.
- No change to release gates.
- No merge and no publication.
