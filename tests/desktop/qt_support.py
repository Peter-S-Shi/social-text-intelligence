"""Shared headless-Qt test support: the shell wrapper (imports Qt; qt tests only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from provisioning.fakes import FakeTransport
from PySide6.QtWidgets import QPushButton

from social_text_intelligence.application.model_provisioning import (
    LANGUAGE_MODEL,
    ModelProvisioning,
)
from social_text_intelligence.desktop.composition import build_desktop_services
from social_text_intelligence.desktop.qt.main_window import MainWindow
from social_text_intelligence.desktop.qt.platform import DesktopPlatform
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.model_store import LocalModelProvisioner

from .conftest import FakePlatform
from .fakes import FakeProvisioning, StubGateway, synthetic_report


class Shell:
    def __init__(
        self,
        tmp_path: Path,
        fake: FakeProvisioning,
        runner: Any,
        platform: FakePlatform | None = None,
        gateway: Any = None,
        language: ModelProvisioning | None = None,
    ) -> None:
        self.fake = fake
        self.platform = platform or FakePlatform()
        self.gateway = gateway or StubGateway(report=synthetic_report())
        # The optional language model: a real store whose transport serves nothing,
        # so no test can reach the network by clicking Download.
        self.language = language or LocalModelProvisioner(
            models_root=tmp_path / "language-models",
            transport=FakeTransport(),
            manifest=(LANGUAGE_MODEL,),
        )
        services = build_desktop_services(
            AppDataLocations(tmp_path),
            provisioning=fake,
            analysis=self.gateway,
            language_provisioning=self.language,
        )
        self.window = MainWindow(
            services,
            runner,
            DesktopPlatform(
                pick_folder=self.platform.pick_folder,
                pick_csv=self.platform.pick_csv,
                pick_save_csv=self.platform.pick_save_csv,
                open_folder=self.platform.open_folder,
                confirm=self.platform.confirm,
            ),
        )
        self.window.show()
        self.window.start()

    @property
    def setup(self) -> Any:
        return self.window.ui.setup_dialog

    @property
    def models(self) -> Any:
        return self.window.ui.models_dialog

    def button(self, parent: Any, text: str) -> QPushButton:
        matches = [
            b
            for b in parent.findChildren(QPushButton)
            if b.text() == text and b.isVisibleTo(parent)
        ]
        assert matches, f"no visible button {text!r}"
        return cast(QPushButton, matches[0])

    def close(self) -> None:
        self.window.close()
