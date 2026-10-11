"""The optional language model: pinned upstream download, separate from analysis.

Synthetic bytes stand in for the real model; nothing here touches the network.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from social_text_intelligence.application.exclusion import (
    LANGUAGE_MODEL_SCOPE,
    MODELS_SCOPE,
)
from social_text_intelligence.application.language_model import (
    LANGUAGE_MODEL_FILE,
    LANGUAGE_MODEL_SHA256,
    LANGUAGE_MODEL_SIZE,
    installed_language_model,
)
from social_text_intelligence.application.model_provisioning import (
    APPROVED_MODELS,
    LANGUAGE_MODEL,
    ModelFile,
    ProvisioningOutcome,
    Readiness,
)
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.model_store import (
    LocalModelProvisioner,
    local_language_model_provisioner,
    local_model_provisioner,
)

from .fakes import FakeTransport

DATA = b"synthetic language model" * 4096
SPEC = replace(
    LANGUAGE_MODEL,
    files=(
        ModelFile(LANGUAGE_MODEL_FILE, len(DATA), hashlib.sha256(DATA).hexdigest()),
    ),
)
URL = f"{LANGUAGE_MODEL.download_base}/{LANGUAGE_MODEL_FILE}"


def provisioner(root: Path, transport: FakeTransport) -> LocalModelProvisioner:
    return LocalModelProvisioner(
        models_root=root, transport=transport, manifest=(SPEC,)
    )


def test_the_pin_names_the_exact_upstream_release_file() -> None:
    assert LANGUAGE_MODEL.download_base == (
        "https://raw.githubusercontent.com/adbar/py3langid/"
        "3b99caf00d0dcbc9416a9d06f8e5b690e919a74e/py3langid/data"
    )
    (item,) = LANGUAGE_MODEL.files
    assert (item.name, item.size, item.sha256) == (
        "model.npz.xz",
        LANGUAGE_MODEL_SIZE,
        LANGUAGE_MODEL_SHA256,
    )
    assert LANGUAGE_MODEL_SIZE == 4_586_720
    # Never part of the readiness that gates analysis.
    assert LANGUAGE_MODEL.key not in {spec.key for spec in APPROVED_MODELS}


def test_download_fetches_the_pinned_url_and_installs_where_the_detector_reads(
    tmp_path: Path,
) -> None:
    transport = FakeTransport(served={URL: DATA})
    store = provisioner(tmp_path, transport)
    assert store.status().models[0].readiness is Readiness.NOT_INSTALLED
    result = store.download()
    assert result.outcome is ProvisioningOutcome.COMPLETED
    assert [url for url, _ in transport.requests] == [URL]
    assert installed_language_model(tmp_path).read_bytes() == DATA
    assert result.status.ready


def test_other_bytes_are_never_installed(tmp_path: Path) -> None:
    store = provisioner(tmp_path, FakeTransport(served={URL: DATA[:-1] + b"!"}))
    result = store.download()
    assert result.outcome is ProvisioningOutcome.FAILED
    assert result.error_code == "checksum_mismatch"
    assert not installed_language_model(tmp_path).exists()


def test_an_interrupted_download_resumes(tmp_path: Path) -> None:
    transport = FakeTransport(served={URL: DATA}, fail_after_bytes={URL: 10_000})
    store = provisioner(tmp_path, transport)
    first = store.download()
    assert first.error_code == "network_unavailable"
    assert first.status.models[0].resumable_bytes == 10_000
    transport.fail_after_bytes.clear()
    assert store.download().outcome is ProvisioningOutcome.COMPLETED
    assert transport.requests[-1] == (URL, 10_000)
    assert installed_language_model(tmp_path).read_bytes() == DATA


def test_the_required_models_status_ignores_the_language_model(
    tmp_path: Path,
) -> None:
    locations = AppDataLocations(tmp_path)
    language = local_language_model_provisioner(locations)
    required = local_model_provisioner(locations)
    assert [m.key for m in language.status().models] == ["language"]
    assert "language" not in required.status().not_ready_keys
    assert language.models_root == required.models_root


def test_language_and_weight_downloads_use_separate_locks(tmp_path: Path) -> None:
    class Locks:
        def __init__(self) -> None:
            self.scopes: list[str] = []

        def try_acquire(self, scope: str) -> object:
            self.scopes.append(scope)
            return type("Held", (), {"release": lambda self: None})()

    locks = Locks()
    LocalModelProvisioner(
        models_root=tmp_path,
        transport=FakeTransport(served={URL: DATA}),
        manifest=(SPEC,),
        process_locks=locks,  # type: ignore[arg-type]
        lock_scope=LANGUAGE_MODEL_SCOPE,
    ).download()
    assert locks.scopes == [LANGUAGE_MODEL_SCOPE]
    assert LANGUAGE_MODEL_SCOPE != MODELS_SCOPE
