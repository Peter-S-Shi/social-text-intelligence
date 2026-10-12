# Synthetic TLS test certificates

These files exist only so the download-transport tests can run a local HTTPS
server. They protect nothing and are not secrets:

- `ca.pem`: a self-signed test CA, "STI synthetic test CA - never trusted". No
  system, browser or product trusts it. Tests trust it explicitly, and only for
  one context. Its private key was discarded after signing.
- `server.pem` and `server.key`: a server certificate for `IP:127.0.0.1` only,
  signed by that CA (RSA 2048, SHA-256, serverAuth, valid until 2126).

Tests use them to check that a trusted chain downloads, and that an untrusted
chain or a mismatched host name is rejected. Never use them anywhere else.
