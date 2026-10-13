# V2 Release-5A-1 — Version freeze and private candidate validation

Status: **the application version is `2.0.0`; the preliminary candidate is
private and is not the release installer. B1 stays OPEN;
`distribution_permitted` stays false.** The planned tag `v2.0.0` is **planned and
not created**. No GitHub Release (including a Draft), tag or public installer
exists.

The Owner approved version `2.0.0` and the planned tag `v2.0.0`. The Owner has
not authorized creating the tag, any Release or Draft, or public distribution.

## 1. What changed

| Where | Change |
| --- | --- |
| `pyproject.toml` | `version = "2.0.0"`, the authoritative declaration |
| `src/social_text_intelligence/__init__.py` | `__version__ = "2.0.0"`; `sti --version` and `sti about` report it |
| Installer | Nothing hard-coded. Both profiles read `pyproject.toml`: candidate `STI-2.0.0-x64-setup.exe`, internal `STI-2.0.0-internal-x64.exe`. `AppVersion` in the Inno script is `2.0.0` |
| Tests | CLI version output; candidate profile; lifecycle status row. A new test requires `pyproject.toml`, `__version__` and the installer's derived version to be one value, and no file under `src`, `tools/m10` or `distribution` to name `0.10.0` |
| Records | `PROJECT_STATUS.md`, `ROADMAP.md` and the installer how-to now say `2.0.0`; the Release-4B record gets a later-note |

Installer policy, the icon, the notices and the two-phase gate are unchanged.

## 2. Historical `0.10.0` records, kept on purpose

These describe V1 or earlier states and are history, not current declarations:

- the V1 lifecycle, Release Candidate Gate and Public Portfolio Delivery text in
  `README.md`, `ROADMAP.md`, `PROJECT_STATUS.md`, `PROJECT_CHARTER.md`, `DEVLOG.md`
  and `docs/FEATURE_COMPLETE_MANUAL_AUDIT.md`;
- the manual acceptance questionnaire and guidance under `manual-qa/`, which
  record `0.10.0` as the version reviewed;
- the S5 records (`STI-0.10.0-internal-x64.exe`, hash `aa43ca1d…`), the S5A
  harness procedure, the M9 contract wording, and the Release-4B record and
  evidence (`STI-0.10.0-x64-setup.exe`, `5c5bde13…6721`).

No remaining current declaration names `0.10.0`.

## 3. Private preliminary candidate (not the release installer)

Built from the clean, committed revision `4414c88` of this PR, with official
CPython 3.13.16. It stays in private storage; nothing was uploaded.

| Item | Result |
| --- | --- |
| Frozen application | `--verify-runtime`, `--smoke` and `--license-info` exit 0; the opt-in frozen pytest passes 3; the compiled `social_text_intelligence` module carries `__version__ == "2.0.0"` |
| Packet | Valid; blockers exactly `[B1]`; B4 remaining empty; LD1–LD6 and source hosting records valid; `distribution_permitted` false |
| Installer | `STI-2.0.0-x64-setup.exe`, 726,695,342 bytes, SHA-256 `4a0fe46e…8c96`; the receipt names profile `candidate`, version `2.0.0`, `published: false`; the Inno script has `AppVersion=2.0.0` |
| Receipt check | The harness function `Get-StiReceiptFacts` accepts it |
| Gate | `release_gate.py candidate` produced the manifest (`awaiting-owner-decisions`). A local `render` with version `2.0.0` and tag `v2.0.0` fills every placeholder; a different version is refused. The preview body stayed local, and no draft was checked or created |

Receipt: [`evidence/r5a1/r5a1-preliminary-candidate-receipt.json`](evidence/r5a1/r5a1-preliminary-candidate-receipt.json).

**This artifact is not the release installer.** Its application revision is a
PR commit that will be squash-merged away. The release installer must be built
fresh from the resulting `main` commit.

## 4. Post-merge rebuild prerequisites

None of these has happened.

1. This PR is independently reviewed, and the Owner separately authorizes the
   squash merge.
2. A clean checkout of the resulting `main` commit, with packaging inputs
   committed (the build refuses otherwise).
3. A fresh build with official CPython 3.13.16 and the verified source directory;
   frozen checks; the packet must derive blockers exactly `[B1]`.
4. A fresh candidate-profile installer, a fresh receipt and manifest. Its name
   must be `STI-2.0.0-x64-setup.exe`; the gate refuses another version.
5. The application revision recorded in that build is the commit the tag must
   point to. The gate checks the real Git tag, not the release's target field.
6. Only then, with separate Owner authorization: create the tag and a **draft**
   release, run the draft check, obtain the Owner Release Gate decision (C15
   signing and SmartScreen BLOCKED, C16 NOT RUN, the two accepted S5 icon
   evidence gaps), publish, and run the public check
   ([V2_R4B_RELEASE_GATE.md](V2_R4B_RELEASE_GATE.md)).

## 5. Validation

| Check | Result |
| --- | --- |
| Targeted tests | `tests/tools`, lifecycle and CLI pass, including the new one-value version test and the Release-5A-1 lifecycle test |
| Local full suite (Windows, Python 3.12) | 1,498 passed, 7 opt-in skipped; Ruff and strict MyPy pass |
| PR CI | One run on the final head; the result is recorded in the PR |

## 6. Not done

No tag, Release or Draft, public installer, merge, rebuild from `main`,
Draft verification or Owner GO. No UI, installer-policy or product change, no
VMware rerun, and no change to B1, `distribution_permitted`, C15/C16, the
accepted S5 gaps or the M9 deferrals.
