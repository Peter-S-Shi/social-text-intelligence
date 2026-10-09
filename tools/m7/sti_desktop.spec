# M7 feasibility build (experiment). Run from the repository root:
#   python -m PyInstaller --noconfirm --distpath _local/m7/dist --workpath _local/m7/build tools/m7/sti_desktop.spec
# One onedir folder holding two executables: the real desktop entry and the E2E probe.
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

datas = collect_data_files("py3langid") + collect_data_files(
    "social_text_intelligence", includes=["resources/*.json"]
)
# The providers import torch and transformers with importlib, so the analyser cannot
# see them; they are named here. Metadata is copied because transformers and
# huggingface_hub check installed package versions at import time.
hidden = [
    "torch",
    "transformers",
    "tokenizers",
    "safetensors",
    "huggingface_hub",
    "py3langid.langid",
    "social_text_intelligence.providers.cardiff_sentiment",
    "social_text_intelligence.providers.samlowe_emotion",
    "social_text_intelligence.providers.language_py3langid",
]
hidden += collect_submodules("transformers.models.roberta")
for package in (
    "torch", "transformers", "tokenizers", "safetensors", "huggingface_hub",
    "numpy", "tqdm", "regex", "requests", "packaging", "filelock", "pyyaml",
    "httpx", "hf_xet", "py3langid",
):
    try:
        datas += copy_metadata(package)
    except Exception:
        pass

excludes = ["flask", "tkinter", "PySide6.QtWebEngineCore", "PySide6.QtQml", "PySide6.QtQuick"]
if os.environ.get("M7_MINIMISE") == "1":
    # developer tooling that the build environment carried in, not application code
    excludes += ["pytest", "_pytest", "pygments", "rich", "typer", "click", "setuptools", "pkg_resources"]
common = dict(pathex=["src"], datas=datas, hiddenimports=hidden, excludes=excludes)

desktop = Analysis(["entry_desktop.py"], **common)
probe = Analysis(["probe_e2e.py"], **common)
MERGE((desktop, "entry_desktop", "sti-desktop"), (probe, "probe_e2e", "sti-probe"))

pyz_d = PYZ(desktop.pure)
pyz_p = PYZ(probe.pure)
exe_d = EXE(pyz_d, desktop.scripts, [], exclude_binaries=True, name="sti-desktop", console=False, upx=False)
exe_p = EXE(pyz_p, probe.scripts, [], exclude_binaries=True, name="sti-probe", console=True, upx=False)
coll = COLLECT(
    exe_d, desktop.binaries, desktop.datas,
    exe_p, probe.binaries, probe.datas,
    name="sti-m7", upx=False,
)
