"""Managed local model folder in the Hugging Face cache layout.

Files enter the pinned snapshot folder only after their size and SHA-256 match
the approved manifest; partial files live in a staging folder the model loaders
never read. Reading status never writes. Nothing here logs.
"""

from __future__ import annotations

import hashlib
import os
import threading
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import BinaryIO

from ..application.model_provisioning import (
    APPROVED_MODELS,
    CancelCheck,
    FolderFinding,
    FolderInspection,
    FolderModelFinding,
    ModelFile,
    ModelSpec,
    ModelsStatus,
    ModelStatus,
    ProgressCallback,
    ProvisioningOutcome,
    ProvisioningPhase,
    ProvisioningProgress,
    ProvisioningResult,
    Readiness,
)
from ..contracts.errors import ModelProvisioningError
from .app_data import AppDataLocations
from .model_download import (
    DownloadTransport,
    TransportError,
    UrllibDownloadTransport,
    pinned_file_url,
)

STAGING_DIRECTORY_NAME = ".sti-staging"
_PART_SUFFIX = ".part"
_IMPORT_SUFFIX = ".import"
_FINDING_PRIORITY = (
    FolderFinding.FOUND,
    FolderFinding.MISMATCHED,
    FolderFinding.INCOMPLETE,
    FolderFinding.WRONG_REVISION,
    FolderFinding.NOT_FOUND,
)
_HASH_CHUNK = 1024 * 1024


def snapshots_dir(root: Path, spec: ModelSpec) -> Path:
    org, name = spec.model_id.split("/", maxsplit=1)
    return root / f"models--{org}--{name}" / "snapshots"


class _Cancelled(Exception):
    pass


class _Progress:
    """Turns byte counts into ``ProvisioningProgress`` events for one operation."""

    def __init__(self, callback: ProgressCallback | None, total: int) -> None:
        self._callback = callback
        self._total = total
        self._done_before_model = 0
        self._model_done_before_file = 0
        self._spec: ModelSpec | None = None

    def start_model(self, spec: ModelSpec) -> None:
        if self._spec is not None:
            self._done_before_model += self._spec.total_bytes
        self._spec = spec
        self._model_done_before_file = 0

    def finish_file(self, item: ModelFile) -> None:
        self._model_done_before_file += item.size

    def report(self, phase: ProvisioningPhase, item: ModelFile, done: int) -> None:
        if self._callback is None or self._spec is None:
            return
        model_done = self._model_done_before_file + done
        self._callback(
            ProvisioningProgress(
                phase=phase,
                model_key=self._spec.key,
                file_name=item.name,
                file_bytes_done=done,
                file_bytes_total=item.size,
                model_bytes_done=model_done,
                model_bytes_total=self._spec.total_bytes,
                overall_bytes_done=self._done_before_model + model_done,
                overall_bytes_total=self._total,
            )
        )


