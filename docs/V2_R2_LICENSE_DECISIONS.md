# V2 Release-2 — Final licence decision closure (LD1–LD6)

Status: **LD1–LD6 OWNER-ASSESSED. B4 is closed in the packet derivation. B1
stays OPEN for one operational prerequisite: public source access.
`distribution_permitted` stays false.**

The repository owner formally approved the internal compliance assessments for
LD1–LD6 (2026-10-13). That approval covers the disclosed residual risks, the
Intel licence's high-risk-use disclaimer, and the bounded oneTBB finding of
**NOT REQUIRED**.

These are **owner-assessed compliance decisions**. They are not an external
legal certification. They are not a special permission from Qt, Intel or any
other rights holder.

The evidence is the existing record, which this milestone does not reopen:

- [Release-2 compliance record](V2_R2_COMPLIANCE_CLOSURE.md);
- [B1 decision memo](V2_M10_S4_B1_DECISION_MEMO.md);
- the Intel provenance and notices in `distribution/legal/intel-openmp/`;
- the source-access materials.

## 1. Decisions

| # | Owner decision | Evidence basis | Residual risk accepted | Blocker effect |
| --- | --- | --- | --- | --- |
| LD1 | The hash-pinned upstream Qt 6.11.2 and `pyside-setup` 6.11.2 release sources and build scripts are delivered as the Corresponding Source of the unmodified official binaries (D1) | All 25 Qt binaries and 96 translations match the official build SBOMs. QtBase/QtSvg match by commit. The binding binaries are byte-identical to the official wheels. `pyside-setup` equals the `v6.11.2` tag tree (S4 memo §2; Release-2 §3.1) | Exact binding producer-source correspondence is unproven. The wheels carry no producer build record, and PyPI publishes no PEP 740 provenance for them | B1 legal subitem closed |
| LD2 | In-package source archives plus GPL v3 §6(d) equivalent access from the download location are the delivery route (D2). Download-only distribution to users' own PCs does not trigger Installation Information (D3) | The archives are in `legal/sources/` with pinned hashes. No User Product is transferred. There is no signature or integrity lock (S4 memo) | The equivalent public access is **not operational** until it is published with a release | B1 legal subitem closed; the operational prerequisite stays (§3) |
| LD3 | Intel's no-reverse-engineering term, scoped in writing to `libiomp5md.dll` and `libiompstubs5md.dll`, is compatible with LGPL v3 §4 for the Qt libraries (D4) | The scope is written in `intel-openmp/NOTICE.md`, `QT_NOTICE.md` and the in-app licence text. The Intel DLLs are loaded by PyTorch, not by Qt (Release-2 §2) | The scope rests on the written notices. Intel has not confirmed it | D4 closed for B1 and B4 |
| LD4 | The two DLLs taken from Intel's pinned, author-signed NuGet package `intelopenmp.redist.win` 2026.1.0.239 are redistributed under the Intel Simplified Software License (Version October 2022) | Package SHA-512 equals the NuGet catalog. The Intel Corporation EV author signature was verified. The build replaces PyTorch's byte-identical copies (Release-2 §1) | Byte-identical copies also reach the build through PyTorch under the Developer Tools EULA. Certificate revocation was not checked | B4 Intel subitem closed |
| LD5 | `intel-openmp/NOTICE.md` satisfies the licence's notice condition. It carries the package's "Copyright Intel Corporation.", the full licence text and `third-party-programs.txt` | Package nuspec copyright; licence and third-party texts byte-identical to the package | The licence text itself carries no copyright line | B4 Intel subitem closed |
| LD6 | The owner accepts the licence's high-risk-use disclaimer. The oneTBB third-party file that `third-party-programs.txt` refers to is **not required** | `libiomp5md.dll` statically contains oneTBB's tbbmalloc 2022.3.0. Its only third-party code, ITT Notify, and oneTBB itself are already listed in the shipped `third-party-programs.txt`. That file's `<install_dir>/tbb/...` line is a generic oneAPI installer cross-reference. The other oneTBB third-party entries are not part of tbbmalloc's upstream build definition. Evidence: PE imports and strings only, no disassembly; upstream oneTBB v2022.3.0 `third-party-programs.txt` and `src/tbbmalloc/CMakeLists.txt` | The oneTBB finding rests on the upstream build definition, not on Intel's internal build | B4 Intel subitem closed |

