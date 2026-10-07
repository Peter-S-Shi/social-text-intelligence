"""A Verify that finds corruption is durable until the file is repaired.

Status stays a cheap, hash-free check; it reads the recorded Verify finding, so
a same-size tampered file cannot flip back to ``ready`` (contract sections 4, 9).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from social_text_intelligence.application.model_provisioning import (
    ProvisioningOutcome,
    Readiness,
    build_provisioned_analysis_service,
)
from social_text_intelligence.application.settings import AppSettings
from social_text_intelligence.contracts import NormalizedTextInput
from social_text_intelligence.contracts.errors import (
    ModelProvisioningError,
    ModelsNotReadyError,
)
from social_text_intelligence.infrastructure.model_store import LocalModelProvisioner

from .fakes import CONTENT, EMOTION, MANIFEST, SENTIMENT, FakeTransport, write_model

TAMPERED = bytes(len(CONTENT["sentiment"]["weights.bin"]))  # same size, wrong bytes


def provisioner(root: Path, transport: FakeTransport | None = None) -> (
    LocalModelProvisioner
):
    return LocalModelProvisioner(
        models_root=root,
        transport=transport or FakeTransport.serving_manifest(),
        manifest=MANIFEST,
    )


def tampered_models(root: Path) -> Path:
    snapshot = write_model(root, SENTIMENT, overrides={"weights.bin": TAMPERED})
    write_model(root, EMOTION)
    return snapshot


def test_verified_corruption_stays_non_ready_across_status_and_restart(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    tampered_models(root)
    first = provisioner(root)
    assert first.status().ready  # the quick check cannot see same-size damage

    assert first.verify().model("sentiment").readiness is Readiness.CORRUPT

    again = first.status().model("sentiment")
    assert again.readiness is Readiness.CORRUPT
    assert again.problem_files == ("weights.bin",)
    restarted = provisioner(root).status()
    assert restarted.model("sentiment").readiness is Readiness.CORRUPT
    assert restarted.model("emotion").ready
    assert restarted.not_ready_keys == ("sentiment",)


def test_analysis_is_blocked_after_verify_finds_corruption(tmp_path: Path) -> None:
    root = tmp_path / "models"
    tampered_models(root)
    transport = FakeTransport.serving_manifest()
    provisioner(root, transport).verify()

    gateway = build_provisioned_analysis_service(
        AppSettings(), provisioner(root, transport)
    )
    with pytest.raises(ModelsNotReadyError) as raised:
        gateway.analyze(
            NormalizedTextInput.from_text("A synthetic sentence.", language="en")
        )

    assert raised.value.not_ready == ("sentiment",)
    assert not gateway.initialized
    assert transport.requests == []  # blocking analysis never downloads


def test_an_explicit_download_repairs_only_the_corrupt_file_and_clears_it(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    snapshot = tampered_models(root)
    transport = FakeTransport.serving_manifest()
    provisioner(root, transport).verify()

    result = provisioner(root, transport).download()

    assert result.outcome is ProvisioningOutcome.COMPLETED
    assert [url for url, _ in transport.requests] == [
        "https://huggingface.co/synthetic-org/sentiment-model/resolve/"
        + "a" * 40
        + "/weights.bin"
    ]
    assert result.status.ready
    assert provisioner(root).status().ready  # also after a restart
    assert (snapshot / "weights.bin").read_bytes() == CONTENT["sentiment"][
        "weights.bin"
    ]


def test_importing_a_good_copy_clears_the_corruption(tmp_path: Path) -> None:
    root = tmp_path / "models"
    tampered_models(root)
    provisioner(root).verify()
    source = tmp_path / "good-cache"
    write_model(source, SENTIMENT)

    result = provisioner(root).import_folder(source)

    assert result.outcome is ProvisioningOutcome.COMPLETED
    assert result.status.ready
    assert provisioner(root).status().ready


def test_a_failed_repair_leaves_the_model_non_ready(tmp_path: Path) -> None:
    root = tmp_path / "models"
    tampered_models(root)
    transport = FakeTransport.serving_manifest()
    provisioner(root, transport).verify()
    transport.reject.add(
        "https://huggingface.co/synthetic-org/sentiment-model/resolve/"
        + "a" * 40
        + "/weights.bin"
    )

    result = provisioner(root, transport).download()

    assert result.outcome is ProvisioningOutcome.FAILED
    assert result.status.model("sentiment").readiness is Readiness.CORRUPT
    assert not provisioner(root).status().ready


def test_a_later_verify_clears_the_finding_once_the_file_matches_again(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    snapshot = tampered_models(root)
    provisioner(root).verify()
    (snapshot / "weights.bin").write_bytes(CONTENT["sentiment"]["weights.bin"])

    # Status stays conservative: only a hash check can lift the finding.
    assert provisioner(root).status().model("sentiment").readiness is (
        Readiness.CORRUPT
    )
    assert provisioner(root).verify().ready
    assert provisioner(root).status().ready


def test_verify_is_refused_while_a_download_or_import_runs(tmp_path: Path) -> None:
    root = tmp_path / "models"
    transport = FakeTransport.serving_manifest()
    busy = provisioner(root, transport)
    refused: list[str] = []

    def verify_during_download(_: str) -> None:
        if not refused:
            try:
                busy.verify()
            except ModelProvisioningError as error:
                refused.append(error.code)

    transport.on_chunk = verify_during_download
    busy.download(("emotion",))

    assert refused == ["provisioning_in_progress"]


def test_a_download_that_re_verifies_a_restored_file_clears_it_without_fetching(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    snapshot = tampered_models(root)
    transport = FakeTransport.serving_manifest()
    provisioner(root, transport).verify()
    (snapshot / "weights.bin").write_bytes(CONTENT["sentiment"]["weights.bin"])

    result = provisioner(root, transport).download()

    assert result.status.ready
    assert transport.requests == []
