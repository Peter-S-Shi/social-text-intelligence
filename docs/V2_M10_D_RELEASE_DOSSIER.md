# M10-D — Release Readiness Dossier and Decision Gate

## 1. Authority and Boundaries

This dossier is initiated from the merged `main` baseline at
`80f53c2155dfc8337c2f49032404ea200fabc7d8` (PR #58 merged). It synthesizes
the completed packaging, compliance, installer engineering, and risk records of
Social Text Intelligence V2 into an auditable release readiness decision
matrix.

This milestone is strictly an **evidence synthesis and decision-preparation
gate**. It does not:
- modify product behavior or runtime code;
- reopen settled architecture decisions or add new features;
- waive the Q5 representative-domain evaluation requirement;
- declare legal compliance or clear distribution gates;
- create a formal Release Candidate approval;
- publish installer binaries, wheel distributions, or GitHub Releases.

M9.0 remains a historical owner-approved design; M9.1 is complete on `main` as
infrastructure only. M9.2–M9.4 remain **DEFERRED** by owner direction. The
optional 30-minute owner packaged-app smoke test remains planned **NOT RUN**.
V1's historical version `0.10.0` and its public portfolio delivery status
preserve historical baseline facts only; they do not authorize the release or
distribution of V2. Formal release authorization is reserved for the repository
owner.

---

## 2. Stratified Release-Readiness Matrix

The release readiness of Social Text Intelligence V2 is stratified across six
auditable layers. Engineering completion and development-host observations must
not be conflated with clean-machine validation, legal compliance, or release
authorization.

| Layer | Focus Area | Status | Evidence & Baseline | Concrete Constraints & Unresolved Blockers |
| --- | --- | --- | --- | --- |
| **L1** | **Engineering Completion** | **COMPLETE** | Implementation commits `49f8771` (M10-A), `e6fdd85` (M10-B), `35df292` (M10-C); GitHub CI [38102500170](https://github.com/Peter-S-Shi/social-text-intelligence/actions/runs/38102500170) PASS on Python 3.11/3.12/3.13 and Node | Core tools ([`tools/m10/build.py`](../tools/m10/build.py), [`compliance.py`](../tools/m10/compliance.py), [`installer.py`](../tools/m10/installer.py)) pass all deterministic generator and schema regressions. Full test suite: 1,186 passed / 6 skipped. |
| **L2** | **Development-Host Observations** | **PASS (Host-Only)** | Frozen onedir build `302d9f5` (652 MiB, 4,920 files); material assembly `c93191e` (761 MiB, 5,265 files); installer build `35df292` | Executed on a Windows x64 development machine with ambient development tools. Verified per-user installation, clean uninstall, reparse link refusal, shortcut integrity, and synthetic byte preservation (C01–C06, C08–C12). Does not substitute for an isolated clean OS. |
| **L3** | **Clean-Machine & UI Matrix** | **NOT RUN** | Defined in [M10-C Installer Record](V2_M10_C_WINDOWS_INSTALLER.md) (§5) | C01–C16 matrix on a fresh VM / Windows Sandbox remains **NOT RUN**. Missing-model UI blocking and download-cancel interaction (C07) and alternative `/DIR` refusal (C14) remain **NOT RUN**. |
| **L4** | **Formal Acceptance & Deferred Risks** | **DEFERRED / NOT RUN** | Approved [M9.0 Evidence Contract](V2_M9_EVIDENCE_CONTRACT.md); [M9.1 Infrastructure](V2_M9_EXIT_GATE.md); [M8 Track A Ledger](V2_M8_TRACK_A_LEDGER.md) | M9.2 authentic dual-model evaluation (180 real records, 60 double-blind reference cases) deferred; Q5 requires representative-domain evidence before model capability claims. Formal 49-step Windows UAT and Windows UI Automation accessibility audit NOT RUN. M8 physical low-RAM/cold-start (A5) and sync folder risks remain open. |
| **L5** | **Signing & SmartScreen** | **OPEN / FRICTION RISK** | Unsigned Inno Setup installer; unsigned executables; no Authenticode credentials | Distribution without a commercial Authenticode code-signing certificate presents potential SmartScreen and application-reputation friction on external Windows systems. Code signing does not guarantee avoidance of reputation prompts, and an unsigned portfolio approach was historically accepted at Architecture Gate A6; external distribution readiness remains open. |
| **L6** | **Legal & Distribution Compliance** | **BLOCKED (B1–B6)** | [M10-B Compliance Record](V2_M10_B_DISTRIBUTION_COMPLIANCE.md); generated local inventory `legal/inventory.json` and committed sanitized receipt [`evidence/m10-b/inventory-receipt.json`](evidence/m10-b/inventory-receipt.json) | Six open distribution blockers (B1–B6). Both Qt DLL replacement experiments failed (exit 2). Microsoft VC++ runtime redistribution and CPython custom build rights unverified. Distribution prohibited. |

---

## 3. Detailed Audit of Unresolved Distribution Blockers (B1–B6)

The M10-B compliance audit established structural inventory checks and upstream
source manifests, but confirmed that binary distribution is legally blocked
under open obligations:

1. **B1 — Corresponding Source & Exact Build Recipes (OPEN, blocks distribution)**:
   While upstream tarballs for QtBase, PySide6, and Shiboken6 are collected and
   checksummed, exact PyPI wheel patch sets, compiler flags, and reproducible
   producer recipes for the deployed binaries are unverified. Distributing
   binaries without verified exact corresponding build recipes leaves obligations
   under LGPL v3 §4(d)–(e)—and GNU GPL v3 §6 where incorporated or applicable
   (e.g., regarding conveyance of Corresponding Source or accompanying Installation
   Information)—unresolved, rather than establishing a legally proven violation.
2. **B2 — Software Renderer Attribution (`opengl32sw.dll`) (OPEN, blocks distribution)**:
   The included Mesa/LLVM-based software OpenGL fallback DLL lacks verified
   compiled-content component attribution and upstream build provenance.
3. **B3 — Microsoft Runtime & CPython Distribution Rights (OPEN, blocks distribution)**:
   Redistribution of Microsoft Visual C++ runtime components (`vcruntime140.dll`,
   `msvcp140.dll`) requires adherence to Microsoft Visual Studio licensing terms.
   Additionally, custom packaged CPython 3.12 binaries require formal runtime
   redistribution review.
4. **B4 — Static & Rust Native Dependency SBOM (OPEN, blocks distribution)**:
   Native Rust extensions (including `tokenizers` and cryptography libraries)
   contain statically compiled crates whose individual licenses and notices are
   not fully resolved by top-level package metadata.
5. **B5 — Embedded Language Model Training Data Terms (`py3langid`) (OPEN, blocks distribution)**:
   The bundled Naive Bayes language identification model carries historical training
   data terms that remain unreviewed for public commercial/packaged redistribution.
6. **B6 — Unresolved Qt DLL Replacement Compatibility (OPEN, blocks distribution)**:
   LGPL v3 §4(d)(1) concerns linking with the Library via a suitable shared-library
   mechanism that operates properly with an interface-compatible modified version
   of the Library, while §4(e) separately addresses conditional Installation
   Information obligations. Real Windows replacement experiments substituting Qt
   DLLs from upstream PySide6 6.11.1 and 6.12.0 wheels while retaining the original
   6.11.2 Python bindings and loader resulted in immediate startup failure
   (`exit 2`). These experiments established no compatible replacement in practice,
   but did not demonstrate that compliant replacement is impossible (e.g., through
   rebuilding matching bindings or coherent ABI toolchains). Because compatible
   dynamic replacement remains unverified and unproven, B6 remains an unresolved
   distribution blocker.

---

## 4. Operational Surfaces Analysis

To prevent ambiguity, the application lifecycle defines three distinct
operational surfaces:

```
+-------------------------------------------------------------------------------+
|                       OPERATIONAL SURFACES BREAKDOWN                          |
+------------------------------------+------------------------------------------+
| Surface                            | Permitted Status & Operational Boundary  |
+------------------------------------+------------------------------------------+
| 1. Public Source-Code Portfolio    | SUPPORTED                                |
|    Presentation (GitHub)           | - Open-source repository inspection      |
|                                    | - Architecture & engineering audit       |
|                                    | - Automated tests & developer workflow   |
|                                    | - No compiled binary distribution        |
+------------------------------------+------------------------------------------+
| 2. Non-Distributable Product       | SUPPORTED UNDER CONTROLLED CONDITIONS    |
|    Demonstrations                  | - Author-operated local execution        |
|                                    | - Pre-recorded video walkthroughs        |
|                                    | - Controlled offline demo launcher       |
|                                    | - Synthetic demo datasets only           |
|                                    | - No installer sharing to third parties  |
+------------------------------------+------------------------------------------+
| 3. Downloadable Binary             | PROHIBITED / BLOCKED                     |
|    Distribution (Releases)         | - Pre-compiled installers & wheels       |
|                                    | - Blocked by unresolved B1-B6            |
|                                    | - Unverified clean-machine state         |
|                                    | - Potential SmartScreen friction         |
|                                    | - Q5 required before capability claims   |
+------------------------------------+------------------------------------------+
```

### Surface 1: Public Source-Code Portfolio Presentation
* **Status**: **SUPPORTED**.
* **Scope**: Hosting the Git repository publicly on GitHub as an engineering
  portfolio artifact under the MIT License.
* **Requirements & Guardrails**:
  - Code, documentation, test suites, and CI workflows are fully auditable.
  - No binary artifacts, packaged installers, or model weights are hosted.
  - The repository maintains strict synthetic data boundaries (no private data or
    unverified credentials).
  - Documentation honestly reflects that V2 model capability claims on external
    domains are unproven (preserving Q5).

### Surface 2: Non-Distributable Product Demonstrations
* **Status**: **SUPPORTED UNDER CONTROLLED CONDITIONS**.
* **Scope**: Conducting private, author-operated demonstrations, video screen
  recordings, or running the local demo launcher (`start_demo.bat`).
* **Requirements & Guardrails**:
  - Execution occurs exclusively on author-controlled hardware or private test
    environments.
  - Input data is limited to synthetic demo projects.
  - The compiled installer or onedir bundle is never transmitted, uploaded, or
    provided to third-party evaluators.
  - Audiences are informed that the software operates as an internal engineering
    prototype without formal release clearance.

### Surface 3: Downloadable Binary Distribution
* **Status**: **PROHIBITED / BLOCKED**.
* **Scope**: Publishing pre-compiled installer executables, onedir ZIP archives,
  or wheels on GitHub Releases, websites, or package indexes for general download.
* **Blockers & Limitations**:
  - Blocked by unresolved distribution obligations B1–B6 (Qt dynamic replacement
    compatibility remains unverified following failed cross-version experiments;
    Microsoft runtime redistribution and exact corresponding build receipts remain
    unestablished; these leave obligations open rather than establishing proven
    noncompliance).
  - Technologically unverified on clean machines (C01–C16 NOT RUN on isolated
    environments).
  - Unsigned binaries present potential SmartScreen and application-reputation
    friction on external systems (signing does not guarantee avoidance of reputation
    prompts, though an unsigned portfolio approach was historically accepted at A6).
  - Precedes required domain validation (Q5 requires authentic software feedback
    benchmarks before making model capability claims, though not an independent
    legal distribution requirement).

---

## 5. Prioritized Follow-Up Backlog

Should the repository owner decide to advance V2 toward binary distribution in
future milestones, the required actions are prioritized below:

### Priority 1: Distribution Compliance & Licensing Resolution (Mandatory for Binary Release)
1. **Resolve B6 (Qt Replaceability)**: Investigate exact ABI and symbol requirements
   for PySide6/Qt DLL replacement under Inno Setup / PyInstaller, or explore
   alternative compliance avenues (e.g., source-distribution-only model or commercial
   licensing).
2. **Resolve B1–B5 (Attribution & Rights)**: Formalize Microsoft C++ runtime
   redistribution terms, compile-time SBOM receipts for static Rust dependencies,
   and exact source patch manifests for shipped wheels.
3. **Code Signing Architecture**: Determine policy and infrastructure for Windows
   Authenticode signing to mitigate potential SmartScreen and application-reputation
   friction on external systems.

### Priority 2: Isolated Clean-Machine Validation (Mandatory for Installer Reliability)
1. **Execute Disposable VM / Windows Sandbox Matrix**: Run
   [`tools/m10/validate_installer.ps1 -EnvironmentKind DisposableVM`](../tools/m10/validate_installer.ps1)
   on an isolated clean machine to close C01–C16.
2. **Execute C07 & C14 Checks**: Verify actual missing-model UI blocking, explicit
   download-confirmation cancellation, and alternative `/DIR` target refusal in the
   compiled installer.

### Priority 3: Formal Evidence & Capability Certification (Mandatory for Model Capability Claims)
1. **Resume M9.2 Evaluation**: Execute authentic software feedback data acquisition
   (180 primary feedback items) and double-blind human reference evaluation (60 items)
   to discharge Q5.
2. **Execute M9.3 Formal UAT & Accessibility Audit**: Run the 49-step scenario UAT
   pack and perform Windows UI Automation / screen-reader accessibility auditing.
3. **Owner Packaged-App Smoke Trial**: Conduct the planned 30-minute owner
   exploratory review on the installed application.

---

## 6. Defensible Recommendation

Based on the verified records and technical facts of the repository:

* **For Downloadable Binary Distribution**: **RECOMMENDATION IS NO-GO**.
  Distributing binary installers at this stage would leave unresolved LGPL written-offer
  and corresponding-source obligations (B1), unverified Qt replacement compatibility
  after failed cross-version experiments (B6), unestablished third-party and Microsoft
  runtime distribution rights (B2–B5), and potential SmartScreen/reputation friction.
  Furthermore, model capability claims remain unsupported pending Q5 representative-domain
  evaluation.
* **For Public Source-Code Portfolio Presentation**: **RECOMMENDATION IS GO (LIMITED TO SOURCE PRESENTATION)**.
  Recommended for accurate public repository presentation under open-source MIT terms,
  showcasing software engineering, architectural evolution, test suites, and transparent
  governance documentation without binary distribution. This recommendation does not
  constitute formal owner release approval.
* **For Controlled Product Demonstrations**: **RECOMMENDATION IS GO (CONTROLLED)**.
  Local demonstrations on author-operated machines using synthetic data are defensible
  and technically validated on the development host.

**Final Determination**:
The formal release and distribution decision remains strictly **PENDING OWNER DECISION**.
Neither binary distribution nor a V2 release candidate tag is authorized without explicit
written direction from the repository owner.
