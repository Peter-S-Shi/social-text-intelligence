# Real-model Batch capacity evidence

This document records the Product Hardening Batch A4 opt-in capacity probe for
Social Text Intelligence 0.10.0. It is measurement evidence, not a new product
performance guarantee and not a change to Batch behavior.

## Scope and method

The probe executes the production `AnalysisService`, `analyze_batch`, and
`EphemeralBatchStore` lease/write-back path with the repository's pinned Cardiff
sentiment and SamLowe emotion revisions. It uses the existing local Hugging Face
cache with offline mode forced. No mock provider, network download, truncation,
parallel inference, background job, persistence, or product optimization is
involved.

The eight deterministic English templates are synthetic and repository-safe.
They contain 12–13 words and 76–82 characters. Every template passes the A2
complete-input validation of both pinned providers; no partial-text inference is
possible. The same loaded provider instances are reused for the warm 1-, 50-,
and 500-row stages.

Peak process resident memory is read from the Windows
`GetProcessMemoryInfo` working-set counters. Physical-memory context comes from
`GlobalMemoryStatusEx`. The report excludes hostnames, usernames, cache paths,
source text, and other local identifiers.

## Reference environment

Measurement timestamp: `2026-08-14T02:46:20Z`.

| Property | Reference value |
| --- | --- |
| OS | Windows 11 (`10.0.26200`) |
| Python | 3.12.13 |
| CPU | 12th Gen Intel Core i7-12700H, 20 logical CPUs |
| Physical memory | 16,823,717,888 bytes total; 2,871,169,024 bytes available at probe start |
| PyTorch | 2.13.0+cpu |
| Execution | CPU-only; offline local cache |
| Sentiment | `cardiffnlp/twitter-roberta-base-sentiment-latest` at `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7` |
| Emotion | `SamLowe/roberta-base-go_emotions` at `d75048347613a25d77de8cf6412eaae9fa7b26be` |

## Measurements

Cold startup separates public provider validation/model initialization from the
first combined inference:

| Cold stage | Wall time |
| --- | ---: |
| Cardiff initialization and complete-input validation | 3.058 s |
| SamLowe initialization and complete-input validation | 0.386 s |
| Both model initializations | 3.444 s |
| First combined inference after initialization | 0.182 s |
| Initialization through first result | 3.626 s |

Warm Batch results use the same initialized service:

| Rows | Wall time | Throughput | Success | Failure | Result committed |
| ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 0.075 s | 13.37 rows/s | 1 | 0 | Yes |
| 50 | 3.763 s | 13.29 rows/s | 50 | 0 | Yes |
| 500 | 39.636 s | 12.61 rows/s | 500 | 0 | Yes |

Process RSS was 38,928,384 bytes before model loading, 1,058,799,616 bytes after
the first combined result, and 1,061,908,480 bytes after the 500-row stage. The
process peak was 1,061,908,480 bytes (about 0.99 GiB). Post-load growth from the
first result through 500 rows was 3,108,864 bytes (about 2.97 MiB), so this probe
did not show row-count-proportional memory growth.

## TTL and active-analysis lease result

Every stage acquired the production Batch analysis lease and committed through
`complete_analysis`. The probe deliberately configured a 1-second workspace TTL.
Both 50 rows (3.763 seconds) and 500 rows (39.636 seconds) ran beyond that TTL;
an intervening store lookup confirmed that the active workspace remained alive,
and each result then committed successfully. The production default TTL is
1,800 seconds, and active analysis remains lease-protected even when execution
crosses that inactivity interval.

Result: no TTL expiry, state loss, false success, or write-back failure occurred.

## Recommended RC acceptance budget

For a comparable CPU-only local desktop with at least 16 GB physical memory,
use the checked-in synthetic probe profile as the reproducible RC reference:

- offline cold initialization through first result: at most 15 seconds;
- warm 1-row Batch: at most 1 second;
- warm 50-row Batch: at most 15 seconds;
- warm 500-row Batch: at most 120 seconds and at least 4 rows/second;
- 500 successful rows, zero failures, active lease retained, and result committed;
- process peak RSS at most 2 GiB;
- post-load RSS growth from warm 1 through warm 500 at most 256 MiB.

These budgets provide substantial headroom over the observed reference run.
They apply to this defined short social-text fixture, not every possible mix of
encoded lengths or hardware. Longer accepted inputs can take longer. The
application's 512-token complete-input boundary remains a correctness contract,
not a latency promise, and the 500-row setting remains a row-capacity limit
rather than a fixed-duration SLA.

## Disposition

Evidence is sufficient for the current frozen product. `MAX_BATCH_ROWS=500`
remains a reasonable deliverable ceiling for an explicit synchronous local Batch
workflow on the reference class of desktop: all rows completed, memory stabilized
after model loading, and the active workspace survived and committed across an
artificially short TTL. No corrective product patch or architecture change is
required by this finding.

This conclusion does not authorize PH-006, PH-007, asynchronous execution,
parallel inference, model replacement, quantization, persistence, or other
performance work.

## Reproduce locally

Install the real-model extras and ensure both pinned revisions already exist in
the ignored `model_cache/`, then run from the repository root:

```text
python benchmarks/real_model_capacity.py --confirm-real-model-run --cache-dir model_cache
```

The command forces offline mode and prints privacy-safe JSON. Use `--output` to
retain a local report. Do not commit locally generated reports without a fresh
privacy review. This heavy probe is deliberately absent from ordinary CI.
