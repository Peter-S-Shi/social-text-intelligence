# V2 M10 S5-UI-001 — Application icon

Status: **COMPLETE on `main` (PR #71). The final Windows check is pending the
owner** (§5). No acceptance installer was made, VMware was not used, and S5 is
not complete.

- B1 and B4 stay OPEN.
- `distribution_permitted` stays false, and nothing was published.

## 1. Defect and root cause

On the clean VM, the Start Menu entry showed the wrong icon. In the S5-NET-001
build (`873776d`):

- `sti-desktop.exe` embedded exactly PyInstaller's default `icon-windowed.ico`;
- `sti-check.exe` embedded exactly PyInstaller's default `icon-console.ico`.

In both cases the 7 RT_ICON images were byte-identical to the defaults.

Root cause: `tools/m10/sti_desktop.spec` passed no `icon=`. Everything else
inherited that default:

- the Start Menu shortcut had no `IconFilename`, so it used the EXE's icon;
- the uninstall entry uses `UninstallDisplayIcon={app}\sti-desktop.exe`;
- Qt never called `setWindowIcon`.

## 2. Asset

The owner chose design **A, "text to evidence"**, from three candidates drawn
from the existing desktop palette in `style.py`. It is now frozen.

- [`assets/icon/sti-icon.svg`](../assets/icon/sti-icon.svg) is the reference.
- `tools/m10/render_icon.py` draws the same geometry with QtGui only, with no
  image library added, into
  `src/social_text_intelligence/desktop/qt/resources/sti.ico`:
  - 8 sizes: 16, 20, 24, 32, 40, 48, 64 and 256 px, stored as PNG entries;
  - the approved 16 px variant keeps a single, thicker bar.
- The render is deterministic on one Qt version. Tests compare decoded pixels,
  not PNG bytes.

## 3. One icon everywhere

| Place | Source now |
| --- | --- |
| `sti-desktop.exe`, `sti-check.exe` | `icon=` in the spec embeds `sti.ico` |
| Start Menu shortcut | `IconFilename: "{app}\sti-desktop.exe"` |
| Uninstall entry | `UninstallDisplayIcon={app}\sti-desktop.exe` (unchanged) |
| Window and taskbar | `app.setWindowIcon` with `application_icon()`, which loads the same file from its package path in source and frozen runs |

`--smoke` now also reports `application_icon`.

**Failure behaviour:**

- At run time, a missing or unreadable file only leaves Qt's default icon. The
  app still starts.
- The build fails closed. The spec refuses to start without the file, and
  `build.py` refuses each of these:
  - an icon that is missing or does not have exactly the 8 sizes;
  - an EXE whose RT_ICON images are not exactly the icon's images (checked with
    a stdlib PE resource reader);
  - a bundled copy that differs from the approved file.

## 4. Validation

| Check | Result |
| --- | --- |
| Icon tests (`tests/desktop/test_app_icon.py`) | every size present; colour samples match design A (tile, bubble, tail, both bars, 16 px single bar); committed ICO equals a fresh render; safe fallback; the app sets the icon |
| Build tests (`tests/tools/test_m10_build.py`) | ICO parser; a missing or incomplete icon fails; a synthetic PE carrying the default, partial or approved images is rejected or accepted correctly; an unshipped copy fails; spec, installer and runtime point at one icon |
| PE reader on the old build | reads PyInstaller's default images exactly; the old build is refused ("does not embed the approved application icon") |
| Local full suite (Windows, Python 3.12) | 1,370 passed, 7 opt-in skipped; Ruff and strict MyPy pass |
| Temporary frozen build (local only, not an acceptance build) | see §4.1 |
| Independent Spec and Standards reviews | no blocking findings; fixed in `e00e9ea`: the exact 16 px-only variant, single-source constants, pixel-level render test |
| PR CI | one run on the code head (PR #71) |

### 4.1 Temporary frozen build

This was one local build at `e00e9ea`, made only to inspect the real EXE icon
resources. It was not compiled into an installer, not used for acceptance and
not published.

| Check | Result |
| --- | --- |
| `build.py` (official CPython 3.13.16) | exit 0, including its own fail-closed icon check; packet valid with blockers **B1** and **B4** only; 5,363 files |
| Build evidence | `application_icon_sha256` `89c205cece73baf92b0a4723f21dc74b0298ace951dfce6466a4541153899573`, which equals the committed `sti.ico` |
| pefile, checked independently | `sti-desktop.exe` and `sti-check.exe` each carry 8 RT_ICON images and 1 RT_GROUP_ICON, identical to `sti.ico` |
| Windows shell (`ExtractAssociatedIcon`) | both new EXEs show the STI icon; the S5-NET-001 build's EXE still shows PyInstaller's default |
| Bundled copy | `_internal/social_text_intelligence/desktop/qt/resources/sti.ico` is present |
| `--verify-runtime` / `--smoke` | exit 0; `--smoke` reports `application_icon: true` |
| Opt-in frozen pytest | 3 passed |

## 5. Owner Windows check (pending)

Update: S5 Stage B took five icon screenshots on a fresh install of candidate
`a16d559`. An agent visual review found design A in the title bar, the taskbar
and the Start Menu programs-folder shortcut. The Start Menu list and
Settings › Apps were not captured well enough and are NOT DETERMINED; no icon
defect is known. The owner's sign-off is pending (see the
[S5 completion record](V2_M10_S5_COMPLETION_RECORD.md) §3.1).

On a fresh install of a later internal build (none is made by this PR), confirm
that one icon appears in all four places:

1. the Start Menu entry;
2. the window title bar;
3. the taskbar button;
4. Settings › Apps (the uninstall entry).

Windows caches icons, so use a fresh profile or snapshot. A screenshot of each
place is enough.

## 6. Not done

- No UI/UX change beyond the icon.
- No change to H1–H3, model download, R1/R2 or licensing.
- No acceptance installer.
- The setup program's own icon is unchanged.
- `validate_installer.ps1` does not check `application_icon`.