## 2. How the decisions are enforced

`distribution/legal/LICENSE_DECISIONS.json` (schema 1) records the six
decisions. It ships in the packet. `tools/m10/compliance.py` holds its approved
content **exactly** (`LD_SCHEMA_1`), scoped to:

- the source manifest's Qt version and archive hashes;
- the two binding packages;
- the pinned Intel package's id, version and SHA-256.

The record is a reviewed code constant, not a self-declared field.

| Packet state | Result |
| --- | --- |
| Valid record, valid B1 engineering record, verified Qt binaries | B1 is narrowed to `B1_ASSESSED`. Its legal subitems are closed, and it names the unoperational public source access. B1 is **never removed** |
| Valid record, and the shipped Intel DLLs, licence texts, notice and NuGet source all match the package it names | The B4 Intel item is dropped. With no other B4 gap, B4 is not derived |
| Record missing, malformed, changed in any field, or scoped to another package or Qt version | B1 keeps its earlier wording and names the rejection. The B4 Intel item stays |
| Any Intel DLL, text, notice or source mismatch | The B4 Intel item stays, whatever the record says |

Fixed in every state:

- `distribution_permitted` is fixed at false in the packet and the installer
  receipt;
- the installer and the clean-machine harness still refuse a packet or receipt
  without B1;
- no schema can record public source hosting as operational or a release gate as
  passed.

Each case above has a test:

- `tests/tools/test_m10_license_decisions.py`;
- `tests/tools/test_m10_b4_notices.py`.

## 3. What is still required before any public release

These are operational release prerequisites, not open legal questions:

1. **Public source access (B1).** Host the archives and records under GPL v3
   §6(d), as prepared in
   [`distribution/release-source-page.md`](../distribution/release-source-page.md).
   Then:
   - update `SOURCE_ACCESS.md`;
   - add a reviewed record that the hosting is operational;
   - rebuild.

   The page is prepared, not published. It names no URL, because none exists.
2. **A separate Owner Release Gate**, including:
   - C15 (signing and SmartScreen), which is BLOCKED;
   - C16, which is NOT RUN;
   - the two carried-forward S5 icon evidence gaps.
3. **The formal claims that stay deferred:**
   - M9.2–M9.4 evidence (DEFERRED);
   - formal Windows UAT and accessibility acceptance.
4. **B5.** py3langid corpus terms stay unverified. B5 is not derived while the
   model is not bundled.

## 4. Validation

| Check | Result |
| --- | --- |
| Focused tests | The licence-decision, B4, B1-decision, installer, source-page and lifecycle tests pass; see the PR |
| Real-packet check (private) | The packet was re-assembled from a copy of the existing private frozen bundle (`ec824ba`). The bundle was not rebuilt and no installer was made. Result: packet valid; blockers exactly `[B1]` (`B1_ASSESSED`); `b4_coverage.remaining` empty; the Intel record owner-assessed; `distribution_permitted` false; the installer's packet check yields `["B1"]`. Receipt: [`r2-license-decisions-packet-check.json`](evidence/r2/r2-license-decisions-packet-check.json) |
| Installer | Not rebuilt. The private installer `b1295763…47ff` from Release-2 predates these decisions. Its receipt still records B1 and B4, as it should for that build |
| PR CI | One run on the PR's final head; the result is recorded in the PR |

## 5. Not done

- No installer rebuild, VMware run, product feature or model change, or M9
  change.
- No publication, tag, GitHub Release or merge.
- No reopening of the completed licensing investigations.
- `B1_OWNER_DECISION.json` (schema 1) is unchanged. It remains the owner's D1–D4
  engineering direction. `LICENSE_DECISIONS.json` supplements it: LD1–LD3
  answer its pending legal confirmation and its unresolved D4.
