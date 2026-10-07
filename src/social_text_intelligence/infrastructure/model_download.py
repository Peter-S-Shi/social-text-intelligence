"""HTTPS download transport for pinned model files; nothing here logs."""

from __future__ import annotations

import http.client
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from typing import IO, Protocol
from urllib.parse import urlsplit

HUGGING_FACE_BASE_URL = "https://huggingface.co"
_USER_AGENT = "social-text-intelligence-model-provisioner"


class TransportError(Exception):
    """A transport failure carrying only a fixed provisioning error code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(slots=True)
class DownloadStream:
    """``resumed`` is true only when the server honoured the requested offset."""

    resumed: bool
    chunks: Iterator[bytes]


class DownloadTransport(Protocol):
    def open(self, url: str, *, start: int) -> AbstractContextManager[DownloadStream]:
        ...


def pinned_file_url(model_id: str, revision: str, file_name: str) -> str:
    return f"{HUGGING_FACE_BASE_URL}/{model_id}/resolve/{revision}/{file_name}"


class _RedirectPolicy(urllib.request.HTTPRedirectHandler):
    """Follow redirects (the CDN keeps the Range header) but never off HTTPS."""

    def __init__(self, require_https: bool) -> None:
        super().__init__()
        self._require_https = require_https

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: http.client.HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        if self._require_https and urlsplit(newurl).scheme != "https":
            raise TransportError("download_rejected")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class UrllibDownloadTransport:
    """Stdlib HTTPS streaming with Range resume; the system proxy applies as-is."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        require_https: bool = True,
        chunk_size: int = 1024 * 1024,
    ) -> None:
        self._timeout = timeout_seconds
        self._require_https = require_https
        self._chunk_size = chunk_size

    @contextmanager
    def open(self, url: str, *, start: int) -> Iterator[DownloadStream]:
        if self._require_https and urlsplit(url).scheme != "https":
            raise TransportError("download_rejected")
        headers = {"User-Agent": _USER_AGENT}
        if start > 0:
            headers["Range"] = f"bytes={start}-"
        opener = urllib.request.build_opener(_RedirectPolicy(self._require_https))
        try:
            response = opener.open(
                urllib.request.Request(url, headers=headers), timeout=self._timeout
            )
        except urllib.error.HTTPError as error:
            error.close()
            raise TransportError("download_rejected") from None
        except (urllib.error.URLError, OSError, http.client.HTTPException):
            raise TransportError("network_unavailable") from None
        with response:
            status = response.status
            content_range = response.headers.get("Content-Range", "")
            if start > 0 and status == 206:
                if not content_range.startswith(f"bytes {start}-"):
                    raise TransportError("download_rejected")
                resumed = True
            elif status == 200:
                resumed = False
            else:
                raise TransportError("download_rejected")
            yield DownloadStream(resumed=resumed, chunks=self._chunks(response))

    def _chunks(self, response: IO[bytes]) -> Iterator[bytes]:
        while True:
            try:
                chunk = response.read(self._chunk_size)
            except (OSError, http.client.HTTPException):
                raise TransportError("network_unavailable") from None
            if not chunk:
                return
            yield chunk
