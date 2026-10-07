"""The urllib transport against a local in-process HTTP server (no internet)."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from social_text_intelligence.infrastructure.model_download import (
    TransportError,
    UrllibDownloadTransport,
    pinned_file_url,
)

BODY = bytes(range(256)) * 64


class _Handler(BaseHTTPRequestHandler):
    honour_ranges = True

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        if self.path == "/missing":
            self.send_error(404)
            return
        if self.path == "/moved":
            self.send_response(302)
            self.send_header("Location", "/file")
            self.end_headers()
            return
        requested = self.headers.get("Range")
        if requested and type(self).honour_ranges:
            start = int(requested.removeprefix("bytes=").rstrip("-"))
            body = BODY[start:]
            self.send_response(206)
            self.send_header(
                "Content-Range", f"bytes {start}-{len(BODY) - 1}/{len(BODY)}"
            )
        else:
            body = BODY
            self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return  # keep test output quiet; the transport itself never logs


@pytest.fixture()
def server() -> Iterator[str]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(
        target=httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
    )
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        _Handler.honour_ranges = True


def read_all(transport: UrllibDownloadTransport, url: str, start: int) -> tuple[
    bool, bytes
]:
    with transport.open(url, start=start) as stream:
        return stream.resumed, b"".join(stream.chunks)


def local_transport() -> UrllibDownloadTransport:
    return UrllibDownloadTransport(require_https=False, chunk_size=1000)


def test_a_fresh_request_streams_the_whole_file(server: str) -> None:
    assert read_all(local_transport(), f"{server}/file", 0) == (False, BODY)


def test_an_honoured_range_resumes_from_the_offset_even_after_a_redirect(
    server: str,
) -> None:
    assert read_all(local_transport(), f"{server}/moved", 5_000) == (
        True,
        BODY[5_000:],
    )


def test_an_ignored_range_is_reported_so_the_caller_restarts(server: str) -> None:
    _Handler.honour_ranges = False

    assert read_all(local_transport(), f"{server}/file", 5_000) == (False, BODY)


def test_http_errors_are_rejections_and_unreachable_hosts_are_network_errors(
    server: str,
) -> None:
    with pytest.raises(TransportError) as rejected:
        read_all(local_transport(), f"{server}/missing", 0)
    assert rejected.value.code == "download_rejected"

    closed = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = closed.server_address[1]
    closed.server_close()
    with pytest.raises(TransportError) as unreachable:
        read_all(local_transport(), f"http://127.0.0.1:{port}/file", 0)
    assert unreachable.value.code == "network_unavailable"


def test_the_production_transport_refuses_anything_but_https(server: str) -> None:
    with pytest.raises(TransportError) as refused:
        read_all(UrllibDownloadTransport(), f"{server}/file", 0)
    assert refused.value.code == "download_rejected"


def test_pinned_urls_name_the_immutable_revision() -> None:
    assert pinned_file_url("org/model", "a" * 40, "config.json") == (
        "https://huggingface.co/org/model/resolve/" + "a" * 40 + "/config.json"
    )
