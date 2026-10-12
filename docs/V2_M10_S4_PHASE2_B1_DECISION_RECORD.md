# V2 M10 S4 phase 2 — B1 owner-decision record

Status: **COMPLETE on `main` (PR #68). B1 stays OPEN.** The owner approved
decisions D1–D3 of the [S4 memo](V2_M10_S4_B1_DECISION_MEMO.md) as an
**engineering implementation direction**. That approval is not legal clearance:

- legal confirmation is pending;
- exact binding producer-source correspondence is unproven;
- D4 is unresolved together with B4.

B4 stays OPEN. B6 is closed only on its QtCore-only criterion. S5 is NOT RUN.
`distribution_permitted` stays false everywhere, and nothing was published.

## 1. The record

[`distribution/legal/B1_OWNER_DECISION.json`](../distribution/legal/B1_OWNER_DECISION.json)
(schema version 1) ships in the packet as `legal/B1_OWNER_DECISION.json`. It
records:

- D1, D2 and D3 as `approved_engineering_direction`, and D4 as `unresolved`,
  linked to B4;
- `legal_confirmation: pending`;
- `binding_producer_source_correspondence: unproven`;
- `public_source_hosting: not operational`;
- `b1_effect: remains_open`;
- `distribution_permitted: false`;
- its scope: Qt 6.11.2, PySide6_Essentials and shiboken6 6.11.2, and the five
  archive SHA-256 values.

Version 1 cannot express a legal confirmation, a B1 closure or an operational
public download. Any such value is rejected, and recording one would need a
reviewed new schema version.

## 2. Packet validation

`compliance.b1_owner_decision()` checks the shipped copy:

- exact field set;
- the fixed values above, with their types (so `true` is not accepted as `1`);
- the D1–D4 states;
- the Qt version and archive hashes against `distribution/source-manifest.json`;
- the binding versions against the bundled components.

The inventory gains `b1_owner_decision`, with its status, record hash and any
problems.

B1 is **always derived**:

| Evidence | B1 wording |
| --- | --- |
| Qt binaries not SBOM-verified | the unverified wording, whatever the record says |
| No record check | the existing binding wording |
| Record missing, malformed or inconsistent | the existing binding wording plus "Owner decision record rejected: …" |
| Valid record | the decided wording: engineering direction only, legal confirmation pending, correspondence unproven, hosting not operational, D4 unresolved |

## 3. Installer receipt

`installer.py` no longer writes a fixed `B1`–`B6` list. It now:

- takes `legal_blockers` from the verified packet's own blocker codes;
- lists any blocker without a code in `other_packet_blockers`;
- refuses a packet that permits distribution or has a malformed blocker list.

Facts the packet does not derive are stated separately in `release_conditions`:

- B6 is closed only on the QtCore-only criterion, and Gui, Widgets and the
  plugins were not rebuilt from modified source;
- clean-machine validation: `NOT RUN`;
- public source hosting: `not operational`.

## 4. Notices refreshed

- **`SOURCE_ACCESS.md`:**
  - the in-package source now;
  - the owner engineering direction, which is not legal clearance;
  - the approved future hosting policy, kept apart from GPL v3 §6(d)'s
    equivalent-access rule;
  - **no public download exists yet**;
  - Installation Information is unlikely to be triggered, subject to the
    pending legal confirmation.
- **`QT_REPLACEMENT.md`:** a modified-source replacement has been shown for
  **QtCore only** (S3). Gui, Widgets and the plugins have not been shown, and the
  runtime build string was not captured.
- **`QT_NOTICE.md`:** the experiment covered QtCore only, and the record is an
  engineering direction, not legal approval.
- **`INSTALLER_NOTICE.txt`:** the blocker summary is updated: B1 and B4 are
  open; B2 and B3 are resolved; B5 is not derived but its terms are unverified;
  B6 is closed only on the QtCore criterion; source hosting is not operational.

The in-app licence text (`license_notice.py`) was not stale and is unchanged.

## 5. Validation

| Check | Result |
| --- | --- |
| Focused tests (`test_m10_b1_decision.py`, `test_m10_installer.py`) | record integrity (valid, missing, malformed, extra field, 13 inconsistent mutations, missing decision, version mismatch); B1 never removed; installer blockers derived; permissive or malformed packets refused |
| Local full suite | 1,285 passed, 6 opt-in skipped; Ruff and strict MyPy pass |
| Frozen build at `d5cb664` (official CPython 3.13.16) | packet valid; blockers **B1** (decided wording) and **B4**; `b1_owner_decision.valid: true` |
| `--verify-runtime` / `--smoke` / `--license-info` | exit 0 |
| Opt-in frozen pytest | 2 passed |
| Internal installer (Inno 6.7.3, not published) | compiled; receipt `legal_blockers: ["B1", "B4"]`, `release_conditions` as in §3, `distribution_permitted: false` |
| PR CI | run on implementation head `d5cb664`, attached to PR #68 |

Evidence: [s4-phase2-receipt.json](evidence/m10-s4/s4-phase2-receipt.json).

## 6. Not done

- No PySide6 rebuild, no Intel licensing work, no release assets and no
  publication.
- R1/R2 and PR #62 are unchanged.
- B1 closure needs the pending legal confirmation (D1–D3) and a decision on D4
  together with B4.
