# 功能完整性人工审计 / Feature Complete Manual Audit

This is the canonical, append-only decision record for the Feature Complete
Review. The Chinese section comes first and the English section follows. Both
sections use the same stable `FCR-XXX` identifiers.

---

# 中文

## 1. 当前状态与使用方法

- 当前阶段：**Feature Complete Review（功能完备审查）**
- Feature Freeze：**尚未开始**
- Release readiness：**否**
- 操作型逐项测试记录：
  [Manual QA](../manual_review_questionnaire.html)
- 当前项目状态：[PROJECT_STATUS.md](../PROJECT_STATUS.md)

每个发现必须单独建立一个 `FCR-XXX` 项目，在开发前完成分类。不得删除、
重新编号或静默改写历史项目；后续变化追加到该项目的“决定记录”中。

## 2. Decision Class 与 Decision

`Decision Class` 表示该发现属于哪个生命周期治理层级，只允许以下四类：

| Decision Class | 含义 |
| --- | --- |
| `MUST_ADD_BEFORE_FREEZE` | 缺失内容阻碍冻结，需明确批准后加入当前版本 |
| `REMOVE_MERGE_HIDE_SIMPLIFY` | 在冻结前收紧、合并、隐藏或移除现有范围 |
| `HARDENING` | 不扩展功能边界的缺陷、可用性、可访问性、隐私、错误状态或一致性改进 |
| `DEFER_NEXT_VERSION` | 有价值但属于未来版本的扩展 |

`Decision` 是独立字段，用来记录具体结果，例如：

- `Add before freeze`
- `Keep as-is`
- `Keep and harden`
- `Simplify`
- `Merge`
- `Hide from primary navigation`
- `Remove`
- `Defer to next version`
- `Reject proposal`

状态使用 `OPEN`、`APPROVED`、`IMPLEMENTED`、`REJECTED`、`DEFERRED` 或
`VERIFIED`。Decision Class、Decision 和状态不得互相替代。

## 3. 固定审计项目格式

```text
Basic Information / 基本信息
- ID: FCR-XXX
- 标题:
- 创建/更新日期:
- 核查者代号:
- 核查版本与 SHA:
- 当前生命周期阶段:
- 相关工作流:

Current Behavior / 当前行为
- 当前可见行为:
- 相关 contract、文档或产品承诺:

Manual Observation / 人工观察
- 操作步骤:
- 实际观察:
- 合成证据或截图引用:
- 人工核查结果:

User Impact / 用户影响
- 受影响的用户或工作流:
- 影响程度与出现条件:

Core Assessment / 核心评估
- 是否符合当前版本目的:
- 是否影响 Feature Freeze:
- 是否涉及隐私、安全、数据完整性、可访问性或误导风险:

Decision / 决定
- Decision Class:
- Decision:
- Status:

Rationale / 理由
- 当前版本理由:
- 被拒绝或延后的替代方案:

Implementation Scope / 实施范围
- In scope:
- Out of scope:
- 需要更新的文档、测试或 QA 项:

Acceptance Criteria / 验收标准
- 可验证标准:
- 必须通过的自动化与人工检查:

Risks and Regression Scope / 风险与回归范围
- 主要风险:
- 受影响模块:
- 必须重跑的回归:

Git / PR Record / Git 与 PR 记录
- Branch:
- Commit:
- PR:
- CI result:

Final Outcome / 最终结果
- 最终交付行为:
- 验证结果:
- 关闭日期:
- 后续事项:
```

## 4. 初始功能审计清单

以下项目是待人工执行的初始范围，不预先宣告通过。