class LocalModelProvisioner:
    """Implements ``ModelProvisioning`` over one managed models folder."""

    def __init__(
        self,
        *,
        models_root: Path,
        transport: DownloadTransport,
        manifest: Sequence[ModelSpec] = APPROVED_MODELS,
    ) -> None:
        self._root = models_root
        self._transport = transport
        self._manifest = tuple(manifest)
        self._busy = threading.Lock()

    @property
    def models_root(self) -> Path:
        return self._root

    def status(self) -> ModelsStatus:
        return ModelsStatus(tuple(self._status(spec) for spec in self._manifest))

    def verify(self, *, on_progress: ProgressCallback | None = None) -> ModelsStatus:
        progress = _Progress(
            on_progress, sum(spec.total_bytes for spec in self._manifest)
        )
        return ModelsStatus(
            tuple(self._status(spec, progress) for spec in self._manifest)
        )

    def discard_partial_downloads(
        self, keys: tuple[str, ...] | None = None
    ) -> ModelsStatus:
        if not self._busy.acquire(blocking=False):
            raise ModelProvisioningError("provisioning_in_progress")
        try:
            for spec in self._select(keys or tuple(s.key for s in self._manifest)):
                for item in spec.files:
                    _remove(self._part_path(spec, item))
        finally:
            self._busy.release()
        return self.status()

    def download(
        self,
        keys: tuple[str, ...] | None = None,
        *,
        on_progress: ProgressCallback | None = None,
        cancelled: CancelCheck | None = None,
    ) -> ProvisioningResult:
        if keys is None:
            keys = self.status().not_ready_keys
        specs = self._select(keys)
        progress = _Progress(on_progress, sum(spec.total_bytes for spec in specs))
        is_cancelled = cancelled or (lambda: False)

        def run() -> None:
            for spec in specs:
                progress.start_model(spec)
                for item in spec.files:
                    self._download_file(spec, item, progress, is_cancelled)
                    progress.finish_file(item)

        return self._operation(run)

    def inspect_folder(self, folder: Path) -> FolderInspection:
        located = self._locate(folder)
        return FolderInspection(tuple(finding for finding, _ in located.values()))

    def import_folder(
        self,
        folder: Path,
        keys: tuple[str, ...] | None = None,
        *,
        on_progress: ProgressCallback | None = None,
        cancelled: CancelCheck | None = None,
    ) -> ProvisioningResult:
        try:
            located = self._locate(folder)
        except ModelProvisioningError as error:
            return self._result(ProvisioningOutcome.FAILED, error)
        importable = {
            key: source
            for key, (finding, source) in located.items()
            if finding.finding is FolderFinding.FOUND and source is not None
        }
        if keys is None:
            keys = tuple(importable)
        if set(keys) - set(importable):
            raise ValueError("Only models found in the folder can be imported.")
        specs = self._select(keys)
        progress = _Progress(on_progress, sum(spec.total_bytes for spec in specs))
        is_cancelled = cancelled or (lambda: False)

        def run() -> None:
            for spec in specs:
                progress.start_model(spec)
                for item in spec.files:
                    self._import_file(
                        spec, item, importable[spec.key], progress, is_cancelled
                    )
                    progress.finish_file(item)

        return self._operation(run)

    def _locate(
        self, folder: Path
    ) -> dict[str, tuple[FolderModelFinding, Path | None]]:
        """Find each model in a user folder by layout and size; read-only."""

        try:
            if not folder.is_dir():
                raise OSError
            children = sorted(entry for entry in folder.iterdir() if entry.is_dir())
        except OSError:
            raise ModelProvisioningError("source_unreadable") from None
        located: dict[str, tuple[FolderModelFinding, Path | None]] = {}
        for spec in self._manifest:
            weights = max(spec.files, key=lambda item: item.size).name
            candidates = [snapshots_dir(folder, spec) / spec.revision] + [
                flat for flat in (folder, *children) if (flat / weights).is_file()
            ]
            best: tuple[FolderModelFinding, Path | None] = (
                FolderModelFinding(spec.key, FolderFinding.NOT_FOUND, ()),
                None,
            )
            if _other_revisions(snapshots_dir(folder, spec), spec.revision):
                best = (
                    FolderModelFinding(spec.key, FolderFinding.WRONG_REVISION, ()),
                    None,
                )
            for candidate in candidates:
                finding = _candidate_finding(spec, candidate)
                if _FINDING_PRIORITY.index(finding.finding) < _FINDING_PRIORITY.index(
                    best[0].finding
                ):
                    best = (finding, candidate)
            located[spec.key] = best
        return located

    def _import_file(
        self,
        spec: ModelSpec,
        item: ModelFile,
        source_dir: Path,
        progress: _Progress,
        cancelled: CancelCheck,
    ) -> None:
        if cancelled():
            raise _Cancelled()
        target = snapshots_dir(self._root, spec) / spec.revision / item.name
        if _file_size(target) == item.size and _matches(
            target, item, progress, ProvisioningPhase.VERIFYING
        ):
            return
        staged = self._part_path(spec, item).with_suffix(_IMPORT_SUFFIX)
        try:
            self._copy_verified(
                item, source_dir / item.name, staged, progress, cancelled
            )
            _install(staged, target)
        finally:
            _remove(staged)

    def _copy_verified(
        self,
        item: ModelFile,
        source: Path,
        staged: Path,
        progress: _Progress,
        cancelled: CancelCheck,
    ) -> None:
        digest = hashlib.sha256()
        copied = 0
        try:
            staged.parent.mkdir(parents=True, exist_ok=True)
            output = staged.open("wb")
        except OSError:
            raise ModelProvisioningError("storage_failed") from None
        with output:
            try:
                handle = source.open("rb")
            except OSError:
                raise ModelProvisioningError("source_unreadable") from None
            with handle:
                while True:
                    try:
                        chunk = handle.read(_HASH_CHUNK)
                    except OSError:
                        raise ModelProvisioningError("source_unreadable") from None
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > item.size:
                        raise ModelProvisioningError("checksum_mismatch")
                    digest.update(chunk)
                    try:
                        output.write(chunk)
                    except OSError:
                        raise ModelProvisioningError("storage_failed") from None
                    progress.report(ProvisioningPhase.COPYING, item, copied)
                    if cancelled():
                        raise _Cancelled()
        if copied != item.size or digest.hexdigest() != item.sha256:
            raise ModelProvisioningError("checksum_mismatch")

    def _operation(self, run: Callable[[], None]) -> ProvisioningResult:
        if not self._busy.acquire(blocking=False):
            return self._result(
                ProvisioningOutcome.FAILED,
                ModelProvisioningError("provisioning_in_progress"),
            )
        try:
            run()
        except _Cancelled:
            return self._result(ProvisioningOutcome.CANCELLED)
        except ModelProvisioningError as error:
            return self._result(ProvisioningOutcome.FAILED, error)
        finally:
            self._busy.release()
        return self._result(ProvisioningOutcome.COMPLETED)

    def _result(
        self,
        outcome: ProvisioningOutcome,
        error: ModelProvisioningError | None = None,
    ) -> ProvisioningResult:
        return ProvisioningResult(
            outcome=outcome,
            status=self.status(),
            error_code=None if error is None else error.code,
            error_message=None if error is None else error.message,
        )

    def _select(self, keys: tuple[str, ...]) -> tuple[ModelSpec, ...]:
        known = {spec.key for spec in self._manifest}
        unknown = set(keys) - known
        if unknown:
            raise ValueError("Unknown model key.")
        return tuple(spec for spec in self._manifest if spec.key in keys)

    def _download_file(
        self,
        spec: ModelSpec,
        item: ModelFile,
        progress: _Progress,
        cancelled: CancelCheck,
    ) -> None:
        if cancelled():
            raise _Cancelled()
        target = snapshots_dir(self._root, spec) / spec.revision / item.name
        if _file_size(target) == item.size and _matches(
            target, item, progress, ProvisioningPhase.VERIFYING
        ):
            return
        part = self._part_path(spec, item)
        start = _file_size(part) or 0
        if start > item.size:
            _remove(part)
            start = 0
        if start < item.size:
            self._fetch(spec, item, part, start, progress, cancelled)
        if not _matches(part, item, progress, ProvisioningPhase.VERIFYING):
            _remove(part)
            raise ModelProvisioningError("checksum_mismatch")
        _install(part, target)

    def _fetch(
        self,
        spec: ModelSpec,
        item: ModelFile,
        part: Path,
        start: int,
        progress: _Progress,
        cancelled: CancelCheck,
    ) -> None:
        url = pinned_file_url(spec.model_id, spec.revision, item.name)
        try:
            part.parent.mkdir(parents=True, exist_ok=True)
            with self._transport.open(url, start=start) as stream:
                written = start if stream.resumed else 0
                with part.open("ab" if stream.resumed else "wb") as handle:
                    for chunk in stream.chunks:
                        if written + len(chunk) > item.size:
                            raise TransportError("download_rejected")
                        handle.write(chunk)
                        written += len(chunk)
                        progress.report(ProvisioningPhase.DOWNLOADING, item, written)
                        if cancelled():
                            raise _Cancelled()
        except TransportError as error:
            if error.code != "network_unavailable":
                _remove(part)
            raise ModelProvisioningError(error.code) from None
        except OSError:
            raise ModelProvisioningError("storage_failed") from None

    def _part_path(self, spec: ModelSpec, item: ModelFile) -> Path:
        return (
            self._root
            / STAGING_DIRECTORY_NAME
            / spec.key
            / spec.revision
            / f"{item.name}{_PART_SUFFIX}"
        )

    def _status(
        self, spec: ModelSpec, verify_with: _Progress | None = None
    ) -> ModelStatus:
        """Quick presence-and-size status; hashes too when ``verify_with`` is set."""

        snapshot = snapshots_dir(self._root, spec) / spec.revision
        missing: list[str] = []
        wrong: list[str] = []
        installed = 0
        if verify_with is not None:
            verify_with.start_model(spec)
        for item in spec.files:
            path = snapshot / item.name
            size = _file_size(path)
            if size is None:
                missing.append(item.name)
            elif size != item.size or (
                verify_with is not None
                and not _matches(
                    path, item, verify_with, ProvisioningPhase.VERIFYING
                )
            ):
                wrong.append(item.name)
            else:
                installed += item.size
            if verify_with is not None:
                verify_with.finish_file(item)
        others = _other_revisions(snapshots_dir(self._root, spec), spec.revision)
        resumable = sum(
            _file_size(self._part_path(spec, item)) or 0
            for item in spec.files
            if item.name in missing or item.name in wrong
        )
        if wrong:
            readiness = Readiness.CORRUPT
        elif not missing:
            readiness = Readiness.READY
        elif len(missing) < len(spec.files) or resumable:
            readiness = Readiness.INCOMPLETE
        elif others:
            readiness = Readiness.WRONG_REVISION
        else:
            readiness = Readiness.NOT_INSTALLED
        return ModelStatus(
            key=spec.key,
            model_id=spec.model_id,
            revision=spec.revision,
            license=spec.license,
            readiness=readiness,
            total_bytes=spec.total_bytes,
            installed_bytes=installed,
            resumable_bytes=resumable,
            problem_files=tuple(
                item.name for item in spec.files if item.name in {*missing, *wrong}
            ),
            other_revisions=others,
        )


