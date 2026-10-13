# V2 M10 S5 — Clean-machine completion record and Release-1 gate packet

Status: **Release-1 gate: OWNER-APPROVED CONDITIONAL EXIT.** S5 raw guest
evidence reviewed. H2-A, C02–C12 and C14 PASS on the reviewed automated
evidence. The icon check is 2 of 4 confirmed and 2 of 4 NOT DETERMINED; the
owner accepted the two gaps as carried-forward items. This is not a release
or distribution permission.

- **Runs.** The owner ran Stage A and Stage B on an isolated VMware guest.
- **Export.** The owner exported the raw evidence to a private host folder.
- **Review.** The evidence was reviewed read-only (§2).
- **No failures.** No assertion failed, and no FAIL item exists.
- **Gate.** The owner approved a CONDITIONAL exit in the working chat (§6). No
  handwritten signature, timestamp or other proof is claimed, and nothing in
  this record upgrades the exit to PASS.

Unchanged:

- `distribution_permitted` stays false; B1 and B4 stay OPEN; B6 stays closed
  only on its QtCore-only criterion; C15 BLOCKED; C16 NOT RUN.
- M9.2–M9.4 stay DEFERRED.
- Nothing was rebuilt, re-downloaded or published.

The only code change in this closure is the junction cleanup in
`tools/m10/validate_installer.ps1` (§4, PR #72).

## 1. Candidate and version chain

| Item | Value |
| --- | --- |
| Frozen application and build commit | `a16d55969c13ce8f0b1cc19e578751845e13b55f` (main after PR #71) |
| Internal installer `STI-0.10.0-internal-x64.exe` | SHA-256 `aa43ca1d0a4c52baa34307e4c92bd10306bcda9a436e4f75ec8dabaa82e01d68`, 726,702,002 bytes |
| Installer receipt | SHA-256 `4fb65d2ed8183f2c4cdb1053e7f46db18ae21d262a56ca7f02a6237a9ddb9711`; blockers B1, B4; `distribution_permitted` false; models not bundled |
| `validate_installer_lib.ps1` | `c52d4fd1b944c1e76aa7b7b919971b2fd87b848b5073dcdb6e09011190431c32`, identical to main, in every input |
| `StiUia.ps1` (runner UI Automation helpers) | `9c2e375e2b18648e22a0e6269a19ba430acd5ed363c109b466d9afef3b4036f2`, unchanged in every input |

The runner (`Run-S5.ps1`, `StiUia.ps1`, the stage launchers and
`Create-Marker.cmd`) is acceptance tooling outside the repository and the
installer payload. It went through three read-only ISO inputs. The hashes below
were recomputed from each ISO's contents, read on the host.

| Input ISO | ISO SHA-256 | `SHA256SUMS.txt` | `validate_installer.ps1` | Use |
| --- | --- | --- | --- | --- |
| Stage 1 frozen package | `9851a7ad11be32e31a38d9c5b273c123fbba1d9d94f414237765f253b5e7364c` | `2628f792…717d` | `b8db1272…3626` (main) | Superseded: its launchers stop on a Restricted script policy |
| Policy A | `920a0d8bafb8102c8528e93180e23f4aceec7ef57bc56c12fcb8ff6cd3c95cf0` | `9de5c7e7cc1de0d63a2efea3bb8a3d0d21b073a11130a665334ab5a092a764f5` | `b8db1272…3626` (main) | Stage A, inferred (§1.1); first Stage B attempt, interrupted |
| Policy A + harness fix | `0449d4ee6428ce6c94dc7784fa423c90aa6f9a15ca58812a7753fd11132938a6` | `ff0e5b2d622db32217051c53fb62f885a7c55dd9f0f41aeb84f31db1c2c2bea0` | `15ad4a834949b555f48b9a0afb8c0632eab3862cc4151ef72b48cadea4e10f61` | Stage B rerun |

Between the Stage 1 package and Policy A, the changes were:

- **Launchers.** They now verify all nine manifest entries, the pinned script,
  installer and receipt hashes and the candidate receipt before starting one
  child Windows PowerShell process with `-ExecutionPolicy Bypass` (§5).
- **`Run-S5.ps1`.** Only its final message changed: raw evidence stays in the
  guest (`5e7e5d81…` → `9e0c8ba1ac01c26753cab3f24bfb632420b4c1b0ccdbb04560c4c69f22e8b470`).

The harness-fix input changes only `validate_installer.ps1`, the launcher pins
and the manifest.

**Since PR #72, the repository harness is byte-identical to the harness that
Stage B ran** (`15ad4a83…`). Before it, main held `b8db1272…3626`.

### 1.1 Stage and snapshot facts

The guest was not touched by this review. Snapshot presence, parentage and
times come from read-only host metadata (the VM's snapshot list and file times).
The VC++ versions match the exported baselines (§2.2).

| Snapshot | Present | Note |
| --- | --- | --- |
| `S5-Pre-Runtime-Upgrade` (VC++ 14.40) | yes | Stage A base |
| `S5-Runtime-Ready` (VC++ 14.51) | yes | Stage B base |
| `S5-F2-Preserve` | yes | Preservation point taken before Stage A/B |
| `S5-StageA-Evidence` | yes | Child of `S5-Pre-Runtime-Upgrade` |
| `S5-StageB-Evidence` | yes | Child of `S5-Runtime-Ready`; state after the final uninstall |
| `S5-StageB-Interrupted-Evidence` | **no** | Not in the snapshot list; the interrupted attempt has no protected state |
| `S5-Models-Ready-Inference-PASS`, `S5-All-Models-Ready` | yes | Real-model snapshots; untouched |

- **Stage A input (inferred).** Stage A ran 17:42–17:48 local time, before the
  harness-fix ISO existed (18:23). So it used the Policy A input and main's
  harness. The evidence does not record the harness hash. Missing mode never
  reaches the junction code.
- **Stage B input.** Stage B ran 18:36–18:42 with the harness-fix ISO attached.
  Its non-interactive Present run completed through the junction cleanup that
  made the old harness prompt. That strongly supports harness `15ad4a83…`, but
  the hash itself is not recorded in the evidence.
- **Guest isolation.** The guest's network adapter does not connect at power-on,
  clipboard and drag-and-drop are disabled, and no shared folder is configured.

## 2. Evidence export and review

The owner exported four guest folders to a private, Git-ignored host folder:

- `STIEvidence-A` and `STIValidation-A`;
- `STIEvidence-B` and `STIValidation-B`.

The review was read-only: no evidence file was changed, moved or deleted. The
full review report stays private on the host, because the raw logs contain the
guest account and machine names, and one screenshot shows the account name.
This section carries only verdicts and hashes.

### 2.1 Integrity

| Check | Stage A | Stage B |
| --- | --- | --- |
| `EVIDENCE-SHA256.txt` entries recomputed and equal | 8 of 8 | 22 of 22 |
| Listed but missing / exported but unlisted | 0 / 0 | 0 / 0 |
| `EVIDENCE-SHA256.txt` SHA-256 | `8c18a2b7320523d0e10d7738388992f23de0f91cab6c8b6641f4a6651d0feb01` | `b325188afcb25fafaf113343d2247450767b679940061414a196fbbb6fa1ded8` |
| `observations.json` equals the runner's copy | yes | yes |
| Candidate in the observations | installer `aa43ca1d…1d68`, application `a16d559…` | same |
| Blockers in the observations | B1, B4; `distribution_permitted` false | same |

Limits of this evidence:

- **No external anchor.** The manifest was produced inside the guest at the end
  of each run. It proves the export is complete and unaltered relative to the
  guest's own record, but nothing outside the guest anchors it.
- **Console agreement.** Every console line the owner reported earlier appears
  verbatim in the runner transcripts and `summary.json`.

### 2.2 Baselines

| Field | Stage A | Stage B |
| --- | --- | --- |
| Windows build, x64 | 10.0.26200, yes | 10.0.26200, yes |
| Standard user | yes | yes |
| VC++ x64 runtime | 14.40.33816, below 14.44 | 14.51.36247, meets 14.44 |
| Network available | false | false |
| STI install, data, Start Menu and uninstall registration absent | yes | yes |

The baseline and the VM marker are automated records and operator intent, not
proof of a clean machine; the snapshot identity comes from the owner and the
host metadata.

## 3. C01–C16 and stage matrix

Columns:

- **Automated evidence (reviewed):** what the raw harness and runner records
  show, read in the exported files.
- **Owner witness:** a human observation the owner reported. It is not a gate
  signature.
- **Determination:** the verdict the reviewed evidence supports. PASS here means
  the raw automated evidence supports the check. It is not an owner signature.

| ID | Check | Automated evidence (reviewed) | Owner witness | Determination | Gap |
| --- | --- | --- | --- | --- | --- |
| H2-A | Missing runtime refused, nothing left behind (Stage A) | Observations: `install_refused_without_runtime` and `no_residue_after_refusal` PASS. The harness writes them only after asserting exit code 1, the refusal log line, no install, data, Start Menu or registration, and an empty TEMP. The installer log records the "14.44 or later is not installed" line and `InitializeSetup returned False` | n/a | PASS | The exit-code value is implied by the assert, not stored |
| C01 | Verified artifact builds into unsigned installer | Stage 1 host build and receipt verification (kept privately on the host) | n/a | PASS (host build) | Not a guest item |
| C02 | Fixed per-user path, installed payload hashes | `installed_payload_matches` true; the runner's reinstall matched every payload file to the receipt | n/a | PASS | None |
| C03 | Start Menu target, working directory, licence link | `start_menu_target` PASS (target, working directory and licence shortcut asserted) | n/a | PASS | None |
| C04 | First native window and safe close | `first_native_launch` PASS; smoke `window` true | n/a | PASS | None |
| C05 | Native dependency readiness without models | `app_runtime.ready` true, `models_loaded` false | n/a | PASS | None |
| C06 | No model weights; synthetic project reopens | Smoke: `models_unbundled` true, `reopened` true, 2 project rows, 1 invalid row | n/a | PASS | None |
| C07 | Missing-model analysis blocked; no download started (limited definition) | All runner steps PASS: dialog shown; closed with **Later**; text entered; "Analysis is unavailable" shown; Analyze disabled; model listing identical before and after. The UIA log shows only "Later" invoked. Two screenshots show "0 of 2 models ready" and the block | **Owner-reported human witness confirmed:** the owner saw "Analysis is unavailable" with models missing, and no download started after "Set up models" was closed | PASS (limited definition) | The Analyze button is outside the screenshot; "disabled" rests on the UIA read |
| C08 | Licence material present and removed on uninstall | `license.materials_present` true; `uninstall_owned_files_and_license_removal` PASS | n/a | PASS | None |
| C09 | Reparse redirect refuses uninstall; external sentinel kept | `reparse_uninstall_refusal` PASS; `external_sentinel_preserved` true; the exported external sentinel is intact. The first attempt was interrupted at the junction cleanup (§4) | n/a | PASS | None |
| C10 | Normal uninstall, both shortcuts removed | `shortcuts_removed` and `uninstall_registration_removed` PASS; the runner's uninstall exited 0 with 0 payload files left | n/a | PASS | Inno overwrites its log, so the earlier uninstalls rest on the harness asserts |
| C11 | Reinstall and second uninstall with unrelated data | `reinstall` PASS; the runner reinstalled the same candidate with matching payload | n/a | PASS | None |
| C12 | Synthetic project/model/unrelated bytes kept | `preservation_sentinels` PASS; three synthetic sentinels have the same hash before and after C07 and the uninstall | n/a | PASS | None |
| C13 | Malformed packet, traversal and output-collision guards | Repository tests and CI; not part of the VM run | n/a | Automated checks only | No clean-machine run |
| C14 | Alternative `/DIR` refused by the real installer | Refusal "Only the fixed per-user application location is supported." in the installer log; exit code 7 recorded; target empty; no residue | n/a | PASS | None |
| C15 | SmartScreen/signing and distribution approval | n/a | n/a | **BLOCKED** | Legal blockers B1 and B4; no signing |
| C16 | Owner 30-minute smoke and formal Windows UAT | n/a | n/a | **NOT RUN** | Not in scope |
| Icons | One STI icon in four places (S5-UI-001) | Five runner screenshots, reviewed visually (§3.1) | Owner accepted the two gaps as carried-forward items | 2 of 4 confirmed; 2 of 4 NOT DETERMINED; no defect found | Start Menu menu UI and Settings › Apps not shown |

These definitions are limits, not results:

- **C07 meaning (owner-approved).** The product has no separate download
  confirmation or Cancel dialog. The check is:
  1. the user closes "Set up models" with **Later**;
  2. no Download control is pressed;
  3. analysis is blocked while models are missing;
  4. no new model files appear.

  No Cancel interaction is claimed.
- **C14 meaning.** Exit code 7 alone is not the verdict. The verdict needs the
  installer's refusal and no residue anywhere.

**FAIL items:** none.

**Benign observation.** The Stage B harness's own output folder keeps one Inno
uninstaller temporary copy in its isolated TEMP. This is outside the
application, data, Start Menu and registry namespaces.

### 3.1 Icon review (agent visual review)

The five screenshots were compared with the repository `sti.ico` (design A),
rendered at 16–256 px. No other exported screenshot shows the Start Menu menu
UI or Settings › Apps.

The four formal places come from the S5-UI-001 check: the Start Menu entry,
the window title bar, the taskbar button and Settings › Apps. The Start Menu
programs-folder shortcut is separate supporting evidence and is not counted
among the four.

| Place | Kind | Finding | Determination |
| --- | --- | --- | --- |
| Window title bar | Formal (1 of 4) | The dedicated title-bar crop missed the icon. Four other screenshots show the window's and dialog's title-bar icon: the 16 px single-bar variant | Confirmed: matches design A |
| Taskbar | Formal (2 of 4) | Blue rounded square with a two-bar speech bubble; the app's running indicator is visible | Confirmed: matches design A |
| Start Menu (menu UI) | Formal (3 of 4) | The "Recommended" entry is cut off by the 560-pixel-high guest display | NOT DETERMINED, not FAIL |
| Settings › Apps | Formal (4 of 4) | The A–Z list was not scrolled to STI, so STI is not in view | NOT DETERMINED, not FAIL |
| Start Menu programs-folder shortcut | Supporting, not counted | "Social Text Intelligence" shortcut shows the design A icon with the shortcut arrow | Matches design A |

**Result:** 2 of 4 formal places confirmed, 2 of 4 NOT DETERMINED.

**Cause of the gaps.** The gaps come from the runner's screenshot capture: a
small display, a misplaced crop and no scrolling. They do not show a product
defect, and no product icon defect is known.

## 4. Junction cleanup fix (formal harness)

**Defect.** In Present mode the harness redirects the installed `legal` folder
to a synthetic external target through a junction, then removes the junction.
The main harness `b8db1272…3626` used `Remove-Item -LiteralPath $legal -Force`.
On Windows PowerShell 5.1, that command asks for confirmation to recurse into a
non-empty junction, and the prompt stopped the first Stage B attempt. The prompt
comes before any deletion. How it was answered is not recorded, and the
interrupted attempt has no protected snapshot.

**Fix (PR #72).** The fix was made outside the repository and reviewed before
Stage B was rerun. It was ported unchanged, so the repository file hash equals
`15ad4a83…`. The new `RemoveVerifiedJunction`:

1. Reads the link with `Get-Item -Force`.
2. Requires `LinkType` `Junction`, the reparse-point attribute and the expected
   target. If any of these differs, it fails with "Unexpected link: stop and
   inspect manually." and removes nothing.
3. Calls `RemoveDirectoryW` through a small `Add-Type` type. This deletes only
   the directory entry: for a junction that is the link itself, never the
   target's contents. It cannot remove a non-empty ordinary directory.
4. Raises the Win32 error if the call fails.
5. Asserts that the link is gone.

The surrounding `finally` block still checks the external sentinel's hash
before restoring the held folder. If any step fails, the harness stops, and the
held folder and the target stay in place for manual inspection.

**Not used:** `-Recurse`, an automatic answer to the prompt, or a silent
deletion.

**Residual limits:**

- **Time-of-check gap.** A gap exists between verification and removal. It is
  accepted for a disposable, single-operator VM.
- **Add-Type.** It needs the normal .NET compiler and is unavailable in
  Constrained Language Mode (for example under WDAC). There it throws after
  verification and before removal, so nothing is removed, but the harness
  cannot complete in that mode.
- **Masked error.** If the verification, `Add-Type` or `RemoveDirectoryW` fails
  inside `finally`, its error replaces any error from the `try` block. The
  install is then left with the junction at `legal` and the original folder at
  `legal-m10c-held`. Nothing is lost, but the root cause must be read from the
  log. This was not changed, so that the repository harness stays
  byte-identical to the one Stage B ran.

**Tests** (`tests/tools/test_m10_validate_installer.py`) run the helper as
defined in the harness, extracted from its syntax tree, on Windows PowerShell
5.1:

- a verified junction over a non-empty nested target is removed without a
  prompt, and the target and held bytes are unchanged;
- a junction to a different target, a plain non-empty directory and a missing
  link are each refused, and nothing is removed;
- a static check confirms the redirect cleanup calls the helper, never uses
  `Remove-Item` on the link, and verifies before removing.

The behavioural tests fail against main's previous harness and pass against
the fix. They are Windows-only and skip on the Linux CI.

## 5. Script-policy exception (Policy A)

M10-C says "there is no automatic logon command or execution-policy bypass".
That wording is unchanged.

**Reason.** The guest's script policy blocked the reviewed runner, and the
Stage 1 launchers correctly stopped for an owner decision.

**Exception granted.** For this S5 run only, the owner authorized one bounded
exception (recorded privately on the host):

- each Stage launcher first verifies the frozen input package;
- it then starts exactly one child Windows PowerShell process with
  `-NoProfile -ExecutionPolicy Bypass -File Run-S5.ps1`;
- no machine or user policy is changed.

Both exported baselines record `execution_policy: Bypass` for the runner
process, consistent with this exception.

**Not authorized:**

- entering passwords;
- changing VMware security settings;
- connecting the guest to a network;
- removing the human-witness requirement.

**Trust anchor.** The launcher cannot authenticate itself through a manifest
that it executes. Trust comes from the independent ISO hash (§1), which the
owner is expected to check before running anything.

**Versions under the exception:**

- **Candidate:** `a16d559`, with installer `aa43ca1d…1d68`.
- **Policy A launchers:**
  - `Stage-A.cmd` `7ae07a2985dc5251b84ec736b20e4a27d99a803ed98de52cd89fedac76b9f675`
  - `Stage-B.cmd` `b95904e4c9ddd4032426134cb81cef1362b56060bbb086c2c9da2f449e1ff386`
- **Harness-fix launchers:**
  - `Stage-A.cmd` `978bee8060208e821974cdd74671e2e85c05395d401a00a3296f8907fd97841a`
  - `Stage-B.cmd` `c47f93af1268dbee35691f737dc8ac0a9de78bd66c950496930c35c929781ca0`
- **Runner:** `Run-S5.ps1` `9e0c8ba1…b8470` in both inputs.

**Governance.** M10-C keeps its rule. A future clean-machine run needs its own
owner authorization, and this exception does not carry over.

## 6. Release-1 gate decision

**Decision: OWNER-APPROVED CONDITIONAL EXIT.**

- **Source.** The owner gave the approval explicitly in the working chat. No
  handwritten signature, timestamp or other proof is claimed.
- **Icon gaps.** The owner accepted the two icon evidence gaps as
  carried-forward items.
- **No rerun.** The owner did not require a new VMware acceptance run.
- **Not a release permission.** A CONDITIONAL exit permits no product release
  or distribution.

Done:

- the candidate is pinned;
- the formal harness matches what Stage B ran;
- the exported evidence chains are complete;
- H2-A, C02–C12 and C14 PASS on the reviewed automated evidence;
- C07 has the owner-reported human witness;
- no FAIL item exists.

Why CONDITIONAL and not PASS:

1. **Carried-forward icon gaps (S5-UI-001).** The Start Menu menu UI and
   Settings › Apps have no visual evidence. No defect is known. A later short
   re-check could close them, and would not be a rerun of the whole
   acceptance.
2. **Pull-request merges.** Approval to merge a pull request is separate from
   this gate decision.

**Independent of this gate:**

- distribution stays prohibited, because B1 and B4 are open and C15 is BLOCKED;
- C16 and formal UAT remain NOT RUN.

| Owner field | Value |
| --- | --- |
| Release-1 gate decision | OWNER-APPROVED CONDITIONAL EXIT (approval given in the working chat; no handwritten signature) |
| C07 witness | Owner-reported human witness confirmed (limited definition) |
| Icon visual review | 2 of 4 formal places confirmed; 2 of 4 NOT DETERMINED, accepted by the owner as carried-forward items |
| Evidence export reviewed | Received and reviewed read-only (§2) |

## 7. Evidence request (fulfilled)

The one-time request for the Stage A/B folders was fulfilled: the owner
exported them to a private host folder. The raw files stay private on the host and are never
committed. Only the verdicts and hashes in §2–§3 enter the repository.

## 8. Not done

- No change to the product, the installer build, the receipt, the frozen
  candidate or the ISOs.
- No new Windows acceptance run.
- No guest access by the reviewer.
- No handwritten gate signature, and no publication.
