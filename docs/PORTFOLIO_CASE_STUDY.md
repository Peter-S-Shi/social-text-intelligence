# Social Text Intelligence V2 — Engineering Case Study

**From text classification to an accountable, local-first desktop workflow**

[Source repository](https://github.com/Peter-S-Shi/social-text-intelligence) · [Windows v2.0.0 release](https://github.com/Peter-S-Shi/social-text-intelligence/releases/tag/v2.0.0) · [Product overview](../README.md)

> **Release scope:** Social Text Intelligence (STI) 2.0.0 is a published, **conditional career-portfolio** release for Windows x64, not an enterprise-certified product. The screenshot gallery uses real Windows Qt widgets populated with synthetic test records and stand-in models. It illustrates the interface, **not measured model accuracy**.

## 1. The problem: a prediction is not a conclusion

Feedback analytics tools make it easy to label text as positive, negative, or emotional. The difficult part is what happens *after* the label appears. A single result can be misleading, a dataset can contain malformed or unsupported records, and a reviewer may disagree with the model. STI is built around that gap between machine output and defensible human interpretation.

The product's central premise is deliberately narrower than a universal NLP platform: **an individual should be able to explore English-language text locally, inspect structured model estimates, keep human judgment separate, and export an auditable account of what occurred.** It does not claim to discover ground-truth feelings, intent, or representative real-world model accuracy.

## 2. What V2 delivers

The released V2 surface is a **native Windows desktop application** built using Python and PySide6/Qt Widgets. A typical workflow is:

1. **Set up models deliberately.** The Windows installer omits model weights. Users choose a verified download of the pinned models or import an existing compatible offline folder. Analysis stays unavailable until the required models are ready.
2. **Create a local project.** Import a CSV, select the text column, validate rows, and retain rejected/failed cases with their reasons rather than silently dropping them.
3. **Analyze text.** Run local sentiment and emotion inference with visible progress; cancellation preserves the existing project state instead of committing partial batch results.
4. **Review the evidence.** Inspect the immutable AI record and independently accept, correct, or mark a human judgment uncertain. Review notes do not silently overwrite machine predictions.
5. **Explore cautiously.** Examine descriptive AI–human agreement, eligible denominators, selected metadata groups, small-sample warnings, and separately authored contextual notes. Export is explicit.

The CLI and loopback-only Flask interfaces are preserved for developer exploration and historical V1 compatibility; **the downloadable V2 product is the Windows desktop**, not a hosted service. V1 Moderation Training and Support Triage were retired from the V2 desktop surface.

## 3. Engineering decisions worth discussing

### Architecture: a desktop interface without business logic locked inside Qt

STI keeps typed contracts and application use cases independent of the presentation framework. The Qt-specific UI depends inward on application/contracts layers; its composition boundary wires infrastructure such as providers and persistence. Local projects use SQLite. This makes workflows more directly testable and allows the CLI/legacy web surfaces to reuse portions of the application and provider design without making them the V2 desktop product.

**Trade-off:** More explicit interfaces and view-model/controller seams are required, but the result is less coupling between UI behavior, storage, and NLP runtime details.

Evidence: [Architecture](ARCHITECTURE.md) · [Core contracts](CONTRACTS.md) · [V2 UI/IA decisions](V2_UI_IA_DECISION.md).

### Trust: the AI record and human decision have different meanings

A review action never rewrites the underlying machine prediction. Human labels, uncertainty, and annotations form a separate record. Agreement is calculated on explicitly eligible reviewed data, not casually marketed as an accuracy percentage. Language warnings and small samples are visible limitations, not hidden inconvenient cases.

**Trade-off:** The interface carries more explanation and state than a single-label dashboard, but retains the difference between a model estimate and a human assertion.

Evidence: [M6 native UI acceptance](V2_M6_ACCEPTANCE.md) · [M8 native UI fidelity](V2_M8_TRACK_B_FIDELITY.md) · [M9 evidence contract](V2_M9_EVIDENCE_CONTRACT.md).

### Data integrity: explicit failure is preferable to partial success

CSV validation distinguishes rejected input from analysis failure. Project-level analysis cancellation does not persist partially processed rows as a supposedly complete result. The engineering record also covers stale-write review protection, local process coordination, explicit export safeguards, and refusal of unsupported operations.

**Trade-off:** Atomic batch cancellation forfeits completed in-memory work from an interrupted run, in exchange for a clear and reviewable commit boundary. Resumable partial commits were intentionally **not** part of the approved V2 scope.

Evidence: [V2 UI/IA decisions, U2](V2_UI_IA_DECISION.md) · [Architecture](ARCHITECTURE.md) · [M8 technical hardening ledger](V2_M8_TRACK_A_LEDGER.md).

### Delivery: publishing a Windows executable is a distinct engineering project

V2 extended a source-level Python app into a reproducible Windows installer workflow. The frozen application uses a pinned toolchain and is shipped without user projects or model weights. The final release binds an application version, exact Git commit, asset size, SHA-256, and a separately published immutable Qt/PySide6 source-material release.

The release was deliberately verified twice: a private draft check before publication and an unauthenticated public-page check afterwards. This matters because a draft can prove its planned metadata, while only a live page can prove that the installer is publicly offered together with the promised source-access link.

Evidence: [Release design and public gate](V2_R4B_RELEASE_GATE.md) · [Published v2.0.0](https://github.com/Peter-S-Shi/social-text-intelligence/releases/tag/v2.0.0) · [Qt/PySide6 source-access release](https://github.com/Peter-S-Shi/social-text-intelligence/releases/tag/sources-qt-6.11.2).

## 4. What is demonstrably delivered — and what is not

| Verified or reported scope | Evidence boundary |
| --- | --- |
| Public Windows v2.0.0 installer, bound to commit `819e048c399799ed78da83c5711ed3b40d5c4caf` | Published GitHub Release, single 726,691,694-byte asset, SHA-256 on the Release page. |
| Native Results, Review, Agreement and Insights views | Committed M8 captures from actual Windows Qt widgets using synthetic records/providers. |
| Release engineering and CI | Main-commit Python 3.11/3.12/3.13 and UAT-companion checks were reported successful; release gate separately verified the public release. |
| Packaged application smoke test | Owner-reported PASS; it is **not** a full formal UAT record. |
| Signing and remaining icon observations | Unsigned/SmartScreen risk accepted by Owner; two S5 icon-evidence gaps retained as accepted limitations. |
| Representative-domain model evaluation, full Windows UAT and assistive-technology acceptance | **Not completed / not claimed.** The project does not present its synthetic example scores as performance metrics. |

The LGPL/third-party source-access work is an owner-assessed compliance effort with documented residual limitations; it is **not** an independent legal certification. See [Third-Party Notices](../THIRD_PARTY_NOTICES.md), [Release-2 license decisions](V2_R2_LICENSE_DECISIONS.md) and [M9 exit gate](V2_M9_EXIT_GATE.md).

## 5. What this project demonstrates to an engineering reviewer

STI is evidence of reasoning about system boundaries, state and failure semantics, human-computer interaction, local privacy, and release integrity. Its strongest design choice is not the classifier itself; it is **making the model's output inspectable and contestable throughout the workflow**. The shipped result is a downloadable desktop application and a public source repository, with visible limitations instead of inflated claims.

**Further reading:** [README](../README.md) · [Architecture](ARCHITECTURE.md) · [Product Discovery](V2_PRODUCT_DISCOVERY.md) · [Development](DEVELOPMENT.md) · [Privacy](PRIVACY.md).
