"""Production packaging adapters, separate from the source desktop entry."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from .packaging import verify_runtime


def smoke() -> dict[str, object]:
    """Bounded synthetic startup/storage smoke, never the per-user data directory."""
    from PySide6.QtWidgets import QApplication

    from ..infrastructure.app_data import AppDataLocations
    from .composition import build_desktop_services
    from .qt.app import build_window
    from .qt.style import STYLESHEET

    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    app.setStyleSheet(STYLESHEET)
    with TemporaryDirectory(prefix="sti-m10-smoke-") as temporary:
        locations = AppDataLocations(Path(temporary) / "application-data")
        window, runner = build_window(locations)
        try:
            window.show()
            window.start()
            app.processEvents()
            services = build_desktop_services(locations)
            missing = all(
                model.readiness.value == "not_installed"
                for model in services.provisioning.status().models
            )
            details = services.workflow.import_csv(
                b"id,text\nSYN-01,This invented software feedback is synthetic.\n"
                b"SYN-02,\n",
                name="Packaging smoke (synthetic)",
            )
            if details.phase.value == "needs_column":
                details = services.workflow.choose_column(
                    details.summary.project_id, "text"
                )
            reopened = services.workflow.open_project(details.summary.project_id)
            return {
                "window": window.isVisible(),
                "models_unbundled": missing,
                "project_rows": details.row_count,
                "invalid_rows": details.invalid_rows,
                "reopened": reopened.row_count == details.row_count,
            }
        finally:
            if not runner.wait_idle(5):
                raise RuntimeError("Packaging smoke did not finish.")
            window.close()
            app.processEvents()


def diagnostic_main() -> int:
    parser = argparse.ArgumentParser(description="Offline packaged runtime checks")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--verify-runtime", action="store_true")
    modes.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    result = verify_runtime()
    if not result.ready:
        print(
            json.dumps(
                {"ready": False, "failed": result.failed, "message": result.message}
            )
        )
        return 2
    if args.smoke:
        try:
            observed = smoke()
        except Exception:
            print(json.dumps({"ready": False, "message": "Packaging smoke failed."}))
            return 2
        print(json.dumps(observed))
        return (
            0
            if all(observed[key] for key in ("window", "models_unbundled", "reopened"))
            and observed["project_rows"] == 2
            and observed["invalid_rows"] == 1
            else 2
        )
    print(json.dumps({"ready": True, "models_loaded": False}))
    return 0


def gui_main() -> int:
    result = verify_runtime()
    if not result.ready:
        # The Qt dependency itself may be absent; use Windows' native message box
        # rather than a broken Qt import or a console traceback with machine paths.
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                None, result.message, "Social Text Intelligence", 0x10
            )
        return 2
    from .qt.app import main

    return main()
