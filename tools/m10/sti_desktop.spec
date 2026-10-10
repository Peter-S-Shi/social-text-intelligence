# Windows onedir production foundation. Build via tools/m10/build.py.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

config = Path(SPECPATH)
root = config.parents[1]
datas = collect_data_files("py3langid")
datas += [(str(root / "LICENSE"), "."), (str(root / "THIRD_PARTY_NOTICES.md"), ".")]
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
    "httpx", "hf_xet", "py3langid",
):
    datas += copy_metadata(package)

common = dict(
    pathex=[str(root / "src")], datas=datas, hiddenimports=hidden,
    excludes=["flask", "tkinter", "PySide6.QtWebEngineCore", "PySide6.QtQml",
              "PySide6.QtQuick", "pytest", "_pytest", "pygments"],
)
desktop = Analysis([str(config / "entry_desktop.py")], **common)
check = Analysis([str(config / "entry_check.py")], **common)
MERGE((desktop, "entry_desktop", "sti-desktop"), (check, "entry_check", "sti-check"))
exe_d = EXE(PYZ(desktop.pure), desktop.scripts, [], exclude_binaries=True,
            name="sti-desktop", console=False, upx=False)
exe_c = EXE(PYZ(check.pure), check.scripts, [], exclude_binaries=True,
            name="sti-check", console=True, upx=False)
COLLECT(exe_d, desktop.binaries, desktop.datas, exe_c, check.binaries, check.datas,
        name="sti-desktop", upx=False)
