# M8 Track A — Technical Product Hardening: evidence ledger

Track A of M8 turns the open M7 risks into bounded, evidence-driven hardening. It
adds no product feature and no new dependency. Track B (UI fidelity) is separate and
is not covered here. This ledger lets another agent continue without chat history.

**Status:** Track A implementation is complete on branch
`milestone/m8a-technical-hardening`. Every item has an explicit disposition below;
nothing is claimed beyond its evidence. **M8 as a whole is not complete** (Track B and
the owner's visual review are pending), and M9 and M10 are not started.

Dispositions: **FIXED** (change plus a regression that failed first), **ACCEPTED**
(understood, left as is, reason given), **NOT REPRODUCED** (stress found nothing),
**NOT VERIFIED** (could not be tested in this environment), **OWNER DECISION**
(a trade-off the owner must settle).

## 1. Environment and method

| Item | Value |
| --- | --- |
| Base | `origin/main` at `53a5c27` (PR #49, M7 CONDITIONAL exit) |
| Machine | Windows 11 Home 10.0.26200, Intel Core i7-12700H, 15.7 GB RAM, local NVMe SSD (the M7 machine) |
| Python | 3.12 in the project `.venv`; 3.11 and 3.14 python.org interpreters were used only for stdlib behaviour probes |
| Models | The two pinned revisions, imported from a local Hugging Face cache into a disposable root (the app's own import and hash check). The normal test suite uses synthetic models and fake gateways only |
| Data | Synthetic text only. All roots are disposable folders under an ignored `_local/` directory; the real `%LOCALAPPDATA%` application folder is never touched |
| Raw outputs | `_local/m8a/` (ignored, not committed): per-round JSON lines, anomaly artefacts, probe reports. Only summaries are in this document |

Method: each item was first reduced to a failing regression where a defect was
demonstrable (red, then green), checked against the existing suites, and measured with
the scripts in `tools/m8/` (below). Two-process tests use a small peer script that is
steered through files and can be hard-killed (`tests/cross_process/`).

## 2. Summary

| Item | Topic | Disposition |
| --- | --- | --- |
| A1 | Cross-process exclusion (analysis of one project; shared models folder) | **FIXED** |
| A2 | The unreplicated "project not available" event | **NOT REPRODUCED** in 128 stress rounds; two real adjacent hazards found and **FIXED**; root cause of the M7 event **not proven** |
| A3 | Cost of re-hashing the weights at first analysis | **OWNER DECISION** (measured; nothing added) |
| A4 | Disk-full, read-only, locked and sync-like conditions | **FIXED** (accurate errors, no partial commit); real OneDrive-style sync **NOT VERIFIED** |
| A5 | Cold start and low memory | UI responsiveness **verified**; memory floor **measured** with a native-crash hazard (**OWNER DECISION**); cold-cache start and physical low-RAM **NOT VERIFIED** |
| A6 | Import-rejected versus analysis-failed counts | **FIXED** in the project summary; Insights wording **ACCEPTED** |

## 3. A1 — Cross-process exclusion

**Finding (M7).** Two instances could analyse the same project (the loser spent its
whole inference for a `stale` result), delete a project under an analysing instance,
and import into the same models folder (the loser failed with a generic
`storage_failed`, and which one lost was unpredictable). Multi-instance stays allowed
(owner decision); the fix is scoped exclusion, not a global guard.

**Root cause of the model-import error.** Both importers staged into the same
`<name>.import` file and then replaced the same target; on Windows the second open or
`os.replace` is a sharing violation, mapped to `storage_failed`.

**Change.**

- Port `application/exclusion.py` (`ProcessLocks`, `ProcessLock`); adapter
  `infrastructure/process_locks.py`. One small lock file per scope under
  `<root>/locks/`, taken with `msvcrt.locking` (Windows) or `fcntl.flock` (POSIX).
  The lock is **tried, never waited on**, so a refused caller answers at once, and it
  is an OS lock on an open handle, so it **disappears with the process however it
  ends**; no file content or existence ever means "held". Scope names are validated
  (`[a-z0-9._-]`), so a scope can never name a path. On POSIX the acquire loop also
  checks that the locked inode is still the file on disk (a deleted lock file cannot
  yield two holders).
- Scope `project-<id>`: held for the whole analysis lease (`begin_analysis` until
  `complete_analysis`/`cancel_analysis`), by `delete`, and by `create_project` while
  the file is half-written. A second instance gets `ProjectBusyElsewhere` ->
  `ProjectBusyError` (code `project_busy`) with the message "This project is in use in
  another window of the app, for example being analysed there. Wait for it to finish
  there, or close that window, then try again. Nothing was changed." The in-process
  message ("cancel it first") is unchanged.
- Scope `models`: held by download, import, Verify and discard-partials
  (`LocalModelProvisioner._exclusive`, together with the in-process flag). The loser
  gets the new code `provisioning_elsewhere` with a fixed recovery message; the desktop
  shows "Another window is changing the models folder" with Try again and OK. The
  quick `status()` stays read-only and unblocked.
- Unchanged by design: leases stay process-local, the per-project revision still makes
  a stale lease fail, an analysed project is never re-analysed, cancellation commits
  nothing, the AI record is immutable. Reading is never blocked.

**Evidence.** `tests/cross_process/` (15 tests, subprocess peers, no real models):
exclusive per scope; release idempotent; scope names cannot name a path; a second
instance cannot start a duplicate analysis (0 inference calls) and the project is
afterwards analysed and recoverable; exclusion is scoped to the same project and does
not block listing/reading or another project; delete is refused while another instance
analyses; **a hard-killed analyser or importer leaves no stale lock**; a refused
analysis leaves no hold in the refusing process; cancellation still commits nothing
and frees the project; model import/Verify/download/discard are refused while another
instance imports; the production wiring (`local_model_provisioner`) takes the lock.
Stress on the final head (section 4): 64 rounds, always exactly one `committed` and one
immediate busy refusal, 0 anomalies.

**Behaviour changes to note.** (1) Deleting a project that another instance is
analysing is now refused (M7 scenario B let the delete win and wasted the analysis);
`tests/persistence/test_project_workflow.py` was updated and a second test keeps the
"a file removed behind the app's back is never resurrected" guarantee. (2) The simulated
crash in `test_a_crash_during_analysis_leaves_a_usable_project` now releases the OS
lock explicitly because an in-process "crash" cannot drop it; the real kill is covered
in `tests/cross_process/`. (3) A freshly killed holder can look held for a few
milliseconds on Windows until the kernel closes its handles; the tests retry for that.

**Limits (ACCEPTED).** `mutate` (review saves, notes, column choice) takes no
cross-process hold: state already separates it from analysis (analysis needs a READY,
unanalysed project; review and notes need an analysed one; the only write on a ready
project is the column choice, which a ready project refuses), and the revision check
still protects the rest, so no case was found where it would waste an analysis. Analysis that is loading weights while another instance
imports the same files is not excluded: import only replaces a file that fails its
hash, and a replace of an open file on Windows fails with `storage_failed`
(recoverable). The POSIX (`flock`) branch is exercised only by the Linux CI job, not on
the development machine; the product claims Windows only. Lock files for existing
projects stay in `<root>/locks/` until the project is deleted (empty files named by
project id).

**Disposition: FIXED.**

## 4. A2 — The unreplicated "project not available" event

**Finding (M7).** One run of an earlier probe version reported both instances `stale`
and then "project no longer available" although the file existed and later read as
analysed; its report file was lost. Suspects: `_summary` listing racing a commit or WAL
checkpoint, transient SQLite busy/locked mapped to "not found", `list_projects`
skipping a file mid-write.

**Method.** `tools/m8/stress_two_instances.py`: per round, a new 300-row project in one
accumulating, persisted root (nothing deleted or overwritten between rounds); two
analyser processes started 0, 0.05, 0.3, 1 or 2 s apart (random, seeded); a third
observer process polling `list_projects` and `open_project` every 2 ms; optional CPU
burner processes (one per logical CPU); on any anomaly the file state (names, sizes,
mtimes), sidecars, exceptions and a byte-exact copy of the project files are saved.
Deterministic providers with a 15 ms per-row delay (so a round lasts about 5 s); real
models were not used because the suspects are in the storage and listing paths, not in
inference.

| Run | Code under test | Rounds | Observer polls | Anomalies |
| --- | --- | --- | --- | --- |
| baseline, idle | `53a5c27` | 32 | 3,970 | 0 (32 x committed + stale) |
| baseline, CPU load | `53a5c27` | 32 | 3,158 | 0 (32 x committed + stale; run time up to 9.6 s) |
| final, idle | this branch | 32 | 4,033 | 0 (32 x committed + busy refusal) |
| final, CPU load | this branch | 32 | 3,101 | 0 (32 x committed + busy refusal) |

No project was ever missing, unreadable or half-written; no final state other than
`analyzed` with 300 rows; no leftover `-wal`/`-shm` files.

**Distinguishing nondeterminism from data loss.** No data loss was observed anywhere.
The M7 signature (both stale, then not found) is exactly what a project file that is
absent at that moment produces: `complete_analysis` returns False when the file is
missing and `get` returns None (regression
`test_a_project_file_removed_mid_analysis_is_not_resurrected`). So at that instant the
file was not visible. Why is **not proven**. Leading hypothesis: the earlier probe
version removed the projects folder between scenarios while an earlier scenario's
instance was still running; the lost report prevents confirming it. The remaining
hypothesis class is a transient file-system condition (scanner, indexer) that made the
file unreadable for a moment.

**Suspects and findings.**

| Suspect | Result |
| --- | --- |
| `_summary` listing racing a commit or WAL checkpoint | Not reproduced (14,262 observer polls during commits across the four runs); readers are not blocked by a writer holding the write lock (`test_readers_are_not_disturbed_by_a_writer_holding_the_write_lock`) |
| Transient busy/locked mapped to "not found" | Ruled out by reading: busy/locked is a `ProjectStorageError`, never `None`. Listing shows such a file as unreadable until it heals |
| `list_projects` skipping or mis-reporting a file mid-write | **Two real hazards found, FIXED test-first**: (a) `create_project` made an empty file visible, so another instance's listing showed a half-created project as *unreadable* (now the creating instance holds the project lock and a lister treats an unreadable-and-locked entry as "being created"); (b) a transient stat failure (sharing violation or access-denied while a scanner/sync client holds the file) crashed the listing with a raw `PermissionError` on Python 3.11/3.12, and on 3.13+ `Path.is_file` swallows every `OSError`, which would read as "project not found" (INFERRED from CPython behaviour; the project supports 3.13). Now only a definite `FileNotFoundError` means absent; any other failure is a storage error and the entry stays listed |

**Disposition: NOT REPRODUCED**; the event stays *unexplained*. The two hazards above
are FIXED (`tests/persistence/test_listing_visibility.py`). The M7 risk R-D3 should not
be closed as "explained"; it can be downgraded to "not reproduced in 128 rounds, with
adjacent hazards removed".

## 5. A3 — Cost of a first-analysis integrity check

**Contract kept.** `ModelProvisioning.status()` remains quick, hash-free and read-only
(`docs/MODEL_PROVISIONING.md`). Nothing was added.

**Measured** (`tools/m8/measure_integrity_cost.py`, real models, warm cache unless
stated; 12 files, 1,004,464,932 bytes):

| Check | Cost |
| --- | --- |
| Full SHA-256 Verify (the app's existing action) | 0.92 to 1.07 s over 6 runs (median 0.92 s); import including copy and hash 1.1 s |
| SHA-256 throughput on the largest file | 914 to 1,025 MiB/s |
| Read straight from disk (no file cache, `FILE_FLAG_NO_BUFFERING`) and hash | 0.9 to 1.3 s (this NVMe is faster than the hash; a slower disk is NOT VERIFIED) |
| Size plus modified-time fingerprint of the 12 files | 0.7 ms |
| First analysis (model load, M7 and A5) | 5 to 11 s |

A one-byte flip in an installed weights file: quick status stayed `ready`; the full
Verify reported it; a size-plus-mtime fingerprint also noticed it here because writing
changes the modified time (it would miss silent media corruption or a restored mtime).

**Trade-off.** A full re-hash once per session at first analysis costs about 1 s on this
machine (an estimated 10 to 20 percent of the first-analysis time; several seconds on a
slower CPU or disk, NOT VERIFIED) and needs no new persisted state: it is the existing
Verify run before the model load, on the worker thread with progress, and a mismatch is
the existing durable finding that already blocks analysis. A fingerprint check is nearly
free but needs a new persisted baseline written at install/Verify time, which changes
the approved "read-only status" contract and catches less.

**Recommendation (decision needed).** Option B: run the existing Verify once per
process before the first model load, and refuse with the existing corruption message on a
mismatch. Alternatives: A) accept the window and keep it documented (current state);
C) size-plus-mtime fingerprint (changes the contract). Not implemented because B alters
the first-analysis experience and the H2 interplay, which is the owner's call.

**Disposition: OWNER DECISION.**

## 6. A4 — Disk-full, read-only, locked and sync-like conditions

**Finding (before).** Every fault surfaced as the generic `storage_failure` ("could not
complete the operation"), and deleting a read-only project said "Close other programs".
Data was never damaged.

**Change.** `sqlite_support.storage_guarded` now classifies by SQLite result code and by
OS error: `storage_full` (SQLITE_FULL, ENOSPC, Windows disk-full), `storage_read_only`
(SQLITE_READONLY, EROFS/EACCES/EPERM), `storage_locked` (SQLITE_CANTOPEN, sharing or lock
violation), `project_busy` (SQLITE_BUSY/LOCKED, as before), otherwise `storage_failure`
with advice. Messages are fixed, content-free, say what to do and that nothing was
changed. The desktop shows a matching title. Model download/import gained
`storage_full` ("not enough free disk space; finished files and a partial download are
kept"); other model-folder write faults (read-only, locked) keep the generic
`storage_failed`, whose message already says to free space or check permissions
(ACCEPTED). Windows reports sharing violations with errno EACCES, so the Windows error
is read before the errno (found in review; regression added). `list_projects` no longer lets a raw `OSError` escape. Delete's failure message
now also mentions the read-only setting.

**Real versus emulated.**

| Condition | How produced | Result |
| --- | --- | --- |
| Project file held open by another program, no sharing | REAL (Win32 `CreateFileW`, share mode 0) | open/analyse: `storage_locked` with advice; listing keeps the project (unreadable until released); delete: `delete_failed`; fully usable after release |
| File held with read sharing only (like a backup reader) | REAL | reading works; analyse: `storage_read_only` |
| Read-only file attribute | REAL | reading works; commit: `storage_read_only`; delete refused with advice; recovered after clearing the attribute |
| Data root is a file where a folder is needed | REAL | import: `storage_failure` with advice; the file untouched; list empty |
| SQLite database full | REAL engine error via `PRAGMA max_page_count` (no disk filled) | analysis commit: `storage_full`, project unchanged (no partial result), lease released and re-analysis works; import: `storage_full`, no project or file left |
| OS-level ENOSPC | EMULATED (injected at the write seams) | model download: `storage_full`, partial file kept and the retry resumes; model import: no staged leftovers; install: nothing partial, existing models stay `ready` |
| Read-only folder (permissions) | EMULATED (errno mapping unit tests); not produced with ACLs, which would change security settings | mapped to `storage_read_only` |
| Sync-managed (OneDrive-like) folder: placeholders, conflict copies, background locks | NOT VERIFIED | the default location is per-user **non-roaming LocalAppData**, which is not a synced folder by default; a held-open file is covered by the REAL lock rows above; conflict copies have non-managed names and are ignored |

**Disposition: FIXED** for the rows above. Sync-managed folders: **NOT VERIFIED**, M4's
"unverified and unclaimed" statement stands.

## 7. A5 — Cold start and low memory

`tools/m8/probe_memory_ui.py` (real models, disposable root, Windows).

**UI stays responsive during the first model load.** Real Qt event loop, real job
runner (worker thread), real `AnalysisGate` and both models, a 10 ms heartbeat on the UI
thread: offscreen x2 and the native `windows` platform x1 gave a worst heartbeat gap of
110, 125 and 152 ms, with 1 or 2 gaps above 100 ms and none above 500 ms, over 5 to 9 s
loads. (Offscreen versus native only changes the paint path; both exercised the same
event loop.) **Verified.**

**Memory.** Peak working set 1.1 to 1.3 GB, peak commit 2.4 to 2.6 GB, private bytes
about 2.0 to 2.2 GB after both models load. A per-process committed-memory limit (Windows
job object; an emulation of a smaller memory budget, not of smaller physical RAM) gave,
repeatably:

| Committed-memory limit | Result |
| --- | --- |
| unlimited, 3,072, 2,560 and 2,432 MB | analysis works |
| 2,304, 2,176 and 2,048 MB | **the process crashes natively (exit `0xC0000005`)**, no message |
| 1,920, 1,792 and 1,536 MB | the app shows its clean `model_load_failed` error (the emotion model could not be loaded) |

So the app needs about 2.5 GB of available commit for both models, and in a band just
below that a native allocation failure inside the model runtime ends the whole
process (a desktop user would lose an unsaved review draft). This is a hazard, not a
defect with a bounded fix: it lives inside the runtime. **Recommendation (decision
needed, can be M10 documentation):** state a minimum requirement (for example 8 GB of
RAM) and consider a pre-flight check of available commit before the first model load
that shows a clear message instead of risking the crash. Not implemented (new behaviour).

**NOT VERIFIED.** Cold-cache start-up after a reboot (needs privileges to drop the file
cache; the data-file cold read was approximated in A3 only); behaviour under real
physical memory pressure on an 8 GB or 4 GB machine (paging, other programs); slow disks
(HDD, SATA, network drive); window-shown time on a clean machine.

**Disposition:** UI responsiveness verified; memory floor measured (**OWNER DECISION**
on the pre-flight check/requirement); the rest **NOT VERIFIED**.

## 8. A6 — Rejected versus failed row counts

**Finding.** A batch records an outcome for every row; an import-rejected row has no
report, so `BatchAggregates.failed_count` counts it too. `describe()` passed that
straight through as `ProjectDetails.failed_rows`, so the Project summary read "Analysed
200 rows · 1 rows failed" for a file whose only problem was one empty row rejected at
import, while the Results page (which subtracts rejected rows) read "200 analysed · 0
failed · 1 rejected at import". This is the M7 observation (`failed_rows = 1`).
`tests/persistence/test_project_workflow.py` had encoded the conflated number as
expected.

**Change.** `failed_rows` = analysis failures of valid rows (`failed_count` minus
`preview.invalid_count`), so analysed + failed = valid rows and rejected rows are only
`invalid_rows`; "1 rows failed" became "1 row failed". Regression: one rejected row
alone -> `(analysed 2, failed 0)`; one rejected and one analysis-failed row ->
`(2, 1)`; both count `analysed + failed == valid`.

**Checked and coherent.** Results page: tabs "All rows = Analysed + Not analysed",
subtitle "analysed · failed · rejected at import", failed card labelled "rows not
analysed" (includes rejected, as worded). Review: "N rows could not be analysed and
are not reviewable" (includes rejected, accurate). Export: rejected rows keep their
validation code with `status = error`.

**ACCEPTED (documented, not changed).** Insights says "N failed row(s) assigned to this
group" and counts every row without an AI result, including rejected rows; this is the
V1/service contract (`failed_count`, the exported `group_failed_count`) and the line
states such rows are never counted in a metric. Rewording would change an accepted M6
text and an export contract for a presentation nuance; flagged for the owner.

**Disposition: FIXED** (Project summary), Insights wording **ACCEPTED**.

## 9. M7 conditional-risk mapping

| Risk | Status after Track A |
| --- | --- |
| R-D1 integrity under concurrency, kill, delete | Still cleared; strengthened by the stress runs |
| R-D2 no single-instance guard; generic import-collision error | **Closed** for the stated scope (scoped exclusion plus actionable messages; evidence in section 3) |
| R-D3 unexplained transient "not available" | **Remains open as unexplained**: not reproduced in 128 rounds, two adjacent hazards removed |
| R-D4 disk-full, sync folder, antivirus lock untested | **Partly closed**: disk-full, read-only and locked-file behaviour probed and fixed; sync-managed folders NOT VERIFIED |
| R-I2 post-Verify weight corruption | Measured; **OWNER DECISION** (section 5) |
| R-S2 memory floor and cold start | Memory floor measured and a native-crash band found (OWNER DECISION); cold start and physical low-RAM NOT VERIFIED |
| failed_rows for rejected rows | **Closed** (FIXED) |
| R-L*, R-P* (LGPL, packaging) | Untouched; M10 |

## 10. Reproduction (Windows PowerShell, repository root)

```powershell
# one-off: the package sources of the code under test
$env:PYTHONPATH = "src"; $env:QT_QPA_PLATFORM = "offscreen"; $env:STI_REQUIRE_QT = "1"; $env:STI_REQUIRE_LANGID = "1"

# regressions
python -m pytest tests\cross_process tests\persistence\test_listing_visibility.py tests\persistence\test_storage_faults.py tests\provisioning\test_storage_full.py -q

# A2 stress (about 3 to 6 minutes per 32 rounds); add --load for CPU burners,
# --src <folder with the package sources> to test another revision
python tools\m8\stress_two_instances.py --root _local\m8\stress\root --out _local\m8\stress\out --rounds 32

# A3 (needs a local Hugging Face cache of the two pinned revisions)
python tools\m8\measure_integrity_cost.py --root _local\m8\a3\root --models-src model_cache

# A4 real file faults
python tools\m8\probe_storage_faults.py --root _local\m8\a4\root

# A5
python tools\m8\probe_memory_ui.py prepare --root _local\m8\a5\root --models-src model_cache
python tools\m8\probe_memory_ui.py limit --root _local\m8\a5\root --limits-mb 3072,2560,2304,2048,1792
$env:QT_QPA_PLATFORM = "offscreen"; python tools\m8\probe_memory_ui.py ui --root _local\m8\a5\root
```

## 11. Commits

| Commit | Content |
| --- | --- |
| `e9d8d8f` | A1 scoped cross-process exclusion |
| `5b87429` | A6 project summary counts |
| `f08028e` | A2 listing and creation hazards |
| `5fad79d` | A4 accurate storage-fault errors; stress and fault probes |
| `3c1e576` | A3/A5 probes; documentation of the new behaviour |
| `27c7d04` | This ledger |
| `01d8ec3` | Review repairs; **final behavioural head** (local full regression 1018 passed, 4 opt-in skipped; Ruff, strict MyPy, compileall, pip check; GitHub CI green on Python 3.11, 3.12, 3.13) |

The governance-only commit after `01d8ec3` is `[skip ci]` and changes documents and
lifecycle-wording assertions only. Independent Standards and Spec reviews ran on this
branch; their findings (Windows sharing violations were classed as read-only; a shared
disk-full helper; the `mutate`/models limits now disclosed here) were repaired in
`01d8ec3`.