def local_model_provisioner(locations: AppDataLocations) -> LocalModelProvisioner:
    """Production wiring: the per-user models folder and the HTTPS transport."""

    return LocalModelProvisioner(
        models_root=locations.models_dir, transport=UrllibDownloadTransport()
    )


def _candidate_finding(spec: ModelSpec, candidate: Path) -> FolderModelFinding:
    missing: list[str] = []
    wrong: list[str] = []
    for item in spec.files:
        size = _file_size(candidate / item.name)
        if size is None:
            missing.append(item.name)
        elif size != item.size:
            wrong.append(item.name)
    if wrong:
        finding = FolderFinding.MISMATCHED
    elif not missing:
        finding = FolderFinding.FOUND
    elif len(missing) < len(spec.files):
        finding = FolderFinding.INCOMPLETE
    else:
        finding = FolderFinding.NOT_FOUND
    problems = tuple(
        item.name for item in spec.files if item.name in {*missing, *wrong}
    )
    return FolderModelFinding(spec.key, finding, problems)


def _matches(
    path: Path, item: ModelFile, progress: _Progress, phase: ProvisioningPhase
) -> bool:
    digest = hashlib.sha256()
    done = 0
    try:
        with path.open("rb") as handle:
            for chunk in _read_chunks(handle):
                digest.update(chunk)
                done += len(chunk)
                progress.report(phase, item, min(done, item.size))
    except OSError:
        return False
    return done == item.size and digest.hexdigest() == item.sha256


def _read_chunks(handle: BinaryIO) -> Iterator[bytes]:
    while chunk := handle.read(_HASH_CHUNK):
        yield chunk


def _install(part: Path, target: Path) -> None:
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(part, target)
    except OSError:
        raise ModelProvisioningError("storage_failed") from None


def _remove(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        raise ModelProvisioningError("storage_failed") from None


def _file_size(path: Path) -> int | None:
    try:
        return path.stat().st_size if path.is_file() else None
    except OSError:
        return None


def _other_revisions(snapshots: Path, pinned: str) -> tuple[str, ...]:
    try:
        entries = sorted(entry.name for entry in snapshots.iterdir() if entry.is_dir())
    except OSError:
        return ()
    return tuple(name for name in entries if name != pinned)
