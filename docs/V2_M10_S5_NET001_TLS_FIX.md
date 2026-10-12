# V2 M10 S5-NET-001 — Model download certificate verification

Status: **fix COMPLETE on `main` (PR #69). Owner VM re-verification of
S5-NET-001 PASSED at product level (§6).** That closes this defect only.
**S5 as a whole is not complete:** the clean-machine matrix C01–C16 is not
formally accepted, and none of its items is marked PASS by this record.

- B1 and B4 stay OPEN.
- B6 stays closed only on its QtCore-only criterion.
- `distribution_permitted` stays false, and nothing was published.

## 1. Defect

During the S5 clean-VM test (Windows 11 in VMware, standard user, internal S4
installer), every pinned Hugging Face download in the app failed with
`network_unavailable` ("Connection lost"). In the same guest, Edge opened the
model page, and curl got HTTP 206 and 1,024 bytes of the pinned weights.

## 2. Diagnosis

The transport caught every `URLError`/`OSError` as `network_unavailable` and
kept no detail, so two bounded probes were run in the guest. Both used the
official CPython 3.13.16 runtime. Its seven key runtime files (`python313.dll`,
`_ssl.pyd`, `_socket.pyd`, `select.pyd`, `_hashlib.pyd`, `libssl-3.dll` and
`libcrypto-3.dll`) are byte-identical to the installed STI.

- **S5-NET-002:** every product-equivalent urllib request failed at `open` with
  `ssl.SSLCertVerificationError`, `verify_code=20` ("unable to get local issuer
  certificate"). No proxy was involved.
- **S5-NET-003 (red/green control):** the product's stdlib arm failed all three
  requests (config, weights, Range resume) on certificate verification. The only
  change in the second arm was a local `truststore.SSLContext` passed through
  `HTTPSHandler(context=…)`, and it passed all three. Results: verdict
  `RED/GREEN`, `reproduction_environment: consistent`,
  `ssl_globals_unchanged: true`.

**Cause.** On Windows, Python's default context gives OpenSSL only the roots
already present in the system store. Unlike the Windows verifier that Edge and
curl rely on, OpenSSL cannot make Windows fetch a missing root or intermediate.
The probes did not determine which certificate was missing, and the fix does not
depend on it.

## 3. Fix

- **Transport:** `UrllibDownloadTransport` builds its opener with
  `HTTPSHandler(context=native_trust_context())`. That function returns
  `truststore.SSLContext(PROTOCOL_TLS_CLIENT)`, with `CERT_REQUIRED` and host-name
  checks, plus the same ALPN (`http/1.1`) and post-handshake-auth options as
  http.client's own default context.
  - Nothing is injected into `ssl`, and verification is never relaxed.
  - HTTPS-only redirects, Range and `Content-Range` validation, checksums and the
    download architecture are unchanged.
- **Error classification:**
  - A certificate verification failure, on the first hop or a redirect hop,
    becomes `certificate_rejected`: "The secure connection could not be
    verified", with a fixed message and no URL.
  - Like `network_unavailable`, it keeps partial files and offers "Download again
    · resumes". Both codes share `PARTIAL_KEEPING_CODES`.
  - Other `SSLError`s stay `network_unavailable`.
- **Dependency:** `truststore` 0.10.4 (MIT, pure Python) is a core dependency,
  constrained to `>=0.10.4,<0.11`.
  - The build pins it in `tools/m10/requirements-build.txt` and installs it from
    `tools/m10/requirements-truststore.txt` (`--require-hashes`, wheel SHA-256
    `adaeaecf1cbb5f4de3b1959b42d41f6fab57b2b1666adb59e89cb0b53361d981`).
  - `build.py` refuses an installed truststore whose files differ from that
    wheel.
- **Licence and packaging:**
  - It has a `component-register.json` entry, which packet assembly requires
    (fail-closed), and a `THIRD_PARTY_NOTICES.md` entry.
  - The frozen inventory carries the wheel's MIT text.
  - `verify_runtime` now requires `truststore`.
  - An opt-in frozen test checks the inventory entry and its notice.

## 4. Tests

`tests/provisioning/test_download_transport_tls.py` runs a local HTTPS server.
Its synthetic CA is trusted nowhere ([`tls/README.md`](../tests/provisioning/tls/README.md)),
and `.gitignore` has an exception for exactly those three files. The tests cover:

- a trusted stream;
- redirect plus Range resume over HTTPS;
- a refused HTTPS-to-HTTP redirect;
- an untrusted chain;
- a host-name mismatch;
- an untrusted redirect target;
- unchanged `ssl` defaults.

Further tests cover:

- keeping partial files after a certificate rejection, then resuming;
- the panel's wording and recovery;
- the runtime preflight;
- the build pin and the licence register.

On Windows these tests run truststore's native verifier. On Linux CI, truststore
uses OpenSSL and the system CA paths, so the Windows path is proven by local
Windows runs and the VM.

## 5. Validation

See [s5-net-001-receipt.json](evidence/m10-s5/s5-net-001-receipt.json).

| Check | Result |
| --- | --- |
| Before the fix (main `4282d03`), local untrusted HTTPS server | reported `network_unavailable` |
| After the fix, same server | reported `certificate_rejected` |
| Local full suite at `2d69d71` (Windows, Python 3.12) | 1,321 passed, 7 opt-in skipped; Ruff and strict MyPy pass |
| Affected suites after the review fixes | 760 passed |
| Independent Spec and Standards reviews | no blocking findings; the should-fix items were addressed in `873776d` |
| PR CI | [run 38280074010](https://github.com/Peter-S-Shi/social-text-intelligence/actions/runs/38280074010): 4 checks passed on `873776d` |
| Frozen build at `873776d` (official CPython 3.13.16) | packet valid; blockers **B1** and **B4** only; inventory has truststore 0.10.4 (MIT, one licence notice); `truststore._windows` is in the PYZ |
| `--verify-runtime` / `--smoke` / `--license-info` | exit 0 (the preflight now requires truststore) |
| Opt-in frozen pytest | 3 passed, including the truststore inventory check |
| Internal installer (Inno 6.7.3, not published) | compiled; SHA-256 `a7fedbd633dd00651df8c22e6d6fac4ea749f25c948f6c3a96126d5e35ebe071`; receipt `legal_blockers: ["B1", "B4"]`, `distribution_permitted: false` |

## 6. Owner VM re-verification: PASS (product level)

The owner verified the fix in the restored Windows 11 VMware guest, as a standard
user, with the internal installer whose SHA-256 is
`a7fedbd633dd00651df8c22e6d6fac4ea749f25c948f6c3a96126d5e35ebe071` (built at
`873776d`). The evidence falls into three kinds, kept separate here.

**Owner-witnessed, in the installed app:**

- Both required models, sentiment and emotion, downloaded for real.
- The app reported that their checksum verification passed.
- Real inference returned Positive (sentiment) and Joy (emotion).
- The optional py3langid language model downloaded, and the app identified
  English (`en`).
- After the app restarted, the models were still installed and Ready.
- Downloads recovered after the owner stopped one and after the network was
  disconnected.

**Shown directly by the owner's final screenshot:** "2/2 models ready", with both
models Ready.

**Automated evidence (§5):**

- the transport tests and CI;
- the frozen build, its packet and checks;
- the installer receipt.

**Not captured, so not claimed:**

- raw network logs, HTTP status codes or byte-level transfer observations from
  the app;
- the certificate chain the app validated;
- which partial byte count each resume continued from.

What the PASS covers: S5-NET-001 is resolved for this build in this environment.
In-app downloads that failed certificate verification before the fix now
complete, verify, run and persist.

What it does not cover:

- the S5 clean-machine matrix (C01–C16);
- the `validate_installer.ps1` lifecycle run;
- the missing/present VC++ runtime stages;
- the C07/C14 manual checks;
- formal Windows UAT;
- release readiness.

Those stay NOT RUN unless a separate record accepts them.

## 7. Not done (separate follow-up work)

- S5-UI-001 (the application icon) is a separate open item.
- Harness corrections H1–H3 to `validate_installer.ps1`:
  - H1: take the blockers from the receipt instead of the hard-coded B1–B6;
  - H2: add the missing/present VC++ runtime stages;
  - H3: keep automatic and witnessed clean-machine acceptance separate.
- The remaining installer lifecycle acceptance in the S5 matrix.
- No change to R1 or R2, B1, B4 or B6.
- No diagnostics system, no `network-check` mode and no download-architecture
  change.
