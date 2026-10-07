"""Synthetic models and an in-memory transport; no network and no real weights."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from social_text_intelligence.application.model_provisioning import (
    ModelFile,
    ModelSpec,
)
from social_text_intelligence.infrastructure.model_download import (
    DownloadStream,
    TransportError,
)

SENTIMENT_BYTES = {
    "config.json": b'{"synthetic": "sentiment"}',
    "weights.bin": bytes(range(256)) * 40,
}
EMOTION_BYTES = {
    "config.json": b'{"synthetic": "emotion"}',
    "model.safetensors": b"synthetic-emotion-weights" * 300,
    "vocab.json": b'{"a": 1}',
}
SENTIMENT_REVISION = "a" * 40
EMOTION_REVISION = "b" * 40


def _files(contents: dict[str, bytes]) -> tuple[ModelFile, ...]:
    return tuple(
        ModelFile(
            name=name, size=len(data), sha256=hashlib.sha256(data).hexdigest()
        )
        for name, data in contents.items()
    )


SENTIMENT = ModelSpec(
    key="sentiment",
    model_id="synthetic-org/sentiment-model",
    revision=SENTIMENT_REVISION,
    license="CC-BY-4.0",
    files=_files(SENTIMENT_BYTES),
)
EMOTION = ModelSpec(
    key="emotion",
    model_id="synthetic-org/emotion-model",
    revision=EMOTION_REVISION,
    license="MIT",
    files=_files(EMOTION_BYTES),
)
MANIFEST = (SENTIMENT, EMOTION)
CONTENT = {"sentiment": SENTIMENT_BYTES, "emotion": EMOTION_BYTES}


def snapshot_dir(root: Path, spec: ModelSpec, revision: str | None = None) -> Path:
    org, name = spec.model_id.split("/")
    return root / f"models--{org}--{name}" / "snapshots" / (revision or spec.revision)


def write_model(
    root: Path,
    spec: ModelSpec,
    *,
    revision: str | None = None,
    only: tuple[str, ...] | None = None,
    overrides: dict[str, bytes] | None = None,
) -> Path:
    """Write a synthetic model in the Hugging Face cache layout."""

    target = snapshot_dir(root, spec, revision)
    target.mkdir(parents=True, exist_ok=True)
    for name, data in CONTENT[spec.key].items():
        if only is not None and name not in only:
            continue
        (target / name).write_bytes((overrides or {}).get(name, data))
    return target


@dataclass
class FakeTransport:
    """Serves manifest content by URL with configurable server behavior."""

    served: dict[str, bytes] = field(default_factory=dict)
    honour_ranges: bool = True
    chunk_size: int = 1024
    fail_after_bytes: dict[str, int] = field(default_factory=dict)
    reject: set[str] = field(default_factory=set)
    requests: list[tuple[str, int]] = field(default_factory=list)
    on_chunk: Callable[[str], None] | None = None

    @classmethod
    def serving_manifest(cls) -> FakeTransport:
        served: dict[str, bytes] = {}
        for spec in MANIFEST:
            for name, data in CONTENT[spec.key].items():
                served[url_for(spec, name)] = data
        return cls(served=served)

    @contextmanager
    def open(self, url: str, *, start: int) -> Iterator[DownloadStream]:
        self.requests.append((url, start))
        if url in self.reject or url not in self.served:
            raise TransportError("download_rejected")
        data = self.served[url]
        resumed = self.honour_ranges and start > 0
        body = data[start:] if resumed else data
        offset = start if resumed else 0
        limit = self.fail_after_bytes.get(url)

        def chunks() -> Iterator[bytes]:
            sent = 0
            for index in range(0, len(body), self.chunk_size):
                piece = body[index : index + self.chunk_size]
                if limit is not None and offset + sent + len(piece) > limit:
                    keep = max(0, limit - offset - sent)
                    if keep:
                        yield piece[:keep]
                    raise TransportError("network_unavailable")
                sent += len(piece)
                if self.on_chunk is not None:
                    self.on_chunk(url)
                yield piece

        yield DownloadStream(resumed=resumed, chunks=chunks())


def url_for(spec: ModelSpec, name: str) -> str:
    return f"https://huggingface.co/{spec.model_id}/resolve/{spec.revision}/{name}"
