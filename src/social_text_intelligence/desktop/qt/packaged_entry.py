"""Production packaging adapters, separate from the source desktop entry."""

from __future__ import annotations

import argparse
import json
import sys

from ..packaging import verify_runtime


def smoke() -> dict[str, object]:
    from .app import packaged_smoke

    return packaged_smoke()


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
    from .app import main

    return main()
