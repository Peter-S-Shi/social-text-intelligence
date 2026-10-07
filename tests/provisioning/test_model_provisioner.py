"""The UI-neutral model provisioning boundary; see docs/MODEL_PROVISIONING.md."""

from __future__ import annotations

from pathlib import Path

from social_text_intelligence.application.model_provisioning import (
    ProvisioningOutcome,
    ProvisioningPhase,
    ProvisioningProgress,
    ProvisioningResult,
    Readiness,
)
from social_text_intelligence.infrastructure.model_store import LocalModelProvisioner

from .fakes import (
    CONTENT,
    EMOTION,
    MANIFEST,
    SENTIMENT,
    FakeTransport,
    snapshot_dir,
    url_for,
    write_model,
)


def make_provisioner(
    root: Path, transport: FakeTransport | None = None
) -> LocalModelProvisioner:
    return LocalModelProvisioner(
        models_root=root,
        transport=transport or FakeTransport.serving_manifest(),
        manifest=MANIFEST,
    )


def test_an_empty_models_folder_reports_both_models_not_installed(
    tmp_path: Path,
) -> None:
    status = make_provisioner(tmp_path / "models").status()

    assert [model.key for model in status.models] == ["sentiment", "emotion"]
    assert all(model.readiness is Readiness.NOT_INSTALLED for model in status.models)
    assert not status.ready
    assert status.not_ready_keys == ("sentiment", "emotion")
    assert not (tmp_path / "models").exists()  # reading status never writes


def test_a_complete_pinned_snapshot_is_ready(tmp_path: Path) -> None:
    root = tmp_path / "models"
    write_model(root, SENTIMENT)
    write_model(root, EMOTION)

    status = make_provisioner(root).status()

    assert status.ready
    sentiment = status.model("sentiment")
    assert sentiment.readiness is Readiness.READY
    assert sentiment.installed_bytes == sentiment.total_bytes
    assert sentiment.problem_files == ()


def test_missing_files_make_a_model_incomplete_and_name_the_missing_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    write_model(root, SENTIMENT, only=("config.json",))
    write_model(root, EMOTION)

    status = make_provisioner(root).status()

    sentiment = status.model("sentiment")
    assert sentiment.readiness is Readiness.INCOMPLETE
    assert sentiment.problem_files == ("weights.bin",)
    assert status.not_ready_keys == ("sentiment",)