| ID | 审计主题 | 必须核查的决定 | 初始状态 |
| --- | --- | --- | --- |
| FCR-001 | 启动与本地边界 | 安装、离线启动、loopback、限制和数据生命周期是否清楚 | OPEN |
| FCR-002 | 顶层导航 | 所有主要工作流是否可发现且层级一致 | OPEN |
| FCR-003 | 直接文本输入 | 空白、超长、英文与不支持语言的反馈是否可恢复 | OPEN |
| FCR-004 | Sentiment 输出 | 标签、分数、置信度、模型和 revision 是否透明 | OPEN |
| FCR-005 | Emotion 输出 | native/compact、多标签阈值和 neutral 语义是否明确 | OPEN |
| FCR-006 | 模型限制 | 输出是否避免心理诊断、客观真相或确定性暗示 | OPEN |
| FCR-007 | Batch 预览 | UTF-8、文本列选择、metadata 和限制是否可理解 | OPEN |
| FCR-008 | Batch 局部失败 | 合法行、无效行和 provider 失败是否逐行保留 | OPEN |
| FCR-009 | Batch 筛选与导出 | 状态、错误、provenance 和可选 native 字段是否可审计 | OPEN |
| FCR-010 | Human Review 队列 | 仅可审阅记录、导航和进度是否正确 | OPEN |
| FCR-011 | 独立人工判断 | accept/correct/uncertain 与 AI 字段是否始终分离 | OPEN |
| FCR-012 | Review 汇总与导出 | 分母、agreement、时间和公式保护是否正确 | OPEN |
| FCR-013 | Insights 分组 | 只使用受信 metadata，不从文本推断群体 | OPEN |
| FCR-014 | Insights 指标 | raw counts、eligible denominator、sample warning 和视角是否一致 | OPEN |
| FCR-015 | Context Notes | 人工来源、UTC 时间、删除和非标签语义是否明确 | OPEN |
| FCR-016 | Insight 导出 | audit metadata、失败行分组、opt-in 和 no-store 是否完整 | OPEN |
| FCR-017 | Moderation 来源 | synthetic policy、reference provenance 和 mock 边界是否诚实 | OPEN |
| FCR-018 | Moderation 决定 | structural error 与 guidance warning 是否真正分离 | OPEN |
| FCR-019 | Moderation 会话 | first/final 决定、反馈、限制和清理是否可审计 | OPEN |
| FCR-020 | Moderation 隐私导出 | 用户文本及上下文是否默认排除、仅显式 opt-in 包含 | OPEN |
| FCR-021 | Triage 来源与 draft | guide、ticket provenance、draft 与无 mock 状态是否清楚 | OPEN |
| FCR-022 | Triage finalize/revision | 原子完成、immutable first decision 和 revision 是否正确 | OPEN |
| FCR-023 | Triage mock 与汇总 | 可见性、unavailable 排除及各指标分母是否正确 | OPEN |
| FCR-024 | Triage 隐私导出 | 各 workspace 上下文类别是否独立 opt-in | OPEN |
| FCR-025 | 隐私与本地状态 | 日志、过期、清理、no-store 和无静默持久化是否一致 | OPEN |
| FCR-026 | 公式注入保护 | 所有用户可控 CSV 字段是否安全转义 | OPEN |
| FCR-027 | 键盘与可访问性 | 焦点、标签、错误定位和主要表单是否可键盘操作 | OPEN |
| FCR-028 | 响应式布局 | 窄屏、表格、导航和关键操作是否仍可使用 | OPEN |
| FCR-029 | 错误与空状态 | 无 token、过期、空结果和非法输入是否提供恢复路径 | OPEN |
| FCR-030 | 文档一致性 | README、Charter、contracts、privacy 与实际行为是否一致 | OPEN |
| FCR-031 | 当前版本范围 | 是否存在必须添加、移除、合并、隐藏或简化的能力 | OPEN |
| FCR-032 | 延后范围 | French、long-form、connectors、persistence 等是否明确隔离 | OPEN |
| FCR-033 | 本地模型缓存冗余 | 固定模型能否在不复制权重或产生未审计转换 revision 的情况下离线运行 | VERIFIED |

## 5. Feature decision index

此索引汇总已分类决定；详细证据仍保留在对应 `FCR-XXX` 项目中。

| ID | Decision Class | Decision | 状态 | 简要理由 | 实施/验证引用 |
| --- | --- | --- | --- | --- | --- |
| FCR-033 | `HARDENING` | Keep and harden | `VERIFIED` | 清除重复缓存，并固定已审计的 sentiment 权重格式；无产品或模型输出变化 | provider 回归、完整质量检查及真实离线双模型测试 |

### FCR-033 — 本地模型缓存冗余

**Basic Information / 基本信息**

- ID: FCR-033
- 标题: 本地 Hugging Face 模型缓存去重与 sentiment 权重格式固定
- 创建/更新日期: 2026-08-09
- 核查者代号: Codex technical audit
- 核查版本与 SHA: 基于 `84fc819f981a8beb33589b6a3a1d74c7bb9b511b` 的 `fix/model-cache-deduplication`
- 当前生命周期阶段: Feature Complete Review
- 相关工作流: Sentiment、Emotion、本地模型加载

