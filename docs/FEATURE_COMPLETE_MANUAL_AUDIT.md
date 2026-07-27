# Feature Complete Manual Audit / 功能完备人工审计

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

## 2. 决定分类

| 决定类别 | 含义 |
| --- | --- |
| `ACCEPT_AS_IS` | 当前行为符合本版本目标，保留不变 |
| `DEFECT` | 现有约定或合理预期未实现，需要修复 |
| `MUST_ADD_BEFORE_FREEZE` | 缺失内容阻碍冻结，需明确批准后加入当前版本 |
| `REMOVE` | 当前能力有害、误导或无必要，应移除 |
| `MERGE` | 与另一能力重复，应合并 |
| `HIDE` | 能力保留，但不应作为当前主要入口展示 |
| `SIMPLIFY` | 范围不变，减少步骤、术语或认知负担 |
| `REJECT` | 提议不应实施，并保留拒绝理由 |
| `DEFER_NEXT_VERSION` | 有价值但不属于当前冻结范围 |

状态使用 `OPEN`、`APPROVED`、`IMPLEMENTED`、`REJECTED`、`DEFERRED` 或
`VERIFIED`。分类和状态不得互相替代。

## 3. 固定审计项目格式

```text
ID: FCR-XXX
标题:
范围/工作流:
观察或问题:
证据与复现:
决定类别:
状态:
当前版本理由:
批准的动作:
验收检查:
相关 PR/commit:
决定记录:
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

## 5. Feature decision index

此索引汇总已分类决定；详细证据仍保留在对应 `FCR-XXX` 项目中。

| ID | 决定类别 | 状态 | 简要理由 | 实施/验证引用 |
| --- | --- | --- | --- | --- |
| — | — | — | 尚未完成首次人工审计 | — |

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
4. add/remove/merge/hide/simplify/reject/defer 都必须同步更新本文件的索引。
5. 批准的实现必须引用 PR/commit、验收检查和验证结果。
6. 每个 coherent lifecycle PR 必须更新 `PROJECT_STATUS.md`。
7. Freeze 后若扩展功能，必须先记录正式 reopening 决定并要求完整回归。
8. 只使用合成证据；不得加入真实用户文本、身份信息、本机路径或私有导出。

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

| Decision class | Meaning |
| --- | --- |
| `ACCEPT_AS_IS` | Keep current behavior because it meets current-version goals |
| `DEFECT` | Repair behavior that violates a contract or reasonable expectation |
| `MUST_ADD_BEFORE_FREEZE` | Add an approved missing capability that blocks freeze |
| `REMOVE` | Remove harmful, misleading, or unnecessary behavior |
| `MERGE` | Combine overlapping capabilities |
| `HIDE` | Retain a capability but remove it from primary presentation |
| `SIMPLIFY` | Reduce steps, terminology, or cognitive load without expanding scope |
| `REJECT` | Do not implement the proposal; retain the rationale |
| `DEFER_NEXT_VERSION` | Preserve value while keeping it outside the current freeze |

Statuses are `OPEN`, `APPROVED`, `IMPLEMENTED`, `REJECTED`, `DEFERRED`, or
`VERIFIED`. A decision class and a status are separate fields.

## 3. Fixed audit-item format

```text
ID: FCR-XXX
Title:
Scope/workflow:
Observation or problem:
Evidence and reproduction:
Decision class:
Status:
Current-version rationale:
Approved action:
Acceptance check:
Related PR/commit:
Decision record:
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

Do not mark an item passed from automated coverage alone. Record its manual
evidence and disposition.

## 5. Feature decision index

| ID | Decision class | Status | Short rationale | Implementation/verification reference |
| --- | --- | --- | --- | --- |
| — | — | — | Initial manual audit has not been completed | — |

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
4. Update the index for every add, remove, merge, hide, simplify, reject, or
   defer decision.
5. Link approved implementation to its PR/commit, acceptance check, and
   validation result.
6. Update `PROJECT_STATUS.md` in every coherent lifecycle PR.
7. After freeze, record a formal reopening decision before feature expansion
   and require full regression.
8. Use synthetic evidence only; never add real user text, identities,
   machine-specific paths, or private exports.
