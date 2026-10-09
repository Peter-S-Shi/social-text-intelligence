"""Managed local model folder in the Hugging Face cache layout.

Files enter the pinned snapshot folder only after their size and SHA-256 match
the approved manifest; partial files live in a staging folder the model loaders
never read. An explicit Verify records a same-size hash mismatch as an empty
marker in a verification folder the loaders never read either; the quick status
reads those markers but never hashes and never writes. Nothing here logs.
"""

from __future__ import annotations

import contextlib
import errno
import hashlib
import os
import threading
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from ..application.exclusion import MODELS_SCOPE, ProcessLocks
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
from .process_locks import FileProcessLocks

STAGING_DIRECTORY_NAME = ".sti-staging"
VERIFICATION_DIRECTORY_NAME = ".sti-verification"
_CORRUPT_SUFFIX = ".corrupt"
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
_WIN_DISK_FULL, _WIN_HANDLE_DISK_FULL = 112, 39


def snapshots_dir(root: Path, spec: ModelSpec) -> Path:
    org, name = spec.model_id.split("/", maxsplit=1)
    return root / f"models--{org}--{name}" / "snapshots"


class _Cancelled(Exception):
    pass


class _Progress:
    """Turns byte counts into ``ProvisioningProgress`` events for one operation.

    Model and overall counts never move backwards. During a download or import,
    verifying a kept or just-fetched file re-reads bytes that are either about
    to be replaced or already counted, so only the file count moves then.
    """

    def __init__(
        self,
        callback: ProgressCallback | None,
        total: int,
        *,
        verifying_advances: bool = False,
    ) -> None:
        self._callback = callback
        self._total = total
        self._verifying_advances = verifying_advances
        self._done_before_model = 0
        self._model_done_before_file = 0
        self._file_done = 0
        self._spec: ModelSpec | None = None

    def start_model(self, spec: ModelSpec) -> None:
        if self._spec is not None:
            self._done_before_model += self._spec.total_bytes
        self._spec = spec
        self._model_done_before_file = 0
        self._file_done = 0

    def finish_file(self, item: ModelFile) -> None:
        self._model_done_before_file += item.size
        self._file_done = 0

    def report(self, phase: ProvisioningPhase, item: ModelFile, done: int) -> None:
        if self._callback is None or self._spec is None:
            return
        if phase is not ProvisioningPhase.VERIFYING or self._verifying_advances:
            self._file_done = max(self._file_done, done)
        model_done = self._model_done_before_file + self._file_done
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


_FileStep = Callable[[ModelSpec, ModelFile, _Progress, CancelCheck], None]


