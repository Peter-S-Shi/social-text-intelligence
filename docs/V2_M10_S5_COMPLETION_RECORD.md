# V2 M10 S5 — Clean-machine completion record and Release-1 gate packet

Status: **S5 clean-machine verdict NOT DETERMINED; Release-1 gate awaiting the
owner's signature.** Stage A and Stage B were run by the owner on an isolated
VMware guest, and the owner reported a PASS console for every automated stage.
The raw guest evidence has **not** been reviewed: it stays inside the encrypted
guest, and no approved channel to read it exists yet (§2). No C01–C16 item is
marked PASS on console output alone.

- `distribution_permitted` stays false; B1 and B4 stay OPEN; B6 stays closed
  only on its QtCore-only criterion; C15 BLOCKED; C16 NOT RUN.
- M9.2–M9.4 stay DEFERRED.
- Nothing was rebuilt, re-downloaded or published.

The only code change in this closure is the junction cleanup in
`tools/m10/validate_installer.ps1` (§4).

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
installer payload. It went through three read-only ISO inputs. All hashes below
were recomputed from the local files during this closure.

| Input ISO | ISO SHA-256 | `SHA256SUMS.txt` | `validate_installer.ps1` | Use |
| --- | --- | --- | --- | --- |
| Stage 1 frozen package | `9851a7ad11be32e31a38d9c5b273c123fbba1d9d94f414237765f253b5e7364c` | `2628f792…717d` | `b8db1272…3626` (main) | Superseded: its launchers stop on a Restricted script policy |
| Policy A | `920a0d8bafb8102c8528e93180e23f4aceec7ef57bc56c12fcb8ff6cd3c95cf0` | `9de5c7e7…64f5` | `b8db1272…3626` (main) | Stage A, inferred (§1.1); first Stage B attempt, interrupted |
| Policy A + harness fix | `0449d4ee6428ce6c94dc7784fa423c90aa6f9a15ca58812a7753fd11132938a6` | `ff0e5b2d622db32217051c53fb62f885a7c55dd9f0f41aeb84f31db1c2c2bea0` | `15ad4a834949b555f48b9a0afb8c0632eab3862cc4151ef72b48cadea4e10f61` | Stage B rerun (attached to the guest now) |

Between the Stage 1 package and Policy A, the changes were:

- **Launchers.** They now verify all nine manifest entries, the pinned script,
  installer and receipt hashes and the candidate receipt before starting one
  child Windows PowerShell process with `-ExecutionPolicy Bypass` (§5).
- **`Run-S5.ps1`.** Only its final message changed: raw evidence stays in the
  guest (`5e7e5d81…` → `9e0c8ba1ac01c26753cab3f24bfb632420b4c1b0ccdbb04560c4c69f22e8b470`).

The harness-fix input changes only `validate_installer.ps1`, the launcher pins
and the manifest.

**After this PR, the repository harness is byte-identical to the harness that
Stage B ran** (`15ad4a83…`). Before it, main held `b8db1272…3626`.

### 1.1 Stage and snapshot facts

