# V2 M10 S5-A — Clean-machine harness hardening (H1–H3)

Status: **COMPLETE on `main` (PR #70).** At the time of this PR the harness
had not been run. It has since been run in S5 Stages A and B, with a later
junction-cleanup fix (§5). Its reviewed observations support H2-A and
C02–C12; Release-1 ended as an owner-approved CONDITIONAL exit. See the
[S5 completion record](V2_M10_S5_COMPLETION_RECORD.md).

- B1 and B4 stay OPEN.
- B6 stays closed only on its QtCore-only criterion.
- `distribution_permitted` stays false, and nothing was rebuilt or published.

Only `tools/m10/validate_installer.ps1`, its new shared checks in
`tools/m10/validate_installer_lib.ps1`, their tests and these records changed.
The harness is not part of the installer payload, so the existing internal
installer (SHA-256 `a7fedbd633dd00651df8c22e6d6fac4ea749f25c948f6c3a96126d5e35ebe071`)
and its receipt remain valid inputs.

## 1. What changed

| Gap | Before | Now |
| --- | --- | --- |
| H1 blockers | `legal_blockers` hard-coded as `B1`–`B6` | Taken from the receipt by `Get-StiReceiptFacts` after a fail-closed structural check (§2). `other_packet_blockers` and `release_conditions` come with them |
| H2 VC++ runtime | No runtime stage; a missing runtime only failed as "Installation failed" | A mandatory `-RuntimeExpectation Missing\|Present` is checked against the real 64-bit registry values, with the installer's own rule: `Installed = 1` and version 14.44 or later |
| H3 acceptance | `observations.json` wrote a fixed `clean_machine_acceptance` string next to automated results | Observations (schema 2) contain automated results only. `clean_machine_acceptance` is always `NOT DETERMINED BY THIS HARNESS`; the clean-baseline proof and the owner's witness are recorded elsewhere; the VM marker is operator intent, not proof |

**Missing mode** runs the silent installer once. It passes only if all of these
hold:

- the exit code is **1** (Inno Setup's "failed to initialize": `InitializeSetup`
  returned False);
- the installer log contains its line "…14.44 or later is not installed.";
- no install folder, data folder, Start Menu folder or uninstall registration
  exists afterwards;
- the isolated TEMP is empty.

It does not run the lifecycle.

**Present mode** runs the existing lifecycle unchanged and also checks that the
uninstall registration is removed.

These protections are unchanged:

- the output folder must be new;
- existing install, data and Start Menu namespaces are refused, and an existing
  uninstall registration is now refused as well;
- payload paths cannot escape the install folder;
- the junction redirect test, the external and preservation sentinels, and no
  recursive cleanup;
- the environment is restored on exit, and the harness fails closed.

## 2. Receipt checks (H1)

A receipt is refused if any of the following holds:

- it is not one JSON object, or not integer schema 1;
- it is not compiled;
- it permits distribution, or the flag is not a strict boolean;
- it bundles models;
- its installer hash, application revision or any payload entry is malformed,
  or the payload is empty;
- `legal_blockers` is not a list, is empty, contains a code outside `B1`–`B6`
  (case-sensitive), repeats a code, or omits B1;
- an uncoded blocker is not non-empty text;
- `release_conditions` lacks `B6`, `clean_machine_validation` or
  `public_source_hosting`, or holds anything but text;
- it claims a clean-machine or owner-smoke result;
- it reports B6 both as a packet blocker and as a release condition.

The real S4 and S5-NET-001 receipts pass, each with blockers B1 and B4.

## 3. Validation

| Check | Result |
| --- | --- |
| `tests/tools/test_m10_validate_installer.py` | The real lib functions run through PowerShell (Windows PowerShell locally, `pwsh` on CI) with synthetic receipts and registry values. Covers 25 unsafe receipts, 7 runtime states in both modes, the observation guarantees, parse checks, static checks (no fixed blocker list, no self-acceptance, guards kept) and cross-checks against `installer.iss` (registry key, `Installed = 1`, 14.44, AppId, refusal log line) |
| Local full suite (Windows, Python 3.12) | 1,361 passed, 7 opt-in skipped; Ruff and strict MyPy pass |
| Real data, read-only | Both real receipts give B1 and B4. This host's registry reads 14.51, which qualifies, and Missing mode is correctly refused here |
| Independent Spec and Standards reviews | No blocking findings. The should-fix items were addressed in `c178c83`: proof of refusal, TEMP residue, stricter receipt checks, shared constants, exact assertions |
| PR CI | One run on code head `c178c83` (PR #70) |

Not verified: the real Missing-mode exit code and log line on a machine without
the runtime. If either differs, Missing mode fails closed, and the stage must be
reported as not passed.

## 4. VM acceptance steps (to run; not run)

1. **Baseline proof (owner, recorded separately).** For each snapshot used,
   privately record:
   - the snapshot name;
   - the Windows build;
   - that the account is a standard user;
   - the result of
     `Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64' -ErrorAction SilentlyContinue`;
   - that no STI install, data or Start Menu folder exists.

   The harness does not provide this proof.
2. **Inputs.** Copy `STI-0.10.0-internal-x64.exe`, `installer-receipt.json`,
   `validate_installer.ps1` and `validate_installer_lib.ps1` (from `main`) to
   `C:\STIInput`. Verify the installer hash. Create the marker
   `C:\STI-M10C-VM.txt`, as in the M10-C record.
3. **Stage A, Missing.** Use a snapshot whose registry shows no qualifying
   runtime. If it has one, the harness refuses: use or create a runtime-free
   snapshot. Run with `-RuntimeExpectation Missing -Output C:\STIValidation-A`.
4. **Stage B, Present.** Use a fresh snapshot that has VC++ 14.44+ and no STI
   installed, such as `S5-Runtime-Ready` before any STI install. Run with
   `-RuntimeExpectation Present -Output C:\STIValidation-B`.
5. **Owner witness (separately).** Record the manual checks the harness does not
   perform, such as the C07 missing-model UI and download-cancel interaction.
6. **Summary.** Keep raw logs private in the guest. Export only a
   privacy-reviewed summary: both `observations.json` files, the baseline
   record and the witness record. Clean-machine acceptance is decided from all
   three together, never from `observations.json` alone.

The guest's script policy still applies. M10-C does not authorize a policy
bypass, so if policy blocks the script, the owner decides how to proceed.

## 5. Later fix: junction cleanup (S5 closure)

Stage B showed that `Remove-Item -Force` on the verified test junction asks for
recursion confirmation on Windows PowerShell 5.1. `RemoveVerifiedJunction` now
verifies the link type, reparse attribute and target, then removes only the link
with `RemoveDirectoryW`. See the [S5 completion record](V2_M10_S5_COMPLETION_RECORD.md) §4.

## 6. Not done

- S5-UI-001 (the application icon) is a separate open item.
- C14 (`/DIR` refusal) is not automated here.
- No new features.
- No change to R1/R2, licensing or the distribution architecture.
- No rebuild.