class LocalModelProvisioner:
    """Implements ``ModelProvisioning`` over one managed models folder."""

    def __init__(
        self,
        *,
        models_root: Path,
        transport: DownloadTransport,
        manifest: Sequence[ModelSpec] = APPROVED_MODELS,
        process_locks: ProcessLocks | None = None,
    ) -> None:
        self._root = models_root
        self._transport = transport
        self._manifest = tuple(manifest)
        self._busy = threading.Lock()
        # Cross-process exclusion for every operation that changes the folder;
        # None keeps the exclusion in-process only (tests, embedding).
        self._process_locks = process_locks

    @contextmanager
    def _exclusive(self) -> Iterator[None]:
        """Hold the in-process flag and the cross-process models lock together.

        Both are tried, never waited on. A second operation in this process is
        ``provisioning_in_progress``; one in another process (another window of the
        app) is ``provisioning_elsewhere``. The OS drops the second kind with its
        process, so a crashed window never leaves the folder locked.
        """

        if not self._busy.acquire(blocking=False):
            raise ModelProvisioningError("provisioning_in_progress")
        try:
            held = None
            if self._process_locks is not None:
                try:
                    held = self._process_locks.try_acquire(MODELS_SCOPE)
                except OSError:
                    raise ModelProvisioningError("storage_failed") from None
                if held is None:
                    raise ModelProvisioningError("provisioning_elsewhere")
            try:
                yield
            finally:
                if held is not None:
                    held.release()
        finally:
            self._busy.release()

    @property
    def models_root(self) -> Path:
        return self._root

    def status(self) -> ModelsStatus:
        return ModelsStatus(tuple(self._status(spec) for spec in self._manifest))

    def verify(self, *, on_progress: ProgressCallback | None = None) -> ModelsStatus:
        """Hash every installed file and record what it finds.

        A same-size file whose hash fails gets a corruption marker that the
        quick status reads, so the finding survives later status checks and
        restarts; a file that matches has any earlier marker cleared.
        """

        progress = _Progress(
            on_progress,
            sum(spec.total_bytes for spec in self._manifest),
            verifying_advances=True,
        )
        with self._exclusive():
            for spec in self._manifest:
                progress.start_model(spec)
                for item in spec.files:
                    target = self._target_path(spec, item)
                    if _file_size(target) == item.size:
                        try:
                            intact = _digest_matches(target, item, progress)
                        except OSError:
                            # Unreadable is not a finding: record nothing.
                            raise ModelProvisioningError("storage_failed") from None
                        if intact:
                            self._accept(spec, item)
                        else:
                            self._mark_corrupt(spec, item)
                    progress.finish_file(item)
        return self.status()

    def discard_partial_downloads(
        self, keys: tuple[str, ...] | None = None
    ) -> ModelsStatus:
        if keys is None:
            keys = tuple(spec.key for spec in self._manifest)
        specs = self._select(keys)
        with self._exclusive():
            for spec in specs:
                for item in spec.files:
                    _remove(self._part_path(spec, item))
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
        return self._operation(
            self._select(keys), on_progress, cancelled, self._download_file
        )

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

        def import_file(
            spec: ModelSpec, item: ModelFile, progress: _Progress, cancel: CancelCheck
        ) -> None:
            self._import_file(spec, item, importable[spec.key], progress, cancel)

        return self._operation(self._select(keys), on_progress, cancelled, import_file)

    def _operation(
        self,
        specs: tuple[ModelSpec, ...],
        on_progress: ProgressCallback | None,
        cancelled: CancelCheck | None,
        provision_file: _FileStep,
    ) -> ProvisioningResult:
        """Run one exclusive download or import, model by model, file by file."""

        progress = _Progress(on_progress, sum(spec.total_bytes for spec in specs))
        is_cancelled = cancelled or (lambda: False)
        try:
            with self._exclusive():
                for spec in specs:
                    progress.start_model(spec)
                    for item in spec.files:
                        if is_cancelled():
                            raise _Cancelled()
                        provision_file(spec, item, progress, is_cancelled)
                        progress.finish_file(item)
        except _Cancelled:
            return self._result(ProvisioningOutcome.CANCELLED)
        except ModelProvisioningError as error:
            return self._result(ProvisioningOutcome.FAILED, error)
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
        if set(keys) - {spec.key for spec in self._manifest}:
            raise ValueError("Unknown model key.")
        return tuple(spec for spec in self._manifest if spec.key in keys)

    def _download_file(
        self,
        spec: ModelSpec,
        item: ModelFile,
        progress: _Progress,
        cancelled: CancelCheck,
    ) -> None:
        target = self._target_path(spec, item)
        if _installed_and_matching(target, item, progress, cancelled):
            self._accept(spec, item)
            return
        part = self._part_path(spec, item)
        start = _file_size(part) or 0
        if start > item.size:
            _remove(part)
            start = 0
        if start < item.size:
            self._fetch(spec, item, part, start, progress, cancelled)
        if not _matches(part, item, progress, cancelled):
            _remove(part)
            raise ModelProvisioningError("checksum_mismatch")
        _install(part, target)
        self._accept(spec, item)

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
                if written < item.size:
                    # A body that ends early is an interrupted transfer: keep it.
                    raise TransportError("network_unavailable")
        except TransportError as error:
            if error.code != "network_unavailable":
                _remove(part)
            raise ModelProvisioningError(error.code) from None
        except OSError as error:
            raise _storage_error(error) from None

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
        target = self._target_path(spec, item)
        if _installed_and_matching(target, item, progress, cancelled):
            self._accept(spec, item)
            return
        staged = self._part_path(spec, item).with_suffix(_IMPORT_SUFFIX)
        try:
            _copy_verified(item, source_dir / item.name, staged, progress, cancelled)
            _install(staged, target)
            self._accept(spec, item)
        finally:
            _discard_quietly(staged)  # never masks the outcome being reported

    def _corrupt_marker(self, spec: ModelSpec, item: ModelFile) -> Path:
        return (
            self._root
            / VERIFICATION_DIRECTORY_NAME
            / spec.key
            / spec.revision
            / f"{item.name}{_CORRUPT_SUFFIX}"
        )

    def _mark_corrupt(self, spec: ModelSpec, item: ModelFile) -> None:
        marker = self._corrupt_marker(spec, item)
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.touch()
        except OSError as error:
            raise _storage_error(error) from None

    def _accept(self, spec: ModelSpec, item: ModelFile) -> None:
        """The installed file has just been hash-verified: clear any finding."""

        _remove(self._corrupt_marker(spec, item))

    def _target_path(self, spec: ModelSpec, item: ModelFile) -> Path:
        return snapshots_dir(self._root, spec) / spec.revision / item.name

    def _part_path(self, spec: ModelSpec, item: ModelFile) -> Path:
        return (
            self._root
            / STAGING_DIRECTORY_NAME
            / spec.key
            / spec.revision
            / f"{item.name}{_PART_SUFFIX}"
        )

    def _status(self, spec: ModelSpec) -> ModelStatus:
        """Quick, read-only status: presence, exact size, and Verify findings."""

        missing, wrong = _compare(
            spec,
            snapshots_dir(self._root, spec) / spec.revision,
            flagged=lambda item: self._corrupt_marker(spec, item).is_file(),
        )
        problems = {*missing, *wrong}
        others = _other_revisions(snapshots_dir(self._root, spec), spec.revision)
        resumable = sum(
            _file_size(self._part_path(spec, item)) or 0
            for item in spec.files
            if item.name in problems
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
            installed_bytes=sum(
                item.size for item in spec.files if item.name not in problems
            ),
            resumable_bytes=resumable,
            problem_files=tuple(
                item.name for item in spec.files if item.name in problems
            ),
            other_revisions=others,
        )


