# M10-C — Windows installer engineering and clean-machine validation

## State and boundaries

The bounded internal installer workflow is established on `main`. Development-host
installation observations PASS; **clean-machine acceptance remains NOT RUN**.
This is installer engineering completion, not completion of the clean-machine,
legal, signing, distribution or release gates. M10-B **B1–B6 remain BLOCKED**.
M9.2–M9.4 remain DEFERRED; Q5 still prohibits unsupported model-capability claims.
M7's CONDITIONAL exit and M8's open risk dispositions are unchanged. The optional
owner 30-minute packaged-app smoke remains planned **NOT RUN**. No binaries are
published and internal tests do not authorize distribution.

## Decision and provenance

Retain the M7/M10-A Windows x64 PyInstaller onedir route and the complete M10-B
license/source packet. Inno Setup **6.7.3** provides a small, declarative per-user
installer and an installation-log-based uninstaller. This pins the stable 6-series
tool used here rather than migrating the approved runtime architecture.
See the [upstream tool](https://jrsoftware.org/isinfo.php),
[versioned release](https://github.com/jrsoftware/issrc/releases/tag/is-6_7_3),
[verification guidance](https://jrsoftware.org/isdl-verify.php),
[per-user privilege contract](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm)
and [uninstall deletion semantics](https://jrsoftware.org/ishelp/topic_uninstalldeletesection.htm).

`tools/m10/installer-toolchain.json` pins the download, compiler and installed
license hashes. The actual downloaded tool had valid upstream Authenticode and
passed `gh release verify-asset` against the explicit 6.7.3 release tag. The
compiler is local build tooling, not a new product dependency. Its license text
is included unchanged in wording, normalized to LF for portable verification.
This attribution does not clear M10-B's unresolved native-component obligations.
The STI installer itself is **unsigned**, with no invented signing credentials.

## Reproducible local recipe

Prerequisites: Windows x64, Python 3.11+, locally authorized Inno Setup 6.7.3,
and the verified complete M10-B packet. No command downloads models or tools.
Use a new local output outside the checkout, or under ignored `_local/`; keep
all compiled output, full receipts and compiler logs private. Never publish them.

```powershell
python tools/m10/installer.py --bundle X:\STI\verified-onedir `
  --output X:\STI\installer-build --iscc X:\STI\inno-6.7.3\ISCC.exe
```

`--prepare-only` checks/stages the packet and produces the script without claiming
a compiled installer; this is the portable CI path. Compilation verifies the
pinned compiler, full input inventory and all output payload hashes. A receipt
binds the original frozen application, inventory, generator, template, notice,
tool and installer hashes. Existing outputs, incomplete/tampered packets,
traversing source names, links/reparse paths and bundled model/database files
are refused. The workflow is repeatable with traceable inputs; a byte-identical
installer across runs is **not** asserted (compiler timestamps may differ).

The observed build used frozen application `c93191ee4d0677f7e78a99fca8b89460b503e7f5`
and input inventory SHA-256
`896f53e8337b5208bd714df369f8eb07a9471c69c2f202cf172921083efda607`.
The 5,265-file existing packet is preserved; two installer-owned notice/marker
files are added. Sanitized build and host receipts are in
[`evidence/m10-c`](evidence/m10-c). Earlier local prototype builds were not
installed and are not the validation candidate.

## Installation and removal contract

- Fixed destination: `%LOCALAPPDATA%\Programs\Social Text Intelligence`.
  Alternative `/DIR` targets are rejected; no administrator elevation is needed.
- Per-user Start Menu links launch `sti-desktop.exe` with its installation
  working directory and expose the `legal` folder. Installation does not launch
  the app automatically or close existing user applications.
- User projects/models remain in the separate application-data namespace;
  model weights stay external and downloads require the existing explicit
  authorization. The installer performs no downloads.
- Explicit file entries are logged for removal. There is no `[UninstallDelete]`,
  recursive wildcard cleanup or user-controlled deletion directory. Unrelated
  files cause their nonempty directories to remain after uninstall.
- Install checks fixed path, collisions and ancestor reparse points. Existing
  payload replacement requires the matching per-user uninstall registration,
  uninstaller and managed marker. Uninstall checks all managed payload ancestors
  and shortcut locations for reparse points before logged removal.
- Guards are bounded safety checks, not a claim to defeat concurrent malicious
  filesystem changes. Unknown residual files are preserved; manual cleanup must
  never substitute an unguarded recursive delete.

The original M10-B inventory covers the original packet. Installed verification
checks that packet plus the two installer payload files through the new receipt;
Inno's own uninstall files are expected additions. No original M10-B integrity
requirement is weakened to accept arbitrary extras.

## Repeatable isolated Windows validation

Prefer a new disposable Windows x64 VM snapshot with no Python, Qt, model cache,
STI installation or profile data. Record the OS/architecture, snapshot identity
and prerequisites privately. Disconnect networking, disable shared clipboard
and printers, and share only the installer, receipt and validation script via
read-only media. Never share projects, model caches or the full development repo.
Do not bypass SmartScreen, change security policy or supply signing credentials.
If an OS security barrier blocks the test, record BLOCKED/NOT RUN and stop.

On a supported host, a local Windows Sandbox configuration may use these
documented settings; change only the generic host input directory:

```xml
<Configuration>
  <Networking>Disable</Networking>
  <ClipboardRedirection>Disable</ClipboardRedirection>
  <PrinterRedirection>Disable</PrinterRedirection>
  <MappedFolders><MappedFolder>
    <HostFolder>X:\STI\validation-input</HostFolder>
    <SandboxFolder>C:\STIInput</SandboxFolder>
    <ReadOnly>true</ReadOnly>
  </MappedFolder></MappedFolders>
</Configuration>
```

See [Microsoft's configuration contract](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file).
There is no automatic logon command or execution-policy bypass. A human must
verify the fresh isolated baseline before creating the following guest marker
and running the reviewed local script under the guest's permitted script policy:

```powershell
'STI M10-C disposable Windows validation v1' | Set-Content C:\STI-M10C-VM.txt
& C:\STIInput\validate_installer.ps1 `
  -Installer C:\STIInput\STI-0.10.0-internal-x64.exe `
  -Receipt C:\STIInput\installer-receipt.json `
  -Output C:\STIValidation -EnvironmentKind DisposableVM
```

The marker expresses operator intent, not proof of a clean baseline. The harness
refuses existing application/profile/Start Menu namespaces and existing output.
It isolates PATH and offline model-cache settings, checks the installed hashes,
starts the native window, verifies runtime/license/synthetic project smoke,
tests redirected-directory uninstall refusal, then uninstalls, reinstalls and
uninstalls again. Only newly created synthetic byte sentinels are used. These
are not valid model weights, actual user projects or formal UAT results.

Keep raw logs and machine screenshots private in the guest. Independently inspect
results and manually observe absent-model analysis being blocked with a clear
readiness/provisioning message; opening download confirmation must not initiate a
download, and cancel must leave models absent. Do not approve a download for this
test. Record exact observed outcomes or NOT RUN. Before destroying the VM,
retain a privacy-reviewed summary through an approved transfer channel; do not
enable broad writable shares or publish private machine evidence.

## Actual observations and acceptance matrix

Observed current Windows development host: initially absent STI install/profile
and Start Menu namespaces; system-only PATH; offline cache. This environment
still has host software and is **not a clean machine**. Windows Home had no
available Windows Sandbox/Hyper-V VM; no features or VM images were installed.
The Computer Use tool could not initialize after reset/retry because its sandbox
could not represent an environment path. This did not validate UI interaction.

| ID | Check | Development host | Fresh VM / clean machine |
| --- | --- | --- | --- |
| C01 | Verified artifact builds into unsigned installer | PASS | NOT RUN |
| C02 | Fixed per-user path and installed payload hashes | PASS | NOT RUN |
| C03 | Start Menu target, working directory, license link | PASS | NOT RUN |
| C04 | First native application window and safe close | PASS | NOT RUN |
| C05 | Native dependency readiness without loading models | PASS | NOT RUN |
| C06 | Model weights absent; synthetic project reopen | PASS | NOT RUN |
| C07 | Actual missing-model analysis UI and download-cancel interaction | NOT RUN | NOT RUN |
| C08 | License/source material present, removed on uninstall | PASS | NOT RUN |
| C09 | Reparse redirect refuses uninstall; external sentinel retained | PASS | NOT RUN |
| C10 | Normal uninstall and both shortcuts removed | PASS | NOT RUN |
| C11 | Reinstall and second uninstall with residual unrelated data | PASS | NOT RUN |
| C12 | Synthetic project/model/unrelated bytes retained | PASS | NOT RUN |
| C13 | Incomplete/malformed packet, traversal and output-collision guards | Automated checks | NOT RUN |
| C14 | Alternative `/DIR` refusal in actual installer | NOT RUN | NOT RUN |
| C15 | SmartScreen/signing and external distribution approval | NOT RUN / BLOCKED | NOT RUN / BLOCKED |
| C16 | Owner optional 30-minute smoke / formal Windows UAT | NOT RUN | NOT RUN |

Automated portable tests and Linux CI establish generator/schema regressions;
they do not establish Windows installation, accessibility, VM acceptance or
legal compliance. Development-host preservation proves the tested sentinel
bytes survive; it is not a claim that every possible user dataset was tested.

## Remaining action

Execute the clean isolated matrix and missing-model/download-cancel UI checks
on an available authorized VM; preserve unsuccessful/unavailable results.
Resolve **B1–B6** before any legal/distribution clearance. Signing/SmartScreen,
owner smoke, formal UAT/accessibility and release decisions remain open. No
M9 evidence requirement or M7/M8 risk has been waived.