**Current Behavior / 当前行为**

- 当前可见行为: 产品行为不变；两个 provider 继续使用原有固定模型与 revision。
- 相关 contract、文档或产品承诺: 本地执行、明确模型 provenance、固定 immutable revision、缓存不进入 Git。

**Manual Observation / 人工观察**

- 操作步骤: 比较缓存文件大小、内容摘要、文件身份、revision 引用与模型张量；在清理后运行真实离线双模型集成测试。
- 实际观察: GoEmotions 的 snapshot 与 blob 是内容相同的两个物理文件；Cardiff sentiment 另有 Transformers 自动转换产生的 Safetensors PR revision，张量与固定 `.bin` 权重一致但不属于批准 revision。
- 合成证据或截图引用: 无用户数据；验证仅使用仓库合成测试文本。
- 人工核查结果: 技术核查通过；缓存已去重，固定 revision 离线推理通过。

**User Impact / 用户影响**

- 受影响的用户或工作流: 本机首次下载过模型的开发与人工核查环境。
- 影响程度与出现条件: 仅占用额外磁盘空间；不改变分析结果。Windows 无符号链接权限时，Hugging Face 会复制 snapshot 文件；Transformers 可能为 `.bin` 自动创建转换 revision。

**Core Assessment / 核心评估**

- 是否符合当前版本目的: 是，保持 local-first 且减少无用缓存。
- 是否影响 Feature Freeze: 属于冻结前可安全完成的 hardening，不构成新功能。
- 是否涉及隐私、安全、数据完整性、可访问性或误导风险: 强化供应链 provenance；不涉及用户数据。

**Decision / 决定**

- Decision Class: `HARDENING`
- Decision: Keep and harden
- Status: `VERIFIED`

**Rationale / 理由**

- 当前版本理由: 删除可证明冗余的本地权重，并阻止已知的自动转换重复出现。
- 被拒绝或延后的替代方案: 不切换到未单独审计的自动转换 Safetensors revision；官方 Safetensors 必须按新 immutable revision 重新审计。

**Implementation Scope / 实施范围**

- In scope: 显式加载固定 `.bin`；provider 回归；本地缓存去重；模型审计、状态与日志更新。
- Out of scope: 新模型、新 revision、标签或分数变化、依赖升级、缓存管理 UI、持久化。
- 需要更新的文档、测试或 QA 项: `MODEL_AUDIT.md`、provider 单元测试、本审计记录、`PROJECT_STATUS.md`、`DEVLOG.md`。

**Acceptance Criteria / 验收标准**

- 可验证标准: GoEmotions snapshot 为指向相同 blob 的符号链接；多余 sentiment conversion revision 不存在；固定模型可真实离线加载。
- 必须通过的自动化与人工检查: 完整测试/质量套件、模型加载回归、真实离线 sentiment 与 combined-model 集成测试、Git 隐私检查。

**Risks and Regression Scope / 风险与回归范围**

- 主要风险: 错删固定权重或让运行时重新下载/转换。
- 受影响模块: Cardiff sentiment runtime 与本机 `model_cache`。
- 必须重跑的回归: provider 单元测试、全套测试、两个真实模型的离线集成测试。

**Git / PR Record / Git 与 PR 记录**

- Branch: `fix/model-cache-deduplication`
- Commit: Draft PR branch head（以 GitHub 为准）
- PR: Draft PR #14 from `fix/model-cache-deduplication`
- CI result: 创建 PR 后由 GitHub Actions 记录；本地验收已通过。

**Final Outcome / 最终结果**

- 最终交付行为: 运行时固定已审计 `.bin`，本地缓存移除两个重复物理权重副本。
- 验证结果: VERIFIED；未改变模型、revision、标签、分数或产品 contract。
- 关闭日期: 2026-08-09
- 后续事项: 继续 FCR-001–FCR-032 的人工功能核查。

## 6. Feature Freeze 决定格式

```text
Feature Freeze decision:
Decision date:
Reviewed version and SHA:
Decision: PASS / DO NOT PASS
Open current-version blockers:
Approved exceptions:
Deferred next-version items:
Required regression:
Approver:
Evidence:
```

Feature Freeze 只能通过明确记录产生。完成 Milestone 10、完成本清单或没有已知
缺陷都不能自动代表冻结通过。