The guest was not touched. These facts come from read-only host metadata (the
VM's snapshot list and file times):

| Snapshot | Present | Note |
| --- | --- | --- |
| `S5-Pre-Runtime-Upgrade` (VC++ 14.40) | yes | Stage A base |
| `S5-Runtime-Ready` (VC++ 14.51) | yes | Stage B base |
| `S5-F2-Preserve` | yes | Preservation point taken before Stage A/B |
| `S5-StageA-Evidence` | yes | Child of `S5-Pre-Runtime-Upgrade` |
| `S5-StageB-Evidence` | yes | Child of `S5-Runtime-Ready`; the current snapshot |
| `S5-StageB-Interrupted-Evidence` | **no** | Not in the snapshot list; the interrupted attempt has no protected state |
| `S5-Models-Ready-Inference-PASS`, `S5-All-Models-Ready` | yes | Real-model snapshots; untouched |

- **Stage A input (inferred).** The `S5-StageA-Evidence` snapshot is older than
  the harness-fix ISO, so Stage A must have used the Policy A input and the
  main harness. Missing mode never reaches the junction code. Guest
  confirmation would settle this.
- **Guest isolation.** The guest's network adapter does not connect at power-on,
  clipboard and drag-and-drop are disabled, and no shared folder is configured.

## 2. Evidence access

The raw evidence is the following, all inside the guest:

- `C:\STIValidation-A\observations.json` and `C:\STIValidation-B\observations.json`;
- the harness logs;
- `C:\STIEvidence-A` and `C:\STIEvidence-B`, which hold `baseline.json`,
  `summary.json`, `uia-log.txt`, copies of the observations, the screenshots and
  `EVIDENCE-SHA256.txt`.

No exported or privacy-reviewed copy exists on the host. Reading the evidence
requires the owner's credentials for the encrypted VM, and a transfer channel
the isolation settings deliberately block. Neither was pre-authorized, so
nothing was attempted.

Every guest-side statement below is therefore an **owner-reported console
observation**: a value the runner printed and the owner relayed. It is not
evidence reviewed in this closure, and it is not an owner witness of the GUI
(§3, "Owner witness"). §7 makes one minimal request that would close this gap.

## 3. C01–C16 and stage matrix

Columns:

- **Automated observation:** what the harness or runner reported, as relayed by
  the owner.
- **Owner witness:** a separate human signature. None has been recorded yet.
- **Determination:** the verdict that the reviewed evidence supports today.

| ID | Check | Evidence source | Automated observation (owner-reported) | Owner witness | Determination | Gap |
| --- | --- | --- | --- | --- | --- | --- |
| H2-A | Missing runtime refused, nothing left behind (Stage A) | Guest `STIValidation-A\observations.json`; runner baseline | `[PASS] baseline` (VC++ 14.40, standard user, offline, no STI namespaces), `[PASS] marker`, `[PASS] H2-A Harness completed`, UI Automation capability PASS | Not recorded | NOT DETERMINED | Exit code, log line and residue values unreviewed |
| C01 | Verified artifact builds into unsigned installer | Host build and receipt (Stage 1) | Build exit 0; icon check, `--verify-runtime`, `--smoke`, `--license-info` exit 0; receipt and installer hash match | n/a | PASS (host build evidence) | None for the build itself |
| C02 | Fixed per-user path, installed payload hashes | Guest harness; runner reinstall payload check | `harness-present` PASS; `reinstall` PASS | Not recorded | NOT DETERMINED | Observations unreviewed |
| C03 | Start Menu target, working directory, licence link | Guest harness | `harness-present` PASS | Not recorded | NOT DETERMINED | Observations unreviewed |
| C04 | First native window and safe close | Guest harness | `harness-present` PASS | Not recorded | NOT DETERMINED | Observations unreviewed |
| C05 | Native dependency readiness without models | Guest harness (`--verify-runtime`) | `harness-present` PASS | n/a | NOT DETERMINED | Observations unreviewed |
| C06 | No model weights; synthetic project reopens | Guest harness (`--smoke`) | `harness-present` PASS | n/a | NOT DETERMINED | Observations unreviewed |
| C07 | Missing-model analysis blocked; no download started (limited definition) | Runner `C07` entry in `summary.json`, model listing, `uia-log.txt` | `C07` PASS | **Pending:** the owner watched the run, but nothing is signed | NOT DETERMINED | Results and owner signature |
| C08 | Licence material present and removed on uninstall | Guest harness | `harness-present` PASS; `uninstall` PASS | n/a | NOT DETERMINED | Observations unreviewed |
| C09 | Reparse redirect refuses uninstall; external sentinel kept | Guest harness `15ad4a83…` | First attempt interrupted at junction cleanup (§4); rerun `harness-present` PASS | n/a | NOT DETERMINED | Observations unreviewed |
| C10 | Normal uninstall, both shortcuts removed | Guest harness; runner guarded uninstall | `uninstall` PASS ("0 payload files left") | n/a | NOT DETERMINED | Results unreviewed |
| C11 | Reinstall and second uninstall with unrelated data | Guest harness; runner reinstall | `harness-present` PASS; `reinstall` PASS | n/a | NOT DETERMINED | Observations unreviewed |
| C12 | Synthetic project/model/unrelated bytes kept | Guest harness; runner `post-harness-inventory` and `preservation` | All PASS | n/a | NOT DETERMINED | Results unreviewed |
| C13 | Malformed packet, traversal and output-collision guards | Repository tests and CI | Automated checks pass; not part of the VM run | n/a | Automated checks PASS; clean machine NOT RUN | None for this closure |
| C14 | Alternative `/DIR` refused by the real installer | Runner `C14` result | `C14` PASS: refused, no residue, exit code 7 recorded | n/a | NOT DETERMINED | Refusal message and residue checks unreviewed |
| C15 | SmartScreen/signing and distribution approval | n/a | n/a | n/a | **BLOCKED** | Legal blockers B1 and B4; no signing |
| C16 | Owner 30-minute smoke and formal Windows UAT | n/a | n/a | n/a | **NOT RUN** | Not in scope |
| Icons | One STI icon in title bar, taskbar, Start Menu, Start Menu folder, Settings › Apps (S5-UI-001) | Five runner screenshots in `STIEvidence-B` | `icons` **NEEDS REVIEW** (by design) | **Pending** visual review | NEEDS REVIEW | Screenshots not seen by any reviewer |

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

No assertion is known to have failed. The determinations stay NOT DETERMINED
because the evidence is unavailable, not because anything failed.

## 4. Junction cleanup fix (formal harness)

**Defect.** In Present mode the harness redirects the installed `legal` folder
to a synthetic external target through a junction, then removes the junction.
The main harness `b8db1272…3626` used `Remove-Item -LiteralPath $legal -Force`
for this. On Windows PowerShell 5.1, that command asks for confirmation to
recurse into a non-empty junction, and the prompt stopped the first Stage B
attempt. The prompt comes before any deletion. How it was answered is not
recorded, and the interrupted attempt has no protected snapshot.

**Fix.** The fix was made outside the repository and reviewed before Stage B
was rerun. It is now ported unchanged, and the repository file hash equals
`15ad4a83…`. The new `RemoveVerifiedJunction` works in this order:

1. Reads the link with `Get-Item -Force`.
2. Requires `LinkType` `Junction`, the reparse-point attribute and the expected
   target. If any differs it fails with "Unexpected link: stop and inspect
   manually.", without removing anything.
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
  Constrained Language Mode, where the harness would fail closed.

**Tests added** (`tests/tools/test_m10_validate_installer.py`): these run the
helper as defined in the harness, extracted from its syntax tree, on Windows
PowerShell 5.1:

- a verified junction over a non-empty nested target is removed without a
  prompt, and the target and held bytes are unchanged;
- a junction to a different target, a plain non-empty directory and a missing
  link are each refused, and nothing is removed;
- a static check that the redirect cleanup calls the helper, never
  `Remove-Item` on the link, and verifies before removing.

The behavioural tests fail against the main harness and pass against the fix.
The junction tests are Windows-only and skip on the Linux CI.

## 5. Script-policy exception (Policy A)

M10-C says "there is no automatic logon command or execution-policy bypass".
That wording is unchanged.

**Exception granted.** For this S5 run only, the owner authorized one bounded
exception (recorded privately on the host):

- each Stage launcher first verifies the frozen input package;
- it then starts exactly one child Windows PowerShell process with
  `-NoProfile -ExecutionPolicy Bypass -File Run-S5.ps1`;
- no machine or user policy is changed.

**Not authorized:**

- entering passwords;
- changing VMware security settings;
- connecting the guest to a network;
- removing the human-witness requirement.

**Trust anchor.** The launcher cannot authenticate itself through a manifest
that it executes. Trust comes from the independent ISO hash the owner checks
(§1).

**Governance.** M10-C keeps its rule. A future clean-machine run needs its own
owner authorization, and this exception does not carry over.

## 6. Release-1 gate decision packet (unsigned)

**Recommended decision: CONDITIONAL.**

**Engineering closure is complete:**

- the candidate is pinned;
- the formal harness matches what ran;
- the stages ran end to end on isolated snapshots;
- the owner reported no failing assertion.

**Conditions before S5 is recorded as PASS:**

1. Review of a privacy-checked export of both `observations.json` files, both
   `baseline.json` and `summary.json` files and the `EVIDENCE-SHA256.txt` chain
   (§7). The review
   decides H2-A, C02–C12 and C14.
2. Owner visual review of the five icon screenshots (S5-UI-001).
3. The owner's signed C07 witness under the limited definition.

If the evidence review finds any violated assertion, that item becomes FAIL and
the gate becomes NOT DETERMINED until it is resolved.

**Independent of this gate:**

- distribution stays prohibited, because B1 and B4 are open and C15 is BLOCKED;
- C16 and formal UAT remain NOT RUN.

| Owner field | Value |
| --- | --- |
| Release-1 gate decision | _unsigned_ |
| C07 witness | _unsigned_ |
| Icon visual review | _unsigned_ |
| Evidence export reviewed | _not received_ |

## 7. Minimal evidence request (one time)

Do this once, from the existing `S5-StageB-Evidence` snapshot and then the
`S5-StageA-Evidence` snapshot. No reinstall, rebuild or model download is
needed.

1. Copy these items into one new, empty, private host folder:
   - `C:\STIValidation-X\observations.json`;
   - the whole `C:\STIEvidence-X` folder.
2. Use a channel the owner approves, for example a temporary shared folder that
   points only at that empty folder and is removed afterwards. Do not enable a
   broad writable share.

The screenshots may show account details, so they are reviewed privately on the
host and never committed. Only a redacted summary would enter the repository.

## 8. Not done

- No change to the product, the installer build, the receipt, the frozen
  candidate or the ISOs.
- No new Windows acceptance run.
- No guest access.
- No merge, signature or publication.
