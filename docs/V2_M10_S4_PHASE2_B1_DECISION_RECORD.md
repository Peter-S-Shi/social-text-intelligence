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

`compliance.b1_owner_decision()` checks the shipped copy. Schema 1 must
**equal the approved content exactly**. The comparison uses type-preserving
canonical JSON, so `true` is not accepted as `1`. It covers:

- the record identity, decision date and basis;
- every D1–D4 status, summary and link;
- the fixed states above;
- a scope of the Qt version and archive hashes from
  `distribution/source-manifest.json` and **exactly** the two binding packages,
  `PySide6_Essentials` and `shiboken6` 6.11.2;
- those two versions against the bundled components.

Any changed, missing or extra field is rejected, at any level, and so is any
other `schema_version`. A later reviewed schema has to be added beside version 1
in `compliance.py`.

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
- refuses a packet that permits distribution or has a malformed blocker list;
- refuses a packet with **no blockers**, because distribution is not permitted;
- refuses **every** packet that omits B1. Self-declared inventory fields (`valid`,
  `b1_effect`, `schema_version`) are not trusted. No implemented schema can close
  B1, so a future closure needs its own reviewed, schema-specific validator. That
  is still not a fixed blocker list: other codes are taken from the packet.

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
| Focused tests (`test_m10_b1_decision.py`, `test_m10_installer.py`) | record integrity: valid, missing, malformed, and 31 contradictory, partial or extended records. These include identity, date type, basis, summaries, extra decision fields, missing decisions, schema version, and the exact two-package scope. B1 is never removed. Installer: blockers are derived; packets that permit distribution, are malformed, have no blockers or omit B1 are refused, including one with a fabricated valid schema 2 record |
| Local full suite | 1,309 passed, 6 opt-in skipped; Ruff and strict MyPy pass |
| Frozen build at `d5cb664` (official CPython 3.13.16) | packet valid; blockers **B1** (decided wording) and **B4**; `b1_owner_decision.valid: true` |
| `--verify-runtime` / `--smoke` / `--license-info` | exit 0 |
| Opt-in frozen pytest | 2 passed |
| Internal installer (Inno 6.7.3, not published) | compiled; receipt `legal_blockers: ["B1", "B4"]`, `release_conditions` as in §3, `distribution_permitted: false` |
| PR CI | `d5cb664` and `9da364c`: 4 checks passed each. The final head `a8caced` has its own run attached to PR #68 |
| Review fixes at `9da364c` and `a8caced` | not rebuilt: the shipped record is unchanged. The existing frozen packet's record passes the exact schema 1 check, and a fresh installer preparation from it gives `legal_blockers: ["B1", "B4"]` |

Evidence: [s4-phase2-receipt.json](evidence/m10-s4/s4-phase2-receipt.json).

## 6. Not done

- No PySide6 rebuild, no Intel licensing work, no release assets and no
  publication.
- R1/R2 and PR #62 are unchanged.
- B1 closure needs the pending legal confirmation (D1–D3) and a decision on D4
  together with B4.