## 7. Codex 维护规则

1. 新发现使用下一个永久 `FCR-XXX` ID。
2. 一个项目只记录一个可独立决定的问题。
3. 不删除或重写历史结论；在“决定记录”中追加变化。
4. 每项必须分别记录四选一 Decision Class 和具体 Decision。
5. add/remove/merge/hide/simplify/reject/defer 都必须同步更新本文件的索引。
6. 批准的实现必须引用 PR/commit、验收检查和验证结果。
7. 每个 coherent lifecycle PR 必须更新 `PROJECT_STATUS.md`。
8. Freeze 后若扩展功能，必须先记录正式 reopening 决定并要求完整回归。
9. 只使用合成证据；不得加入真实用户文本、身份信息、本机路径或私有导出。

---

# English

## 1. Current state and use

- Current phase: **Feature Complete Review**
- Feature Freeze: **Not started**
- Release readiness: **No**
- Repeatable operational checklist:
  [Manual QA](../manual_review_questionnaire.html)
- Current project state: [PROJECT_STATUS.md](../PROJECT_STATUS.md)

Create one `FCR-XXX` item for each finding and classify it before development.
Never delete, renumber, or silently rewrite a historical item; append later
changes to its decision record.

## 2. Decision classes

`Decision Class` records the lifecycle-governance level of a finding. Only
these four top-level classes are valid:

| Decision class | Meaning |
| --- | --- |
| `MUST_ADD_BEFORE_FREEZE` | Add an approved missing capability that blocks freeze |
| `REMOVE_MERGE_HIDE_SIMPLIFY` | Tighten, merge, hide, or remove existing scope before freeze |
| `HARDENING` | Improve defects, usability, accessibility, privacy, error states, or consistency without expanding the feature boundary |
| `DEFER_NEXT_VERSION` | Preserve valuable expansion outside the current-version freeze |

`Decision` is a separate field for the specific outcome:

- `Add before freeze`
- `Keep as-is`
- `Keep and harden`
- `Simplify`
- `Merge`
- `Hide from primary navigation`
- `Remove`
- `Defer to next version`
- `Reject proposal`

Statuses are `OPEN`, `APPROVED`, `IMPLEMENTED`, `REJECTED`, `DEFERRED`, or
`VERIFIED`. Decision Class, Decision, and status are separate fields.

## 3. Fixed audit-item format

```text
Basic Information
- ID: FCR-XXX
- Title:
- Created/updated date:
- Reviewer alias:
- Reviewed version and SHA:
- Current lifecycle phase:
- Affected workflow:

Current Behavior
- Current visible behavior:
- Relevant contract, documentation, or product promise:

Manual Observation
- Steps:
- Actual observation:
- Synthetic evidence or screenshot reference:
- Manual result:

User Impact
- Affected users or workflows:
- Severity and conditions:

Core Assessment
- Current-version fit:
- Feature Freeze impact:
- Privacy, security, data-integrity, accessibility, or misleading-risk impact:

Decision
- Decision Class:
- Decision:
- Status:

Rationale
- Current-version rationale:
- Rejected or deferred alternatives:

Implementation Scope
- In scope:
- Out of scope:
- Documentation, tests, or QA items to update:

Acceptance Criteria
- Verifiable criteria:
- Required automated and manual checks:

Risks and Regression Scope
- Main risks:
- Affected modules:
- Required regression:

Git / PR Record
- Branch:
- Commit:
- PR:
- CI result:

Final Outcome
- Delivered behavior:
- Validation result:
- Closed date:
- Follow-up:
```

## 4. Initial feature audit checklist

These are the same canonical items as the Chinese checklist. They do not
predeclare a pass.

