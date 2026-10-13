# V2 Release-4A — Public source access integration (B1 engineering)

Status: **B1 stays OPEN, narrowed to one release prerequisite: the installer
download page must link to the public source release, and that same-page link
must be verified.** B4 is not derived. `distribution_permitted` stays false.

This milestone changes no product behaviour and builds no installer. It records
Release-3 and teaches the packet checks to tell satisfied B1 conditions from
missing, inconsistent or substituted evidence.

> **Later (PR #77).** Release-4B replaced the packaged "not live" wording with neutral text and moved the same-page link check into a two-phase release gate. See [V2_R4B_RELEASE_GATE.md](V2_R4B_RELEASE_GATE.md). This record is kept as it stood at PR #76.

## 1. What is public (Release-3)

| Fact | Value |
| --- | --- |
| Release | <https://github.com/Peter-S-Shi/social-text-intelligence/releases/tag/sources-qt-6.11.2> |
| Contents | Source-access materials only. Not a Social Text Intelligence V2 release and no application binary |
| Tag, commit | `sources-qt-6.11.2`, pinned to `de247c5569f31f3a95c4c6249785e6e491622179` |
| Immutable | Yes (`immutable=true`) |
| Assets | 13: the five source archives, four Qt SBOMs, `qt-binary-provenance.json`, `source-manifest.json`, `QT_REPLACEMENT.md`, `SHA256SUMS` |
| Checks | All 13 downloaded from the public links; 12 verified against `SHA256SUMS`; `SHA256SUMS` hash equal to the upload; GitHub's release attestation verified for the release and for each asset; the API's SHA-256 per asset equal to the manifests |
| Presentation | GitHub displays the release as Latest. The owner accepted this presentation deviation; it is not revisited |

Receipt: [`evidence/r3/r3-source-release-receipt.json`](evidence/r3/r3-source-release-receipt.json).

## 2. Operational hosting record

`distribution/legal/SOURCE_HOSTING.json` (schema 1) ships in the packet.
`tools/m10/compliance.py` holds its approved content **exactly** (`SH_SCHEMA_1`).
It records the release above and the 13 asset hashes, and it states, in fixed
fields:

- `installer_download_page`: `not live`;
- `installer_page_source_link_verified`: `false`;
- `distribution_permitted`: `false`.

`source_hosting()` validates it against the evidence, not just its own text:

| Check | Fails when |
| --- | --- |
| Equals the approved schema 1 content | any field is missing, extra or changed (URL, tag, commit, immutability, installer-page claims, permission) |
| Archive hashes equal `source-manifest.json` | the manifest names a different archive than was hosted |
| SBOM hashes equal `qt-binary-provenance.json` | a different SBOM was hosted |
| Manifest and provenance file hashes equal the repository's | either file differs from the hosted one |
| `QT_REPLACEMENT.md` hash equals the packet's copy | the packet's guide differs from the hosted one |
| Record present and well-formed | missing, malformed or not schema version 1 |

## 3. B1 and B4 derivation

| Packet state | B1 |
| --- | --- |
| Qt binaries unverified | `B1_UNVERIFIED` |
| No valid owner engineering record | earlier wording; hosting cannot narrow it |
| No valid LD1–LD6 record | `B1_DECIDED`, naming the rejection; hosting cannot narrow it |
| LD1–LD6 valid, hosting record absent or not checked | `B1_ASSESSED` (public access prepared, not operational) |
| LD1–LD6 valid, hosting record rejected | `B1_ASSESSED`, naming the rejection |
| LD1–LD6 and hosting valid | `B1_HOSTED`: the release is public; the installer page and its verified same-page link remain |

**B1 is never removed.** No schema can record the installer page as live or its
link as verified, and `installer.py` still refuses a packet without B1. Closing
B1 needs a reviewed record of that verification (a new schema version and code
change), which is a release-time step.

`installer.py` does not trust the inventory's claim of valid hosting. It
re-reads `legal/SOURCE_HOSTING.json` from the packet and requires it to equal the
approved content and the recorded hash. A forged or stale claim refuses the
installer. A valid one sets the receipt's `public_source_hosting` release
condition to "source release published and recorded; the installer download page
does not link to it yet, and that same-page link is not verified". Without a
valid claim it stays "not operational".

**B4:** unchanged in effect. The Intel item stays closed only on LD3–LD6 and a
matching package, texts and notice (below).

## 4. Intel `NOTICE.md` content check

The earlier check only required `intel-openmp/NOTICE.md` to exist. The record
now pins its content: `provenance.json` carries `license.notice_sha256`, and
`intel_openmp_status` compares the notice's SHA-256. A changed or missing notice
keeps the B4 Intel item open. This reopens none of LD1–LD6; the notice text is
unchanged.

## 5. Notices that now name the release

`SOURCE_ACCESS.md`, `QT_NOTICE.md`, the in-app licence text and the installer
warning name the permanent release URL. They say the installer download page is
not live, and none calls B1 closed.
[`distribution/release-source-page.md`](../distribution/release-source-page.md)
becomes the template of that page, with the release location filled and the
installer-specific placeholders left open.

## 6. Remaining release prerequisites

1. A live installer download page that carries the source page content and links
   to the source release next to the installer.
2. Verify that same-page link from the public URL. This is the explicit final B1
   prerequisite.
3. A reviewed record of that verification (new schema version and code), then a
   rebuild and installer.
4. A separate Owner Release Gate: C15 (signing and SmartScreen) BLOCKED, C16 NOT
   RUN, and the two carried-forward S5 icon evidence gaps.
5. Deferred and unchanged: M9.2–M9.4; formal Windows UAT and accessibility; B5's
   corpus terms (not derived while the model is not bundled).

## 7. Validation

| Check | Result |
| --- | --- |
| Focused tests (`tests/tools`, lifecycle) | 270 passed, 3 opt-in skipped. New `test_m10_source_hosting.py` covers the committed record and the notices, the derivation tiers, missing and malformed records, ten mutated records, substituted archive and guide evidence, and the installer's re-derivation with three forgeries. `test_m10_b4_notices.py` adds a tampered `NOTICE.md` case. The source page test now allows only the published release URL |
| Real-packet check (private) | The packet was re-assembled from a copy of the existing frozen bundle `ec824ba` (no rebuild, no installer). Blockers exactly `[B1]` (`B1_HOSTED`); `b4_coverage.remaining` empty; hosting record valid; `distribution_permitted` false; the installer's packet check yields `["B1"]` and its hosting condition is the "not linked, not verified" text. Receipt: [`r4a-packet-check.json`](evidence/r4a/r4a-packet-check.json) |
| Installer | Not rebuilt. The Release-2 installer predates all of this and keeps its B1/B4 receipt |
| PR CI | One run on the PR's final head; the result is recorded in the PR |

## 8. Not done

No installer rebuild or publication, application tag or Release, VMware run,
product or model change, M9 change, merge, or new licensing research. LD1–LD6,
`B1_OWNER_DECISION.json` and `LICENSE_DECISIONS.json` are unchanged.
