"""Dev/acceptance helper (not a product feature): open the native desktop on demo data.

The demo project is a small invented CSV.
Everything lives in a disposable demo folder (``_local/demo`` by default), never in
the real per-user application-data folder. The first run seeds it: it imports the
two pinned models from a local Hugging Face cache (``model_cache``), imports an
invented CSV, analyses it with the real models, and accepts a few AI judgments so
Review and Agreement show content. Later runs open the same folder instantly.

    python tools/demo/launch_demo.py [--root DIR] [--models-src DIR] [--reset]
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

DEMO_NAME = "Demo feedback (invented)"
ACCEPTED_ROWS = 6
SEEDED_MARKER = "demo_seeded.txt"
# Written when the tool first claims a folder, before any seeding, so a seed that
# was interrupted is still recognised as the tool's own. Only a folder that carries
# it, and holds nothing but the entries below, is ever cleaned automatically.
SENTINEL = ".sti-demo-workspace"
SENTINEL_TEXT = "sti demo workspace" + chr(10)
TOOL_CHILDREN = ("projects", "models", "locks")  # created by the app's own folders


class UnsafeRoot(Exception):
    """The folder is not a disposable demo workspace this tool may touch."""


def _refuse(root: Path, why: str) -> UnsafeRoot:
    return UnsafeRoot(
        f"Refusing to use {root}: {why}. Nothing was changed or deleted. "
        "Choose an empty or new folder for --root, or leave --root out."
    )


def _is_link(path: Path) -> bool:
    return path.is_symlink() or bool(
        getattr(os.path, "isjunction", lambda _p: False)(path)
    )


def prepare_workspace(
    root: Path, *, real_app_data: Path | None, repo: Path, reset: bool = False
) -> bool:
    """Make ``root`` a clean tool-owned workspace; True when it needs seeding.

    Raises ``UnsafeRoot`` before changing anything unless the folder is missing,
    empty, or carries this tool's sentinel and holds only the tool's own entries.
    Cleaning removes only those known entries, never an arbitrary tree.
    """

    lexical = Path(os.path.abspath(root))
    resolved = lexical.resolve()
    home = Path.home().resolve()
    if _is_link_in_path(lexical):
        raise _refuse(root, "it is, or sits behind, a link to somewhere else")
    if resolved == Path(resolved.anchor) or resolved in (home, repo.resolve()):
        raise _refuse(root, "it is a drive, home or repository root")
    if resolved in repo.resolve().parents or resolved in home.parents:
        raise _refuse(root, "it contains the repository or the home folder")
    if real_app_data is not None:
        real = real_app_data.resolve()
        if resolved == real or real in resolved.parents or resolved in real.parents:
            raise _refuse(root, "it is, holds or sits inside the real app data")
    if not resolved.exists():
        resolved.mkdir(parents=True)
        (resolved / SENTINEL).write_text(SENTINEL_TEXT, encoding="utf-8")
        return True
    if not resolved.is_dir():
        raise _refuse(root, "it is not a folder")
    entries = {item.name: item for item in resolved.iterdir()}
    if not entries:
        (resolved / SENTINEL).write_text(SENTINEL_TEXT, encoding="utf-8")
        return True
    if SENTINEL not in entries:
        raise _refuse(root, "it is not empty and was not created by this tool")
    known = {*TOOL_CHILDREN, SEEDED_MARKER, SENTINEL}
    unknown = sorted(set(entries) - known)
    if unknown:
        raise _refuse(root, f"it holds files this tool did not create ({unknown[0]})")
    if any(_is_link(entries[name]) for name in TOOL_CHILDREN if name in entries):
        raise _refuse(root, "one of its folders is a link to somewhere else")
    if not reset and SEEDED_MARKER in entries:
        return False
    for name in TOOL_CHILDREN:  # a reset, or an interrupted seed: clean what we made
        if name in entries:
            shutil.rmtree(entries[name])
    if SEEDED_MARKER in entries:
        entries[SEEDED_MARKER].unlink()
    return True


def _is_link_in_path(path: Path) -> bool:
    return any(_is_link(parent) for parent in (path, *path.parents))


def seed(services, models_src: Path) -> list[str]:  # type: ignore[no-untyped-def]
    """Import models, the demo CSV and a few reviews; return notes for the console."""

    from demo_data import csv_text

    from social_text_intelligence.application.review_workflow import (
        Advance,
        ReviewFilters,
    )
    from social_text_intelligence.services.review import ReviewFilter

    notes: list[str] = []
    provisioning = services.provisioning
    if not provisioning.status().ready:
        if models_src.is_dir():
            print("Importing the pinned models (about 1 GB, first run only)...")
            provisioning.import_folder(models_src)
        verified = provisioning.verify()
        services.gate.note_verify_result(verified)
        if not verified.ready:
            notes.append(
                "Models are not ready, so the demo project is imported but not "
                "analysed. Use the model setup screen, or pass --models-src."
            )
    details = services.workflow.import_csv(csv_text().encode("utf-8"), name=DEMO_NAME)
    project_id = details.summary.project_id
    if details.phase.value == "needs_column":
        services.workflow.choose_column(project_id, "text")
    if provisioning.status().ready:
        print("Analysing the demo rows with the real models (about a minute)...")
        services.workflow.analyze(project_id)
        queue = ReviewFilters(status=ReviewFilter.UNREVIEWED)
        for _ in range(ACCEPTED_ROWS):
            snapshot = services.reviews.open_review(project_id, queue)
            if snapshot.record is None:
                break
            services.reviews.accept_both(
                project_id,
                snapshot.record.row_number,
                "Demo: AI judgment accepted.",
                expected=snapshot.record.review,
                filters=queue,
                advance=Advance.STAY,
            )
    return notes


def _real_app_data() -> Path | None:
    from social_text_intelligence.infrastructure.app_data import (
        default_app_data_locations,
    )

    try:
        return default_app_data_locations().root.resolve()
    except Exception:  # noqa: BLE001 - only used to refuse the real folder
        return None


def main(argv: list[str] | None = None, *, real_app_data: Path | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(REPO / "_local" / "demo"))
    parser.add_argument("--models-src", default=str(REPO / "model_cache"))
    parser.add_argument(
        "--reset",
        action="store_true",
        help="remove this tool's own demo data and seed again",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    real = real_app_data if real_app_data is not None else _real_app_data()
    if real is not None:
        resolved = Path(os.path.abspath(root)).resolve()
        if resolved == real or real in resolved.parents:
            sys.stderr.write("Refusing to use the real application-data folder.\n")
            return 2
    try:
        needs_seed = prepare_workspace(
            root, real_app_data=real, repo=REPO, reset=args.reset
        )
    except UnsafeRoot as error:
        sys.stderr.write(f"{error}\n")
        return 2
    root = Path(os.path.abspath(root)).resolve()

    from PySide6.QtWidgets import QApplication

    from social_text_intelligence.desktop.composition import build_desktop_services
    from social_text_intelligence.desktop.qt.app import build_window
    from social_text_intelligence.desktop.qt.main_window import APP_TITLE
    from social_text_intelligence.desktop.qt.style import STYLESHEET
    from social_text_intelligence.infrastructure.app_data import AppDataLocations

    locations = AppDataLocations(root)
    if needs_seed:
        for note in seed(build_desktop_services(locations), Path(args.models_src)):
            print(note)
        (root / SEEDED_MARKER).write_text("seeded\n", encoding="utf-8")
    app = QApplication.instance() or QApplication(sys.argv[:1])
    assert isinstance(app, QApplication)
    app.setApplicationName(APP_TITLE)
    app.setStyleSheet(STYLESHEET)
    window, runner = build_window(locations)
    window.setWindowTitle(f"{APP_TITLE} (demo data)")
    window.show()
    window.start()
    code = app.exec()
    runner.wait_idle(5)
    return code


if __name__ == "__main__":
    sys.exit(main())