def test_a_wrong_size_file_is_corrupt_and_never_repaired_by_reading_status(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    snapshot = write_model(root, EMOTION, overrides={"vocab.json": b"{}"})

    status = make_provisioner(root).status()

    assert status.model("emotion").readiness is Readiness.CORRUPT
    assert status.model("emotion").problem_files == ("vocab.json",)
    assert (snapshot / "vocab.json").read_bytes() == b"{}"


def test_only_another_revision_is_wrong_revision_and_is_left_alone(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    other = "c" * 40
    other_snapshot = write_model(root, SENTIMENT, revision=other)

    status = make_provisioner(root).status()

    sentiment = status.model("sentiment")
    assert sentiment.readiness is Readiness.WRONG_REVISION
    assert sentiment.other_revisions == (other,)
    assert (other_snapshot / "weights.bin").is_file()


def test_another_revision_beside_the_pinned_one_is_reported_but_ready(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    write_model(root, SENTIMENT, revision="c" * 40)
    write_model(root, SENTIMENT)

    sentiment = make_provisioner(root).status().model("sentiment")

    assert sentiment.readiness is Readiness.READY
    assert sentiment.other_revisions == ("c" * 40,)


def test_download_installs_both_pinned_models_and_reports_progress(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    transport = FakeTransport.serving_manifest()
    events: list[ProvisioningProgress] = []

    result = make_provisioner(root, transport).download(on_progress=events.append)

    assert result.outcome is ProvisioningOutcome.COMPLETED
    assert result.status.ready
    assert result.error_code is None
    for spec in MANIFEST:
        for name, data in CONTENT[spec.key].items():
            assert (snapshot_dir(root, spec) / name).read_bytes() == data
    assert {url for url, _ in transport.requests} == set(transport.served)

    overall_total = sum(spec.total_bytes for spec in MANIFEST)
    downloading = [e for e in events if e.phase is ProvisioningPhase.DOWNLOADING]
    assert downloading
    assert all(e.overall_bytes_total == overall_total for e in events)
    done = [e.overall_bytes_done for e in downloading]
    assert done == sorted(done)
    assert downloading[-1].overall_bytes_done == overall_total
    last_weights = [e for e in downloading if e.file_name == "weights.bin"][-1]
    assert last_weights.file_bytes_done == last_weights.file_bytes_total == 10_240
    assert last_weights.model_bytes_total == SENTIMENT.total_bytes
    assert not any((root / ".sti-staging").rglob("*.part"))


def test_download_of_one_model_leaves_the_other_untouched(tmp_path: Path) -> None:
    root = tmp_path / "models"
    transport = FakeTransport.serving_manifest()

    result = make_provisioner(root, transport).download(("emotion",))

    assert result.status.model("emotion").ready
    assert result.status.model("sentiment").readiness is Readiness.NOT_INSTALLED
    assert all("emotion-model" in url for url, _ in transport.requests)


def test_a_dropped_connection_keeps_progress_and_the_next_download_resumes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    transport = FakeTransport.serving_manifest()
    weights_url = url_for(SENTIMENT, "weights.bin")
    transport.fail_after_bytes[weights_url] = 4_096

    failed = make_provisioner(root, transport).download(("sentiment",))

    assert failed.outcome is ProvisioningOutcome.FAILED
    assert failed.error_code == "network_unavailable"
    assert failed.error_message is not None
    assert "http" not in failed.error_message
    sentiment = failed.status.model("sentiment")
    assert sentiment.readiness is Readiness.INCOMPLETE
    assert sentiment.problem_files == ("weights.bin",)
    assert sentiment.resumable_bytes == 4_096
    assert (snapshot_dir(root, SENTIMENT) / "config.json").is_file()

    transport.fail_after_bytes.clear()
    transport.requests.clear()
    resumed = make_provisioner(root, transport).download(("sentiment",))

    assert resumed.outcome is ProvisioningOutcome.COMPLETED
    assert resumed.status.model("sentiment").ready
    assert transport.requests == [(weights_url, 4_096)]
    assert resumed.status.model("sentiment").resumable_bytes == 0


def test_a_server_that_ignores_the_range_restarts_that_file_from_zero(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    transport = FakeTransport.serving_manifest()
    weights_url = url_for(SENTIMENT, "weights.bin")
    transport.fail_after_bytes[weights_url] = 3_000
    make_provisioner(root, transport).download(("sentiment",))
    transport.fail_after_bytes.clear()
    transport.honour_ranges = False

    result = make_provisioner(root, transport).download(("sentiment",))

    assert result.status.model("sentiment").ready
    weights = snapshot_dir(root, SENTIMENT) / "weights.bin"
    assert weights.read_bytes() == CONTENT["sentiment"]["weights.bin"]


def test_cancelling_mid_file_keeps_the_partial_for_resume(tmp_path: Path) -> None:
    root = tmp_path / "models"
    transport = FakeTransport.serving_manifest()
    weights_url = url_for(SENTIMENT, "weights.bin")
    chunks_seen: list[str] = []
    transport.on_chunk = chunks_seen.append

    result = make_provisioner(root, transport).download(
        ("sentiment",),
        cancelled=lambda: chunks_seen.count(weights_url) >= 3,
    )

    assert result.outcome is ProvisioningOutcome.CANCELLED
    assert result.error_code is None
    sentiment = result.status.model("sentiment")
    assert sentiment.readiness is Readiness.INCOMPLETE
    assert sentiment.resumable_bytes == 3 * transport.chunk_size

    transport.requests.clear()
    transport.on_chunk = None
    resumed = make_provisioner(root, transport).download(("sentiment",))

    assert resumed.status.model("sentiment").ready
    assert transport.requests == [(weights_url, 3 * transport.chunk_size)]


def test_a_partial_download_alone_makes_a_model_incomplete(tmp_path: Path) -> None:
    root = tmp_path / "models"
    transport = FakeTransport.serving_manifest()
    transport.fail_after_bytes[url_for(EMOTION, "config.json")] = 5

    result = make_provisioner(root, transport).download(("emotion",))

    emotion = result.status.model("emotion")
    assert emotion.readiness is Readiness.INCOMPLETE
    assert emotion.installed_bytes == 0
    assert emotion.resumable_bytes == 5


def test_a_checksum_mismatch_discards_the_file_and_keeps_earlier_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    transport = FakeTransport.serving_manifest()
    weights_url = url_for(SENTIMENT, "weights.bin")
    genuine = transport.served[weights_url]
    transport.served[weights_url] = bytes(len(genuine))  # same size, wrong bytes

    result = make_provisioner(root, transport).download(("sentiment",))

    assert result.outcome is ProvisioningOutcome.FAILED
    assert result.error_code == "checksum_mismatch"
    sentiment = result.status.model("sentiment")
    assert sentiment.readiness is Readiness.INCOMPLETE
    assert sentiment.problem_files == ("weights.bin",)
    assert sentiment.resumable_bytes == 0
    assert not (snapshot_dir(root, SENTIMENT) / "weights.bin").exists()
    assert (snapshot_dir(root, SENTIMENT) / "config.json").is_file()


def test_a_rejected_or_oversized_response_fails_without_installing(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    transport = FakeTransport.serving_manifest()
    transport.reject.add(url_for(EMOTION, "config.json"))
    weights_url = url_for(EMOTION, "model.safetensors")
    transport.served[weights_url] = transport.served[weights_url] + b"extra"

    rejected = make_provisioner(root, transport).download(("emotion",))
    assert rejected.error_code == "download_rejected"

    transport.reject.clear()
    oversized = make_provisioner(root, transport).download(("emotion",))
    assert oversized.error_code == "download_rejected"
    emotion = oversized.status.model("emotion")
    assert emotion.problem_files == ("model.safetensors", "vocab.json")
    assert emotion.resumable_bytes == 0  # the over-long body is not kept


def test_download_replaces_only_bad_installed_files_after_verifying_the_rest(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    tampered = bytes(len(CONTENT["emotion"]["model.safetensors"]))
    write_model(root, EMOTION, overrides={"model.safetensors": tampered})
    write_model(root, SENTIMENT, overrides={"config.json": b"{}"})
    transport = FakeTransport.serving_manifest()
    assert make_provisioner(root, transport).status().model("emotion").ready

    result = make_provisioner(root, transport).download(("emotion", "sentiment"))

    assert result.status.ready
    assert sorted(url for url, _ in transport.requests) == sorted(
        [url_for(EMOTION, "model.safetensors"), url_for(SENTIMENT, "config.json")]
    )
    installed = snapshot_dir(root, EMOTION) / "model.safetensors"
    assert installed.read_bytes() == CONTENT["emotion"]["model.safetensors"]


def test_download_adds_the_pinned_revision_and_leaves_another_revision_alone(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    other = write_model(root, SENTIMENT, revision="c" * 40, overrides={
        "config.json": b'{"other": "revision"}'
    })

    result = make_provisioner(root).download()

    sentiment = result.status.model("sentiment")
    assert sentiment.ready
    assert sentiment.other_revisions == ("c" * 40,)
    assert (other / "config.json").read_bytes() == b'{"other": "revision"}'


def test_a_second_operation_while_one_runs_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "models"
    transport = FakeTransport.serving_manifest()
    provisioner = make_provisioner(root, transport)
    nested: list[ProvisioningResult] = []

    def start_another(_: str) -> None:
        if not nested:
            nested.append(provisioner.download(("emotion",)))

    transport.on_chunk = start_another
    outer = provisioner.download(("sentiment",))

    assert outer.outcome is ProvisioningOutcome.COMPLETED
    assert nested[0].outcome is ProvisioningOutcome.FAILED
    assert nested[0].error_code == "provisioning_in_progress"


def test_an_unwritable_models_folder_fails_with_storage_failed(
    tmp_path: Path,
) -> None:
    blocked = tmp_path / "models"
    blocked.write_bytes(b"not a folder")

    result = make_provisioner(blocked).download()

    assert result.outcome is ProvisioningOutcome.FAILED
    assert result.error_code == "storage_failed"
    assert not result.status.ready


def test_verify_finds_same_size_damage_that_the_quick_status_cannot(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    damaged = bytes(len(CONTENT["sentiment"]["weights.bin"]))
    snapshot = write_model(root, SENTIMENT, overrides={"weights.bin": damaged})
    write_model(root, EMOTION)
    provisioner = make_provisioner(root)
    assert provisioner.status().ready

    verified = provisioner.verify()

    assert verified.model("sentiment").readiness is Readiness.CORRUPT
    assert verified.model("sentiment").problem_files == ("weights.bin",)
    assert verified.model("emotion").ready
    assert (snapshot / "weights.bin").read_bytes() == damaged  # never repaired


def test_discarding_partial_downloads_removes_only_staged_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "models"
    transport = FakeTransport.serving_manifest()
    transport.fail_after_bytes[url_for(SENTIMENT, "weights.bin")] = 2_048
    provisioner = make_provisioner(root, transport)
    provisioner.download(("sentiment",))
    assert provisioner.status().model("sentiment").resumable_bytes == 2_048

    status = provisioner.discard_partial_downloads()

    sentiment = status.model("sentiment")
    assert sentiment.resumable_bytes == 0
    assert sentiment.readiness is Readiness.INCOMPLETE  # config.json stays
    assert (snapshot_dir(root, SENTIMENT) / "config.json").is_file()
