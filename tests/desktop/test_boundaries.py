"""Dependency direction and Qt licensing hygiene, checked from the source itself."""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "src" / "social_text_intelligence"
ROOT_NAME = "social_text_intelligence"

QT_ROOTS = {"PySide6", "shiboken6", "PyQt5", "PyQt6", "PySide2"}
FORBIDDEN_FOR_DESKTOP = {
    "sqlite3",
    "torch",
    "transformers",
    "flask",
    "huggingface_hub",
    "requests",
    "urllib",
    "http",
    "socket",
}
# Only Qt modules that Qt offers under the LGPL (the PySide6-Essentials set).
# Adding one is a licensing decision: check it against Qt's licence listing first.
ALLOWED_QT_MODULES = {"QtCore", "QtGui", "QtWidgets"}


def modules_imported_by(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    package_parts = (
        [ROOT_NAME, *path.relative_to(PACKAGE).with_suffix("").parts[:-1]]
        if path != PACKAGE
        else [ROOT_NAME]
    )
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package_parts[: len(package_parts) - (node.level - 1)]
                module = ".".join(
                    [*base, *(node.module.split(".") if node.module else [])]
                )
            else:
                module = node.module or ""
            found.add(module)
            found.update(f"{module}.{alias.name}" for alias in node.names)
    return found


def sources(under: Path) -> list[Path]:
    return sorted(under.rglob("*.py"))


def root_of(module: str) -> str:
    return module.split(".")[0]


def test_only_the_qt_adapter_imports_qt() -> None:
    offenders = []
    for path in sources(PACKAGE):
        if "desktop" in path.parts and "qt" in path.parts:
            continue
        for module in modules_imported_by(path):
            if root_of(module) in QT_ROOTS:
                offenders.append(f"{path.relative_to(PACKAGE)} -> {module}")
    assert offenders == []


def test_inner_layers_never_import_the_desktop_layer() -> None:
    offenders = []
    for path in sources(PACKAGE):
        if "desktop" in path.parts:
            continue
        for module in modules_imported_by(path):
            if module.startswith(f"{ROOT_NAME}.desktop"):
                offenders.append(f"{path.relative_to(PACKAGE)} -> {module}")
    assert offenders == []


def test_the_desktop_layer_does_not_reach_models_sqlite_network_or_flask() -> None:
    offenders = []
    for path in sources(PACKAGE / "desktop"):
        for module in modules_imported_by(path):
            if root_of(module) in FORBIDDEN_FOR_DESKTOP:
                offenders.append(f"{path.relative_to(PACKAGE)} -> {module}")
            if module.startswith(f"{ROOT_NAME}.interface"):
                offenders.append(f"{path.relative_to(PACKAGE)} -> {module}")
            if module.startswith(f"{ROOT_NAME}.providers.") and module.split(".")[
                -1
            ] in {
                "cardiff_sentiment",
                "samlowe_emotion",
            }:
                offenders.append(f"{path.relative_to(PACKAGE)} -> {module}")
    assert offenders == []


def test_only_the_composition_root_wires_infrastructure() -> None:
    importers = set()
    for path in sources(PACKAGE / "desktop"):
        if any(
            m.startswith(f"{ROOT_NAME}.infrastructure")
            for m in modules_imported_by(path)
        ):
            importers.add(path.relative_to(PACKAGE / "desktop").as_posix())
    assert importers == {"composition.py", "qt/app.py"}


def test_qt_modules_used_are_limited_to_the_lgpl_set() -> None:
    used = set()
    for path in sources(PACKAGE / "desktop" / "qt"):
        for module in modules_imported_by(path):
            parts = module.split(".")
            if parts[0] == "PySide6" and len(parts) > 1:
                used.add(parts[1])
    assert used, "the Qt adapter should import PySide6 modules"
    assert used <= ALLOWED_QT_MODULES, used - ALLOWED_QT_MODULES