def local_model_provisioner(locations: AppDataLocations) -> LocalModelProvisioner:
    """Production wiring: the per-user models folder and the HTTPS transport."""

    return LocalModelProvisioner(
        models_root=locations.models_dir,
        transport=UrllibDownloadTransport(),
        process_locks=FileProcessLocks(locations.locks_dir),
    )


def _compare(
    spec: ModelSpec,
    directory: Path,
    flagged: Callable[[ModelFile], bool] | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return the (missing, wrong) manifest file names in ``directory``."""

    missing: list[str] = []
    wrong: list[str] = []
    for item in spec.files:
        size = _file_size(directory / item.name)
        if size is None:
            missing.append(item.name)
        elif size != item.size or (flagged is not None and flagged(item)):
            wrong.append(item.name)
    return tuple(missing), tuple(wrong)


def _candidate_finding(spec: ModelSpec, candidate: Path) -> FolderModelFinding:
    missing, wrong = _compare(spec, candidate)
    if wrong:
        finding = FolderFinding.MISMATCHED
    elif not missing:
        finding = FolderFinding.FOUND
    elif len(missing) < len(spec.files):
        finding = FolderFinding.INCOMPLETE
    else:
        finding = FolderFinding.NOT_FOUND
    problems = {*missing, *wrong}
    return FolderModelFinding(
        spec.key,
        finding,
        tuple(item.name for item in spec.files if item.name in problems),
    )


def _copy_verified(
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
    except OSError as error:
        raise _storage_error(error) from None
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
                except OSError as error:
                    raise _storage_error(error) from None
                progress.report(ProvisioningPhase.COPYING, item, copied)
                if cancelled():
                    raise _Cancelled()
    if copied != item.size or digest.hexdigest() != item.sha256:
        raise ModelProvisioningError("checksum_mismatch")


def _installed_and_matching(
    target: Path, item: ModelFile, progress: _Progress, cancelled: CancelCheck
) -> bool:
    return _file_size(target) == item.size and _matches(
        target, item, progress, cancelled
    )


def _matches(
    path: Path,
    item: ModelFile,
    progress: _Progress,
    cancelled: CancelCheck | None = None,
) -> bool:
    """For download and import: an unreadable file is simply not kept."""

    try:
        return _digest_matches(path, item, progress, cancelled)
    except OSError:
        return False


def _digest_matches(
    path: Path,
    item: ModelFile,
    progress: _Progress,
    cancelled: CancelCheck | None = None,
) -> bool:
    """Hash ``path`` against the manifest; read errors propagate as ``OSError``."""

    digest = hashlib.sha256()
    done = 0
    with path.open("rb") as handle:
        for chunk in _read_chunks(handle):
            digest.update(chunk)
            done += len(chunk)
            progress.report(ProvisioningPhase.VERIFYING, item, min(done, item.size))
            if cancelled is not None and cancelled():
                raise _Cancelled()
    return done == item.size and digest.hexdigest() == item.sha256


def _read_chunks(handle: BinaryIO) -> Iterator[bytes]:
    while chunk := handle.read(_HASH_CHUNK):
        yield chunk


def _install(part: Path, target: Path) -> None:
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(part, target)
    except OSError as error:
        raise _storage_error(error) from None


def _storage_error(error: OSError) -> ModelProvisioningError:
    """A full disk gets its own code; every other write failure stays generic."""

    full = error.errno == errno.ENOSPC or getattr(error, "winerror", None) in {
        _WIN_DISK_FULL,
        _WIN_HANDLE_DISK_FULL,
    }
    return ModelProvisioningError("storage_full" if full else "storage_failed")


def _remove(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        raise ModelProvisioningError("storage_failed") from None


def _discard_quietly(path: Path) -> None:
    with contextlib.suppress(OSError):
        path.unlink(missing_ok=True)


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