| ID | Audit topic | Required decision | Initial status |
| --- | --- | --- | --- |
| FCR-001 | Startup and local boundary | Are installation, offline startup, loopback binding, limits, and data lifecycle clear? | OPEN |
| FCR-002 | Top-level navigation | Are all major workflows discoverable and consistently organized? | OPEN |
| FCR-003 | Direct text input | Are blank, oversized, English, and unsupported-language outcomes recoverable? | OPEN |
| FCR-004 | Sentiment output | Are labels, scores, confidence, model, and revision transparent? | OPEN |
| FCR-005 | Emotion output | Are native/compact, multi-label threshold, and neutral semantics explicit? | OPEN |
| FCR-006 | Model limitations | Does output avoid psychological, objective-truth, or certainty implications? | OPEN |
| FCR-007 | Batch preview | Are UTF-8 input, text-column selection, metadata, and limits understandable? | OPEN |
| FCR-008 | Batch partial failure | Are valid rows, invalid rows, and provider failures preserved separately? | OPEN |
| FCR-009 | Batch filters and export | Are status, errors, provenance, and optional native fields auditable? | OPEN |
| FCR-010 | Human Review queue | Are only reviewable records included with correct navigation and progress? | OPEN |
| FCR-011 | Independent human judgment | Do accept/correct/uncertain remain separate from AI fields? | OPEN |
| FCR-012 | Review summary and export | Are denominators, agreement, timestamps, and formula safety correct? | OPEN |
| FCR-013 | Insight grouping | Is grouping limited to trusted metadata without text-derived group inference? | OPEN |
| FCR-014 | Insight metrics | Are raw counts, eligible denominators, sample warnings, and perspectives consistent? | OPEN |
| FCR-015 | Context Notes | Are human authorship, UTC time, deletion, and non-label semantics explicit? | OPEN |
| FCR-016 | Insight export | Are audit metadata, failed-row grouping, opt-ins, and no-store complete? | OPEN |
| FCR-017 | Moderation sources | Are synthetic policy, reference provenance, and mock boundaries honest? | OPEN |
| FCR-018 | Moderation decisions | Are structural errors and guidance warnings behaviorally separate? | OPEN |
| FCR-019 | Moderation sessions | Are first/final decisions, feedback, limits, and clearing auditable? | OPEN |
| FCR-020 | Moderation privacy export | Is user context excluded by default and included only by explicit opt-in? | OPEN |
| FCR-021 | Triage sources and drafts | Are guide/ticket provenance, draft, and no-mock states clear? | OPEN |
| FCR-022 | Triage finalize/revision | Are atomic finalization, immutable first decision, and revisions correct? | OPEN |
| FCR-023 | Triage mock and summary | Are visibility, unavailable exclusions, and metric denominators correct? | OPEN |
| FCR-024 | Triage privacy export | Is each workspace context category independently opt-in? | OPEN |
| FCR-025 | Privacy and local state | Are logging, expiry, clearing, no-store, and no silent persistence consistent? | OPEN |
| FCR-026 | Formula-injection protection | Is every user-controlled CSV field safely escaped? | OPEN |
| FCR-027 | Keyboard and accessibility | Are focus, labels, error location, and major forms keyboard-operable? | OPEN |
| FCR-028 | Responsive layout | Do narrow screens, tables, navigation, and critical actions remain usable? | OPEN |
| FCR-029 | Error and empty states | Do missing tokens, expiry, empty results, and invalid input offer recovery? | OPEN |
| FCR-030 | Documentation consistency | Do README, Charter, contracts, privacy, and behavior agree? | OPEN |
| FCR-031 | Current-version scope | Must any capability be added, removed, merged, hidden, or simplified? | OPEN |
| FCR-032 | Deferred scope | Are French, long-form, connectors, persistence, and other expansion isolated? | OPEN |
| FCR-033 | Local model-cache redundancy | Can pinned models run offline without duplicate weights or an unaudited conversion revision? | VERIFIED |

Do not mark an item passed from automated coverage alone. Record its manual
evidence and disposition.

## 5. Feature decision index

| ID | Decision Class | Decision | Status | Short rationale | Implementation/verification reference |
| --- | --- | --- | --- | --- | --- |
| FCR-033 | `HARDENING` | Keep and harden | `VERIFIED` | Remove redundant cache artifacts and pin the audited sentiment weight format without product or model-output changes | Provider regression, full quality suite, and real offline two-model tests |

### FCR-033 — Local model-cache redundancy

**Basic Information**

- ID: FCR-033
- Title: Deduplicate the local Hugging Face model cache and pin the sentiment weight format
- Created/updated: 2026-08-09
- Reviewer alias: Codex technical audit
- Reviewed version and SHA: `fix/model-cache-deduplication`, based on `84fc819f981a8beb33589b6a3a1d74c7bb9b511b`
- Current lifecycle phase: Feature Complete Review
- Related workflows: Sentiment, Emotion, and local model loading

**Current Behavior**

