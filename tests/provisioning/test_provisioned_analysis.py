"""Analysis only runs from verified local models and never downloads them."""

from __future__ import annotations

from pathlib import Path

import pytest

from social_text_intelligence.application.model_provisioning import (
    build_provisioned_analysis_service,
    provisioned_analysis_settings,
)
from social_text_intelligence.application.projects import InMemoryProjectRepository
from social_text_intelligence.application.settings import AppSettings
from social_text_intelligence.application.use_cases import ApplicationUseCases
from social_text_intelligence.contracts.errors import (
    ModelsNotReadyError,
    ProviderError,
)
from social_text_intelligence.infrastructure.model_store import LocalModelProvisioner

from .fakes import EMOTION, MANIFEST, SENTIMENT, FakeTransport, write_model

NOT_READY_MESSAGE = (
    "The required local models are not ready. Download them or use a models "
    "folder before analysing."
)


def provisioner_for(root: Path, transport: FakeTransport) -> LocalModelProvisioner:
    return LocalModelProvisioner(
        models_root=root, transport=transport, manifest=MANIFEST
    )


def test_direct_analysis_without_ready_models_fails_and_downloads_nothing(
    tmp_path: Path,
) -> None:
    transport = FakeTransport.serving_manifest()
    root = tmp_path / "models"
    write_model(root, EMOTION)
    gateway = build_provisioned_analysis_service(
        AppSettings(), provisioner_for(root, transport)
    )
    use_cases = ApplicationUseCases(InMemoryProjectRepository(), gateway)

    with pytest.raises(ModelsNotReadyError) as raised:
        use_cases.analyze_text("A synthetic sentence.", max_text_length=100)

    assert raised.value.not_ready == ("sentiment",)
    assert ApplicationUseCases.safe_error(raised.value) == NOT_READY_MESSAGE
    assert transport.requests == []
    assert not gateway.initialized
    assert not (root / ".sti-staging").exists()


def test_batch_analysis_without_ready_models_commits_nothing(tmp_path: Path) -> None:
    transport = FakeTransport.serving_manifest()
    gateway = build_provisioned_analysis_service(
        AppSettings(), provisioner_for(tmp_path / "models", transport)
    )
    use_cases = ApplicationUseCases(InMemoryProjectRepository(), gateway)
    token = use_cases.upload_batch(
        b"text\nFirst synthetic row.\nSecond synthetic row.\n",
        max_bytes=10_000,
        max_rows=10,
        max_text_length=100,
    )

    with pytest.raises(ModelsNotReadyError):
        use_cases.analyze_workspace(token)

    workspace = use_cases.projects.get(token)
    assert workspace is not None
    assert workspace.result is None
    assert workspace.preview is not None
    assert transport.requests == []


def test_ready_models_are_loaded_from_the_managed_folder_in_offline_mode(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    settings = provisioned_analysis_settings(
        AppSettings(cache_dir=Path("elsewhere"), offline=False), root
    )

    assert settings.cache_dir == root
    assert settings.offline is True


def test_ready_models_pass_the_gate_and_reach_the_local_loaders(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    write_model(root, SENTIMENT)
    write_model(root, EMOTION)
    transport = FakeTransport.serving_manifest()
    gateway = build_provisioned_analysis_service(
        AppSettings(), provisioner_for(root, transport)
    )
    use_cases = ApplicationUseCases(InMemoryProjectRepository(), gateway)

    # Synthetic files are not loadable weights, so the real loaders fail
    # locally; what matters is that the readiness gate let analysis through.
    with pytest.raises(ProviderError):
        use_cases.analyze_text("A synthetic sentence.", max_text_length=100)

    assert gateway.initialized
    assert transport.requests == []
