"""The urllib transport over HTTPS against a local server (M10 S5-NET-001).

The server uses a synthetic test CA (``tls/README.md``) that nothing trusts. Only
a test context trusts it, and only for one test. Rejecting an untrusted chain may
make the operating system's verifier consult its own root-update service; no
model repository is contacted. On Windows these tests run truststore's native
verifier; on Linux, truststore verifies with OpenSSL and the system CA paths, so
the Windows path is proven only by a Windows run.
"""

from __future__ import annotations

import ssl
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import truststore

from social_text_intelligence.infrastructure.model_download import (
    TransportError,
    UrllibDownloadTransport,
    native_trust_context,
)

TLS = Path(__file__).parent / "tls"
BODY = bytes(range(256)) * 64


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - http.server API
        if self.path == "/moved":
            self.send_response(302)
            self.send_header("Location", "/file")
            self.end_headers()
            return
        if self.path == "/elsewhere":
            # The second hop presents this server's certificate for another name.
            self.send_response(302)
            port = self.headers["Host"].rsplit(":", 1)[1]
            self.send_header("Location", f"https://localhost:{port}/file")
            self.end_headers()
            return
        if self.path == "/insecure":
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:9/file")
            self.end_headers()
            return
        requested = self.headers.get("Range")
        if requested:
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
        return


@pytest.fixture()
def https_port() -> Iterator[int]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(TLS / "server.pem", TLS / "server.key")
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    thread = threading.Thread(
        target=httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
    )
    thread.start()
    try:
        yield httpd.server_address[1]
    finally:
        httpd.shutdown()
        httpd.server_close()


def trusting_test_ca() -> ssl.SSLContext:
    """The production context, also trusting the synthetic CA for this test."""
    context = native_trust_context()
    context.load_verify_locations(cafile=str(TLS / "ca.pem"))
    return context


def read_all(
    transport: UrllibDownloadTransport, url: str, start: int = 0
) -> tuple[bool, bytes]:
    with transport.open(url, start=start) as stream:
        return stream.resumed, b"".join(stream.chunks)


def ssl_defaults() -> tuple[object, ...]:
    return (
        ssl.SSLContext,
        ssl.create_default_context,
        ssl._create_default_https_context,
    )


def test_production_downloads_verify_with_a_local_native_trust_context() -> None:
    context = native_trust_context()

    assert isinstance(context, truststore.SSLContext)
    assert context.verify_mode is ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_a_trusted_chain_streams_the_whole_file(https_port: int) -> None:
    transport = UrllibDownloadTransport(context_factory=trusting_test_ca)

    assert read_all(transport, f"https://127.0.0.1:{https_port}/file") == (False, BODY)


def test_a_range_resumes_over_https_after_a_redirect(https_port: int) -> None:
    transport = UrllibDownloadTransport(context_factory=trusting_test_ca)

    assert read_all(transport, f"https://127.0.0.1:{https_port}/moved", 5_000) == (
        True,
        BODY[5_000:],
    )


def test_a_redirect_from_https_to_http_is_still_refused(https_port: int) -> None:
    transport = UrllibDownloadTransport(context_factory=trusting_test_ca)

    with pytest.raises(TransportError) as refused:
        read_all(transport, f"https://127.0.0.1:{https_port}/insecure")
    assert refused.value.code == "download_rejected"


def test_an_untrusted_chain_is_a_certificate_rejection(https_port: int) -> None:
    with pytest.raises(TransportError) as rejected:
        read_all(UrllibDownloadTransport(), f"https://127.0.0.1:{https_port}/file")
    assert rejected.value.code == "certificate_rejected"


def test_a_certificate_for_another_host_is_a_certificate_rejection(
    https_port: int,
) -> None:
    transport = UrllibDownloadTransport(context_factory=trusting_test_ca)

    with pytest.raises(TransportError) as rejected:
        read_all(transport, f"https://localhost:{https_port}/file")
    assert rejected.value.code == "certificate_rejected"


def test_an_untrusted_redirect_target_is_a_certificate_rejection(
    https_port: int,
) -> None:
    transport = UrllibDownloadTransport(context_factory=trusting_test_ca)

    with pytest.raises(TransportError) as rejected:
        read_all(transport, f"https://127.0.0.1:{https_port}/elsewhere")
    assert rejected.value.code == "certificate_rejected"


def test_downloads_leave_the_global_ssl_defaults_untouched(https_port: int) -> None:
    before = ssl_defaults()

    read_all(
        UrllibDownloadTransport(context_factory=trusting_test_ca),
        f"https://127.0.0.1:{https_port}/file",
    )
    with pytest.raises(TransportError):
        read_all(UrllibDownloadTransport(), f"https://127.0.0.1:{https_port}/file")

    assert ssl_defaults() == before
    assert ssl.SSLContext.__module__ == "ssl"
    assert ssl._create_default_https_context is ssl.create_default_context
