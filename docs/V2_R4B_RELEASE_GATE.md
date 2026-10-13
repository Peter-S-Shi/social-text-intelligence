# V2 Release-4B — Private release candidate and two-phase publication gate

Status: **engineering complete; B1 stays OPEN; `distribution_permitted` stays
false.** No application tag, GitHub Release or installer publication was made.

## 1. The circular dependency

Release-4A left one B1 prerequisite: the page that offers the installer must
link to the public source release, and that link must be verified. Two facts
make the obvious order impossible:

- the page exists publicly only after the release is published;
- an immutable release cannot have its assets replaced afterwards.

So the installer cannot wait for a verified page, and no packet baked into the
installer can state the result. The gate separates what can be proven before
publication from what only publication can show.

## 2. The two phases

| Phase | Evidence | Can it report B1 operational closure? |
| --- | --- | --- |
| Pre-publication (draft) | The unpublished draft matches the plan: tag, target revision, exact asset set and digests, body hash, and the body links the source release | **No.** It reports only `ready_for_owner_approval` |
| Owner approval | The Owner reviews the draft check and approves in chat. No file records or stands in for it | — |
| Post-publication (public) | Without credentials: the public API shows a non-draft, immutable release with the same plan; the source release is still the one `SOURCE_HOSTING.json` pins; the public page links it | **Yes**, and only for that release |

`tools/m10/release_gate.py` does this, and each receipt holds the digests of the
live responses it came from, so a reviewer can rerun the check:

| Command | Purpose |
| --- | --- |
| `candidate` | A sanitized manifest from a private installer receipt: filename, size, SHA-256, application revision, source release. No path leaves the host. Status `awaiting-owner-decisions` |
| `render` | The release body from `distribution/release-source-page.md`. It needs the Owner's version and tag, refuses while any placeholder is unfilled, and refuses a tag that collides with the source release |
| `verify --phase draft` | Authenticated check of the draft against the plan |
| `verify --phase public` | Unauthenticated check of the published release, the source release and the page |

The checks are fail-closed and named: wrong tag, a target that is not the
candidate revision, a prerelease, a changed body, a missing source link, an
extra or altered asset, a non-immutable public release, an altered or
unlocked source release, a page without the link. Each fails its own check, and
any failure blocks both `ready_for_owner_approval` and closure.

**What closure means.** B1's operational prerequisite is met for that release
by a passing public phase. The packet inside the installer stays `B1` by design:
it was fixed before publication and cannot assert the outcome. The Owner Gate
reads the public receipt. Nothing in the gate sets `distribution_permitted`.

## 3. Packaged text no longer goes stale

An immutable installer cannot carry a claim that later becomes false. Release-4A
wrote "no installer page is live" into the packet. Now the hosting record, the
B1 wording, `SOURCE_ACCESS.md`, `QT_NOTICE.md` and the installer notice say only
that the sources are in the installer and in the immutable source release, and
that each release page offering the installer links to it. They assert neither
that such a page exists nor that it does not. The gate, not the packet, checks
the link.

## 4. The release-facing installer path

`installer.py --profile candidate` is new. `--profile internal` (the default)
is unchanged apart from reading the version from `pyproject.toml`; its name
(`STI-0.10.0-internal-x64.exe`), its notice and its warning are as before.

| | internal | candidate |
| --- | --- | --- |
| Application name | "Social Text Intelligence (internal engineering)" | "Social Text Intelligence" |
| File name | `STI-<version>-internal-x64.exe` | `STI-<version>-x64-setup.exe` |
| Notice shown | `INSTALLER_NOTICE.txt` (not approved for distribution) | `RELEASE_NOTICE.txt`: licence facts and system requirements, no approval or status claim |
| Extra gates | — | blockers exactly `[B1]` and no other packet blocker; valid LD1–LD6 record; valid source hosting record; no open B4 item; the packet's revision equals the clean, committed `HEAD` |

Both profiles keep the existing protections: byte and set verification of the
packet, model and user-data exclusion, no Microsoft runtime, link and
reparse-point refusal, and the pinned Inno Setup. A candidate receipt records
`release_candidate: true`, `published: false`, the version and the file name.

The version comes from `pyproject.toml` (`0.10.0`). **It was not changed and no
tag was chosen.** The gate refuses a version that differs from the installer's,
so a different version needs a rebuild.

## 5. Private candidate

Built from the committed revision `33e0f6c` with official CPython 3.13.16. It
stays in private storage; nothing was uploaded.

| Item | Result |
| --- | --- |
| Frozen checks | `--verify-runtime`, `--smoke` (including `application_icon: true`) and `--license-info` exit 0; the opt-in frozen pytest passes 3 |
| Packet | Valid; blockers exactly `[B1]`; B4 remaining empty; LD record and hosting record valid |
| Installer | `STI-0.10.0-x64-setup.exe`, 726,695,345 bytes, SHA-256 `5c5bde13…6721`; receipt: [`evidence/r4b/r4b-candidate-receipt.json`](evidence/r4b/r4b-candidate-receipt.json) |
| Receipt check | The harness function `Get-StiReceiptFacts` accepts it |
| Manifest | `release_gate.py candidate` produced it; status `awaiting-owner-decisions` |
| Clean-machine run | Not repeated. The payload differs from the VMware-tested candidate only by notice and name changes and the packaged text, not by behaviour |

This candidate proves the path. The release build must be repeated on the final
tagged commit.

## 6. Remaining release-time actions and decisions

Owner decisions (surfaced, not made):

1. The application version. `0.10.0` is the current value.
2. The application tag, which must not start with `sources-`.

Then, in order:

1. Rebuild the installer with the candidate profile on the final commit, produce
   the manifest, and render the body.
2. Create a **draft** release with that tag, the installer as the only asset, and
   the rendered body (the Owner authorizes this step).
3. Run `verify --phase draft`. It must pass.
4. The Owner approves, with the Owner Release Gate: C15 (signing and
   SmartScreen) BLOCKED, C16 NOT RUN, and the two accepted S5 icon evidence gaps.
5. Publish. Run `verify --phase public`. Only a passing run reports B1's
   operational closure; record its receipt.
6. If a later release is wanted, the whole sequence repeats; an immutable release
   is never edited.

Unchanged: M9.2–M9.4 DEFERRED; formal Windows UAT and accessibility; B5.

## 7. Validation

| Check | Result |
| --- | --- |
| Targeted tests | `tests/tools` and lifecycle: 318 passed, 3 opt-in skipped. New: gate manifest (12 inconsistent receipts), body rendering and the unfilled template, a correct draft, nine wrong drafts, an extra asset, public closure, a draft or non-immutable response failing the public phase, a missing page link, an altered or unlocked source release; and the candidate profile gate (ten failing packets, an uncommitted tree, the CLI refusal) |
| Local full suite (Windows, Python 3.12) | 1,484 passed, 7 opt-in skipped; Ruff and strict MyPy pass |
| PR CI | One run on the final head; the result is recorded in the PR |

## 8. Not done

No application tag, GitHub Release (draft or public), installer publication,
version or tag decision, merge, new hosting service, VMware rerun, product or
model change, M9 work or licensing research. LD1–LD6 and `B1_OWNER_DECISION.json`
are unchanged.