- Visible behavior: Product behavior is unchanged; both providers retain their approved pinned model and revision.
- Contract/document promise: Local execution, explicit model provenance, immutable revisions, and no tracked cache artifacts.

**Manual Observation**

- Steps: Compared size, digest, file identity, revision references, and model tensors; ran real offline two-model integration tests after cleanup.
- Observation: The GoEmotions snapshot and blob were identical physical copies. Cardiff sentiment also had an auto-converted Safetensors PR revision whose tensors matched the pinned `.bin` but whose revision was outside the approval.
- Synthetic evidence: Repository-authored synthetic test text only; no user data.
- Result: Technical review passed; the cache is deduplicated and pinned-revision offline inference passes.

**User Impact**

- Affected users/workflows: Local development and manual-review environments that downloaded the models.
- Impact: Extra disk consumption only; no analysis-result change. Hugging Face can copy snapshot files when Windows symlinks are unavailable, and Transformers can create a conversion revision for `.bin` weights.

**Core Assessment**

- Current-version fit: Yes; preserves local-first behavior while removing unnecessary cache storage.
- Feature Freeze impact: Safe pre-freeze hardening, not a feature addition.
- Privacy/security/integrity/accessibility/misleading risk: Strengthens supply-chain provenance and uses no user data.

**Decision**

- Decision Class: `HARDENING`
- Decision: Keep and harden
- Status: `VERIFIED`

**Rationale**

- Current-version rationale: Remove proven redundant local weights and prevent the known auto-conversion duplicate from recurring.
- Rejected/deferred alternative: Do not switch to an independently unaudited auto-converted Safetensors revision; any official Safetensors revision needs a new immutable-revision audit.

**Implementation Scope**

- In scope: Explicit pinned `.bin` loading, provider regression, local cache repair, and model-audit/status/log updates.
- Out of scope: New models, revisions, labels, score changes, dependency updates, cache UI, or persistence.
- Documentation/tests/QA: `MODEL_AUDIT.md`, provider unit test, this audit record, `PROJECT_STATUS.md`, and `DEVLOG.md`.

**Acceptance Criteria**

- Verifiable criteria: GoEmotions snapshot symlinks to the identical blob; the extra sentiment conversion revision is absent; pinned models load in real offline tests.
- Required checks: Full test/quality suite, model-loading regression, real offline sentiment and combined-model integration tests, and Git privacy review.

**Risks and Regression Scope**

- Main risk: Removing the pinned weight or causing a download/conversion at runtime.
- Affected modules: Cardiff sentiment runtime and the machine-local `model_cache`.
- Required regression: Provider unit tests, full suite, and offline integration with both real models.

**Git / PR Record**

- Branch: `fix/model-cache-deduplication`
- Commit: Draft PR branch head (authoritative in GitHub)
- PR: Draft PR #14 from `fix/model-cache-deduplication`
- CI result: GitHub Actions records it after PR creation; local acceptance passed.

**Final Outcome**

- Delivered behavior: Runtime pins the audited `.bin`; the local cache no longer stores two redundant physical weight copies.
- Validation: VERIFIED; no model, revision, label, score, or product-contract change.
- Closed: 2026-08-09
- Follow-up: Continue manual review of FCR-001–FCR-032.

## 6. Feature Freeze decision format

```text
Feature Freeze decision:
Decision date:
Reviewed version and SHA:
Decision: PASS / DO NOT PASS
Open current-version blockers:
Approved exceptions:
Deferred next-version items:
Required regression:
Approver:
Evidence:
```

Feature Freeze exists only through this explicit decision. Milestone 10
completion, checklist completion, or the absence of known defects does not pass
the gate automatically.

## 7. Codex maintenance rules

1. Assign the next permanent `FCR-XXX` ID to each new finding.
2. Keep one independently decidable issue per item.
3. Never delete or rewrite history; append changes to the decision record.
4. Record one of the four Decision Class values and a separate specific
   Decision for every item.
5. Update the index for every add, remove, merge, hide, simplify, reject, or
   defer decision.
6. Link approved implementation to its PR/commit, acceptance check, and
   validation result.
7. Update `PROJECT_STATUS.md` in every coherent lifecycle PR.
8. After freeze, record a formal reopening decision before feature expansion
   and require full regression.
9. Use synthetic evidence only; never add real user text, identities,
   machine-specific paths, or private exports.
