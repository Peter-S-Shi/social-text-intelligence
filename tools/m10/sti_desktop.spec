# Windows onedir production foundation. Build via tools/m10/build.py.
import re
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

config = Path(SPECPATH)
root = config.parents[1]
# py3langid ships as code only: its statistical model (data/model.npz.xz) is not
# redistributed; users may install it from upstream inside the app (M10 S1, B5).
datas = [(str(root / "LICENSE"), "."), (str(root / "THIRD_PARTY_NOTICES.md"), ".")]
# The approved application icon (M10 S5-UI-001): embedded in both executables and
# shipped at its package path for Qt. build.py refuses a build without it.
icon = root / "src/social_text_intelligence/desktop/qt/resources/sti.ico"
if not icon.is_file():
    raise SystemExit("The application icon is missing; the build is refused.")
datas.append((str(icon), "social_text_intelligence/desktop/qt/resources"))
hidden = [
    "torch", "transformers", "tokenizers", "safetensors", "huggingface_hub",
    "py3langid.langid", "social_text_intelligence.providers.cardiff_sentiment",
    "social_text_intelligence.providers.samlowe_emotion",
    "social_text_intelligence.providers.language_py3langid",
]
hidden += collect_submodules("transformers.models.roberta")
for package in (
    "torch", "transformers", "tokenizers", "safetensors", "huggingface_hub",
    "numpy", "tqdm", "regex", "packaging", "filelock", "pyyaml",
    "httpx", "py3langid",
):
    datas += copy_metadata(package)

common = dict(
    pathex=[str(root / "src")], datas=datas, hiddenimports=hidden,
    # hf_xet serves only Hugging Face Xet downloads; models are fetched by the
    # app's own client and loaded from local folders (M10-E2, blocker B4).
    excludes=["flask", "tkinter", "PySide6.QtWebEngineCore", "PySide6.QtQml",
              "PySide6.QtQuick", "pytest", "_pytest", "pygments", "hf_xet"],
    # The LGPL binding layer stays as loose files beside its DLLs, so a user can
    # replace the whole Qt/PySide6/shiboken6 set without rebuilding the PYZ.
    module_collection_mode={"PySide6": "py", "shiboken6": "py"},
)
desktop = Analysis([str(config / "entry_desktop.py")], **common)
check = Analysis([str(config / "entry_check.py")], **common)
# Not redistributed: the Mesa software renderer the Widgets-only UI never loads
# (M10-E1, B2); Microsoft Visual C++ runtime DLLs, which come from the system
# runtime the installer requires (M10-E2, B3); and PyTorch's protoc.exe build
# tool, which nothing executes at run time (M10-E2, B4).
sys.path.insert(0, str(config))
from build import MICROSOFT_RUNTIME  # noqa: E402  (shared with the build checks)

OMITTED = re.compile(r"opengl32sw\.dll|protoc\.exe", re.I)


def shipped(entry):
    name = Path(entry[0]).name
    return not (OMITTED.fullmatch(name) or MICROSOFT_RUNTIME.fullmatch(name))


for analysis in (desktop, check):
    analysis.binaries = [entry for entry in analysis.binaries if shipped(entry)]
    analysis.datas = [entry for entry in analysis.datas if shipped(entry)]
# COLLECT deduplicates the shared onedir files. Keep each Analysis intact:
# MERGE creates cross-executable extraction dependencies, unsuitable here.
exe_d = EXE(PYZ(desktop.pure), desktop.scripts, [], exclude_binaries=True,
            name="sti-desktop", console=False, upx=False, icon=str(icon))
exe_c = EXE(PYZ(check.pure), check.scripts, [], exclude_binaries=True,
            name="sti-check", console=True, upx=False, icon=str(icon))
COLLECT(exe_d, desktop.binaries, desktop.datas, exe_c, check.binaries, check.datas,
        name="sti-desktop", upx=False)
