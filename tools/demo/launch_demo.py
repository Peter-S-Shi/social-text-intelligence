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
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

DEMO_NAME = "Demo feedback (invented)"
ACCEPTED_ROWS = 6
SEEDED_MARKER = "demo_seeded.txt"


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(REPO / "_local" / "demo"))
    parser.add_argument("--models-src", default=str(REPO / "model_cache"))
    parser.add_argument("--reset", action="store_true", help="delete and re-seed")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    from PySide6.QtWidgets import QApplication

    from social_text_intelligence.desktop.composition import build_desktop_services
    from social_text_intelligence.desktop.qt.app import build_window
    from social_text_intelligence.desktop.qt.main_window import APP_TITLE
    from social_text_intelligence.desktop.qt.style import STYLESHEET
    from social_text_intelligence.infrastructure.app_data import (
        AppDataLocations,
        default_app_data_locations,
    )

    try:
        real: Path | None = default_app_data_locations().root.resolve()
    except Exception:  # noqa: BLE001 - only used to refuse the real folder
        real = None
    if real is not None and (root == real or real in root.parents):
        sys.stderr.write("Refusing to use the real application-data folder.\n")
        return 2
    if args.reset and root.is_dir():
        shutil.rmtree(root)
    locations = AppDataLocations(root)
    marker = root / SEEDED_MARKER
    if not marker.is_file():
        # a missing marker means no earlier run finished seeding: start clean
        if root.is_dir():
            shutil.rmtree(root)
        for note in seed(build_desktop_services(locations), Path(args.models_src)):
            print(note)
        root.mkdir(parents=True, exist_ok=True)
        marker.write_text("seeded\n", encoding="utf-8")
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
