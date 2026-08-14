# 功能完整性人工审计 / Feature Complete Manual Audit

This is the canonical, append-only decision record for the Feature Complete
Review. The Chinese section comes first and the English section follows. Both
sections use the same stable `FCR-XXX` identifiers.

---

# 中文

## 1. 当前状态与使用方法

- 当前阶段：**Product Hardening（产品加固）**
- Feature Freeze：**PASS（2026-08-13 用户明确批准）**
- Release readiness：**否**
- 操作型逐项测试记录：
  [Manual QA](../manual-qa/manual_review_questionnaire.html)
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
| FCR-002 | 顶层导航 | 所有主要工作流是否可发现且层级一致 | VERIFIED |
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
| FCR-030 | 文档一致性 | README、Charter、ROADMAP、Development、Project Status 与 CLI 的职责及当前状态是否一致 | VERIFIED；A7 review 与 final-head CI PASS |
| FCR-031 | 当前版本范围 | 是否存在必须添加、移除、合并、隐藏或简化的能力 | OPEN |
| FCR-032 | 延后范围 | French、long-form、connectors、persistence 等是否明确隔离 | OPEN |
| FCR-033 | 本地模型缓存冗余 | 固定模型能否在不复制权重或产生未审计转换 revision 的情况下离线运行 | VERIFIED |
| FCR-034 | Emotion neutral 阈值回退语义 | neutral 是否明确表示阈值回退，而非最高 raw score | VERIFIED |
| FCR-035 | Batch 筛选后位置 | 筛选后是否返回 Results，而不是页面顶部 | VERIFIED |
| FCR-036 | Batch 清理确认 | 销毁临时关联状态前是否明确警告并确认 | VERIFIED |
| FCR-037 | Human Review 完成提示 | 队列完成是否明确显示 | VERIFIED |
| FCR-038 | Context Note UTC 可见性 | note 卡片是否直接显示 UTC created_at | VERIFIED |
| FCR-039 | Insights 失败分组计数 | 成功、可靠分组失败、未分组失败是否显式分开 | VERIFIED |
| FCR-040 | Triage 无 mock 状态 | 无 mock 时是否明确 unavailable 且不显示误导 copy | VERIFIED |
| FCR-041 | Batch 到 Triage 关联入口 | 正常 UI 是否保留 batch token 进入 Triage | VERIFIED |
| FCR-042 | 分数列表排序 | 分数列表是否需要更强的排序可读性 | OPEN；非 blocker |
| FCR-043 | 说明与错误信息层级 | 次要说明、警告、错误的视觉层级是否足够清楚 | OPEN；非 blocker |
| FCR-044 | 嵌套工作流返回主界面 | Triage 四个内部界面及同类深层页面是否有明确主界面返回链接 | VERIFIED；人工复测通过 |
| FCR-045 | 临时 Batch 状态完整性 | 容量、TTL 与 active analysis 是否可能静默销毁或丢失现有工作 | VERIFIED；PR #18 correction CI 通过 |
| FCR-046 | 完整输入推理真实性 | 合法长文本是否可能被模型静默截断并作为整篇分析返回 | VERIFIED；behavioral candidate review 与 CI 通过 |
| FCR-047 | 全局 HTTP request-body 边界 | 异常大的 form / multipart request 是否会在字段验证或临时状态操作前统一拒绝 | VERIFIED；behavioral candidate review 与 CI 通过 |
| FCR-048 | 真实模型 Batch 容量与性能证据 | 500 行真实双模型分析是否可完成、内存稳定且跨 TTL 安全提交 | VERIFIED；A4 离线 CPU probe 证据充分 |
| FCR-049 | 并发 workspace mutation 完整性 | stale workspace mutation 是否可能静默覆盖已接受的新状态 | VERIFIED；A5 behavioral review 与 CI PASS |
| FCR-050 | 本地浏览器安全边界 | 非可信 Host、跨源 unsafe request 或缺失安全 headers 是否可能越过 loopback browser boundary | VERIFIED；A6 code review、CI 与 real-browser smoke PASS |

## 5. Feature decision index

此索引汇总已分类决定；详细证据仍保留在对应 `FCR-XXX` 项目中。

| ID | Decision Class | Decision | 状态 | 简要理由 | 实施/验证引用 |
| --- | --- | --- | --- | --- | --- |
| FCR-030 | `HARDENING` | Keep and harden | `VERIFIED` | 以 Project Status 为唯一 live ledger，分离 Charter、Roadmap、README、Development 与 CLI 职责，避免当前态重复漂移 | behavioral SHA `cce3133d7a2dcf9d1d06fe2e11a190c79dd22a1c` review PASS；PR #24 reviewed-head CI PASS |
| FCR-033 | `HARDENING` | Keep and harden | `VERIFIED` | 清除重复缓存，并固定已审计的 sentiment 权重格式；无产品或模型输出变化 | provider 回归、完整质量检查及真实离线双模型测试 |
| FCR-034 | `HARDENING` | Keep and harden | `VERIFIED` | 明确 neutral threshold fallback，不改模型语义 | 定向回归与 final-candidate 人工复测通过 |
| FCR-035 | `HARDENING` | Keep and harden | `VERIFIED` | 筛选后回到 Results anchor | Batch route 回归与人工复测通过 |
| FCR-036 | `HARDENING` | Keep and harden | `VERIFIED` | 清理前要求显式确认并说明关联状态 | Batch clear route 回归与委托技术复测通过 |
| FCR-037 | `HARDENING` | Keep and harden | `VERIFIED` | 明确显示 review queue 完成 | Review route 回归与人工复测通过 |
| FCR-038 | `HARDENING` | Keep and harden | `VERIFIED` | note 卡片显示 timezone-aware UTC created_at | Insights route 回归与人工复测通过 |
| FCR-039 | `HARDENING` | Keep and harden | `VERIFIED` | 显式分开可靠分组失败与未分组失败，不猜测 | Insights service/route 回归与人工复测通过 |
| FCR-040 | `HARDENING` | Keep and harden | `VERIFIED` | 无 mock 明确 unavailable，assisted copy 按可用性显示 | Triage route 回归与人工复测通过 |
| FCR-041 | `HARDENING` | Keep and harden | `VERIFIED` | Batch Results 增加保留 token 的 Triage 入口 | Batch/Triage 关联回归与人工隐私复测通过 |
| FCR-042 | `HARDENING` | Keep and harden | `OPEN` | 分数排序是独立可读性改进，不阻碍当前 contract | 后续 Product Hardening |
| FCR-043 | `HARDENING` | Keep and harden | `OPEN` | 说明/错误层级是跨页面视觉改进，当前可恢复性未失败 | 后续 Product Hardening |
| FCR-044 | `HARDENING` | Keep and harden | `VERIFIED` | 复测证明缺失返回路径造成重大操作困难；所有嵌套工作流增加明确 home link | exact behavioral SHA 人工复测与 CI 通过 |
| FCR-045 | `HARDENING` | Keep and harden | `VERIFIED` | 容量阻止新建而非驱逐；active analysis 跨 TTL 原子写回或明确失败；error render 保留配置限制 | Product Hardening Batch A1 targeted/full regression；PR #18 correction head CI PASS |
| FCR-046 | `HARDENING` | Keep and harden | `VERIFIED` | 以真实 tokenizer 编码长度拒绝超出 pinned 模型预算的完整输入，禁止静默截断与 partial-text success | Product Hardening Batch A2 behavioral SHA review PASS；PR #19 CI PASS |
| FCR-047 | `HARDENING` | Keep and harden | `VERIFIED` | 以 3 MiB Flask 全局 ceiling 在 form/multipart 解析和状态操作前统一 413；CSV 2 MiB payload limit 保持独立 | Product Hardening Batch A3 behavioral SHA review PASS；PR #20 CI PASS |
| FCR-048 | `HARDENING` | Keep and harden | `VERIFIED` | opt-in 真实离线双模型 probe 证明 500 行完成、加载后 RSS 稳定、active lease 跨短 TTL 原子写回；无需产品 patch | [A4 容量证据](REAL_MODEL_CAPACITY_EVIDENCE.md)；PR #21 review/CI PASS 并已合并 |
| FCR-049 | `HARDENING` | Keep and harden | `VERIFIED` | 共享 store-level atomic mutation 始终基于 current state；安全独立变更串行保留，不可合并 one-shot 竞争明确返回 409 | behavioral SHA `a3ec11b674c11148d66be73475b43d0796329a54` review PASS；PR #22 behavioral-head CI PASS |
| FCR-050 | `HARDENING` | Keep and harden | `VERIFIED` | 只信任 loopback Host；unsafe methods 执行 lightweight same-origin 检查；全部响应采用严格 self-only CSP 与统一安全 headers | behavioral SHA `1a2d25fafc532215b45cf8d6310e8e1b2b16140d` review/CI PASS；real-browser smoke PASS |

### 2026-08-13 最新反馈分类

**Git 交付更新：** FCR-034–041 的实现 commit 为 `31c16c0`，位于
`hardening/pre-freeze-manual-qa` 的 Draft PR #16。下方创建时标为“待填写”的
Git/PR 占位记录由本更新取代；最终远程 head 与 CI 状态以 PR checks 为准。

| 反馈 | 分类 | 处理 |
| --- | --- | --- |
| `manual-qa/`、可追踪样本/指南、本地 results 隔离 | QA infrastructure / governance | 本轮建立规范目录；`results/` 由仓库 `.gitignore` 保护 |
| 问卷侧边栏、上一/下一 Session | QA infrastructure / governance | 本轮更新 tracked questionnaire；不创建 FCR |
| 一键启动 BAT | Release / RC ergonomics | 用户明确要求后已实现为项目根目录相对路径 launcher；不创建 FCR，不改变产品 contract |
| 输入包含箭头时分数略有变化 | QA guidance | 输入字符已变化，分数小幅变化属预期；补充 exact-input 指南，不创建 FCR |
| 分数列表排序 | Product FCR / Hardening | FCR-042，非 blocker |
| 说明/错误文字视觉层级 | Product FCR / Hardening | FCR-043，非 blocker |
| Triage/嵌套工作流返回主界面 | Product FCR / Hardening | FCR-044；pre-freeze blocker 已修并在 exact behavioral SHA 上人工复测通过 |

### 2026-08-13 既有 FCR disposition map

- `VERIFIED / Keep as-is`: FCR-001–002, 004, 006–013, 016, 018–020,
  022, 025, 027–029, 032–033。
- `VERIFIED / Keep and harden`: FCR-034–041 与 FCR-044；final-candidate
  人工或委托技术复测均已完成。
- `OPEN verification`: FCR-003、005、014、015、017、021、023、026、031。
  FCR-002 已由 FCR-044 final-head smoke test 重新关闭；V-01 已由 exact tested
  behavioral SHA 满足，V-03–V-06 已由自动化/静态/委托技术复测覆盖。
- `VERIFIED / Keep and harden`: FCR-030；Product Hardening Batch A7 已完成
  review 与 reviewed-head CI，PH-008 已关闭。
- `OPEN / non-blocking Hardening`: FCR-042–043。
- `VERIFIED / Product Hardening`: FCR-045；exact correction SHA 的 targeted/full
  local validation 与 PR #18 remote CI 均通过，PR #18 已合并到 main
  `1b36fe8c024823c1f4829621a7bcc733b2915c93`。

### FCR-030 — 文档与 CLI 当前状态一致性

- **Basic Information / 基本信息:** 生命周期文档、贡献者说明与 `sti about`；Product Hardening PH-008；状态 `VERIFIED`。
- **Current Behavior / 当前行为:** `PROJECT_STATUS.md` 是唯一 canonical live execution state；Roadmap 维护可变生命周期计划；Charter 仅维护稳定边界；README 提供简洁当前概览；Development 维护贡献纪律；CLI 仅报告安装版本、已完成功能边界与能力，并指向 Project Status。
- **Manual Observation / 人工观察:** A7 审计发现 README、Roadmap、Charter 与 CLI 仍把 Feature Complete Review 或 Feature Freeze 描述为待进行，Project Status 仍把已合并 PR #23 写成下一操作。
- **User Impact / 用户影响:** 冲突的当前态会误导开发、审查和发布判断，并使每次生命周期转换需要重复修正文案。
- **Core Assessment / 核心评估:** PH-008 与既有 FCR-030 是同一 documentation-consistency 根因；不建立 FCR-051。
- **Decision / 决定:** Class `HARDENING`; Decision `Keep and harden`; Status `VERIFIED`。
- **Rationale / 理由:** 将易变事实集中到一个 live ledger，比在 Charter 或 CLI 中复制 gate/PR/SHA 更能持续保持真实；历史记录仍保留当时正确的状态。
- **Implementation Scope / 实施范围:** 修正当前 README、ROADMAP、Charter、Development、Project Status 与 `sti about`；同步 A6 merge 和 FCR-050 `VERIFIED`；不改 contracts/privacy/architecture 中不存在的矛盾。
- **Acceptance Criteria / 验收标准:** 当前 surfaces 对 0.10.0、Milestones 1–10 complete、FCR Completed、Freeze PASS、Product Hardening、Manual Acceptance/RC Not started、Release readiness No 一致；CLI 不声称 freeze pending，也不冒充 live ledger；Manual QA 指向 tracked canonical path。
- **Risks and Regression Scope / 风险与回归范围:** CLI about 输出、当前态职责、tracked Markdown 相对链接、canonical Manual QA 路径、历史记录不被误改；不涉及模型或 workflow behavior。
- **Git / PR Record / Git 与 PR 记录:** `hardening/product-hardening-cycle`；Product Hardening Batch A7 PR #24；behavioral candidate `cce3133d7a2dcf9d1d06fe2e11a190c79dd22a1c` lifecycle/CLI consistency review PASS；reviewed head `371b41bec0c6418bc07748a36d34e46dd4392664` Python 3.11/3.12/3.13 final-head CI PASS。
- **Final Outcome / 最终结果:** targeted consistency regression、review 与 reviewed-head CI 全部通过，FCR-030 关闭为 `VERIFIED`。`PROJECT_STATUS.md` 保持唯一 canonical live execution ledger；FCR-045–050 保持 `VERIFIED`，Feature Freeze 保持 PASS，PH-009 未开始。

### FCR-034–FCR-041 — 固定审计记录

以下每项均保持完整固定模板；共同核查日期为 2026-08-13，核查者代号为
manual reviewer + Codex engineering review，基线为 `main` 的 `dc70857`，阶段为
Feature Complete Review。分支、candidate commit、PR 与 CI 在本轮 Git 交付后填写。

#### FCR-034 — Emotion neutral threshold-fallback 语义

- **Basic Information / 基本信息:** Direct analysis；状态 `IMPLEMENTED`。
- **Current Behavior / 当前行为:** UI 现在明确说明：没有 non-neutral compact score 达到阈值时，dominant `neutral` 是 fallback，并不声称 raw neutral score 最高；模型、revision、scores、阈值不变。
- **Manual Observation / 人工观察:** 原 `direct-multilabel` 为 N/A，观察到语义歧义；需在 candidate 上重测 fallback 与已有 non-empty secondary case。
- **User Impact / 用户影响:** 防止把 fallback 当成最高概率 emotion，影响解释透明度。
- **Core Assessment / 核心评估:** 当前版本目标内；冻结前 blocker；涉及误导风险，不涉及隐私/安全。
- **Decision / 决定:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`。
- **Rationale / 理由:** 修正文案即可恢复既有 contract；拒绝调阈值、换模型或改标签。
- **Implementation Scope / 实施范围:** 仅结果页解释与 targeted route test；不做 emotion 扩展。
- **Acceptance Criteria / 验收标准:** fallback 与 raw-score ranking 可区分；secondary/native/threshold 语义不变；自动化通过并人工复测。
- **Risks and Regression Scope / 风险与回归范围:** Direct template；重跑 direct route 与全套回归。
- **Git / PR Record / Git 与 PR 记录:** `hardening/pre-freeze-manual-qa`; candidate/PR/CI 待 Git 交付。
- **Final Outcome / 最终结果:** 定向回归与 final-candidate 人工复测通过；状态 `VERIFIED`。

#### FCR-035 — Batch 筛选后结果位置

- **Basic Information / 基本信息:** Batch filter；状态 `IMPLEMENTED`。
- **Current Behavior / 当前行为:** 筛选表单提交返回 `#results` anchor，不改变筛选或数据。
- **Manual Observation / 人工观察:** 原测试通过但每次回到页顶；本项为非 blocker UX hardening。
- **User Impact / 用户影响:** 减少重复滚动，不影响结果正确性。
- **Core Assessment / 核心评估:** 当前范围内、非冻结 blocker、无隐私/数据风险。
- **Decision / 决定:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`。
- **Rationale / 理由:** 可与同页修复安全捆绑；拒绝重新设计 Batch UI。
- **Implementation Scope / 实施范围:** 仅 anchor 与 route regression。
- **Acceptance Criteria / 验收标准:** 筛选后定位 Results；filter semantics 不变。
- **Risks and Regression Scope / 风险与回归范围:** Batch navigation；重跑 Batch routes。
- **Git / PR Record / Git 与 PR 记录:** 当前 hardening 分支；candidate/PR/CI 待填写。
- **Final Outcome / 最终结果:** 已实现，非 Freeze blocker。

#### FCR-036 — 临时 Batch 清理确认

- **Basic Information / 基本信息:** Batch destructive action；状态 `IMPLEMENTED`。
- **Current Behavior / 当前行为:** 清理表单说明 batch、review、insights 与关联状态会删除，要求显式 checkbox；无确认时返回 400 且保留状态。
- **Manual Observation / 人工观察:** 原 `batch-clear` 失败：点击后立即销毁。
- **User Impact / 用户影响:** 防止误删临时工作成果；其他 workspace 不受影响。
- **Core Assessment / 核心评估:** 当前版本 blocker；涉及数据完整性，不扩展持久化。
- **Decision / 决定:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`。
- **Rationale / 理由:** 显式确认符合既有临时生命周期；拒绝 undo、数据库或历史记录。
- **Implementation Scope / 实施范围:** 表单确认、route validation、targeted tests。
- **Acceptance Criteria / 验收标准:** 未确认不删除；确认后旧 token 失效；无关 workspace 保留。
- **Risks and Regression Scope / 风险与回归范围:** Batch clear 与 linked state；全套 route 回归。
- **Git / PR Record / Git 与 PR 记录:** 当前 hardening 分支；candidate/PR/CI 待填写。
- **Final Outcome / 最终结果:** 自动化与委托技术复测通过；状态 `VERIFIED`。

#### FCR-037 — Human Review 完成提示

- **Basic Information / 基本信息:** Human Review queue；状态 `IMPLEMENTED`。
- **Current Behavior / 当前行为:** 全部 reviewable records 完成后显示明确 completion status。
- **Manual Observation / 人工观察:** 原 queue 可用但只能通过 Next 不再前进推断完成。
- **User Impact / 用户影响:** 提高流程结束可发现性；不改 decision 或 denominator。
- **Core Assessment / 核心评估:** 非 blocker hardening，无隐私/安全风险。
- **Decision / 决定:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`。
- **Rationale / 理由:** 小范围反馈补强；拒绝新增 workflow 状态机。
- **Implementation Scope / 实施范围:** Review template 与 route regression。
- **Acceptance Criteria / 验收标准:** 完成状态明确；已保存 decisions 不变。
- **Risks and Regression Scope / 风险与回归范围:** Review navigation/summary。
- **Git / PR Record / Git 与 PR 记录:** 当前 hardening 分支；candidate/PR/CI 待填写。
- **Final Outcome / 最终结果:** 已实现，非 Freeze blocker。

#### FCR-038 — Context Note UTC timestamp 可见性

- **Basic Information / 基本信息:** Insights Context Notes；状态 `IMPLEMENTED`。
- **Current Behavior / 当前行为:** 当前 note 卡直接显示 timezone-aware UTC `created_at`。
- **Manual Observation / 人工观察:** 原行为可用，但 reviewer 未能直接确认 UTC semantics。
- **User Impact / 用户影响:** 提升 provenance/auditability；不改 note 内容或生命周期。
- **Core Assessment / 核心评估:** 非 blocker hardening；涉及审计透明度。
- **Decision / 决定:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`。
- **Rationale / 理由:** 复用已存在 contract 字段；拒绝 editing history/persistence。
- **Implementation Scope / 实施范围:** Insights template 与 route regression。
- **Acceptance Criteria / 验收标准:** UI 清楚显示 ISO timestamp 和 UTC；export 保持不变。
- **Risks and Regression Scope / 风险与回归范围:** Context Notes UI/export。
- **Git / PR Record / Git 与 PR 记录:** 当前 hardening 分支；candidate/PR/CI 待填写。
- **Final Outcome / 最终结果:** 已实现，非 Freeze blocker。

#### FCR-039 — Insights 失败与未分组计数

- **Basic Information / 基本信息:** Insights grouping；状态 `IMPLEMENTED`。
- **Current Behavior / 当前行为:** 每组显示 successful、可靠归属 failed；另显示本 grouping 无法可靠归属的 failed 总数，并明确不猜测。
- **Manual Observation / 人工观察:** 原 `insights-failures` 失败：只能从 eligible/total 推断。
- **User Impact / 用户影响:** 防止失败行在 group context 中看似消失。
- **Core Assessment / 核心评估:** 冻结前 blocker；涉及 denominator/data-integrity 透明度。
- **Decision / 决定:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`。
- **Rationale / 理由:** 仅展示既有安全 grouping 规则；拒绝从文本猜群组。
- **Implementation Scope / 实施范围:** Insights card 与 assigned/unassigned route regression。
- **Acceptance Criteria / 验收标准:** 三类 count 明确；raw metrics/denominators/filters 不变。
- **Risks and Regression Scope / 风险与回归范围:** Insights group summaries/export consistency。
- **Git / PR Record / Git 与 PR 记录:** 当前 hardening 分支；candidate/PR/CI 待填写。
- **Final Outcome / 最终结果:** 自动化与人工复测通过；状态 `VERIFIED`。

#### FCR-040 — Support Triage explicit no-mock state

- **Basic Information / 基本信息:** Triage ticket/mock；状态 `IMPLEMENTED`。
- **Current Behavior / 当前行为:** 无 mock 时显示 `Mock unavailable`；只有 mock 存在且 assisted 时才显示 visible deterministic mock 提示；表单不预填。
- **Manual Observation / 人工观察:** 原 `triage-mock-source` 与 `triage-visibility` 失败，copy 暗示不存在的 suggestion。
- **User Impact / 用户影响:** 消除 mock provenance/availability 误导。
- **Core Assessment / 核心评估:** 冻结前 blocker；涉及透明度，不涉及真实模型。
- **Decision / 决定:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`。
- **Rationale / 理由:** 修正条件渲染即可；拒绝生成/推断缺失 mock。
- **Implementation Scope / 实施范围:** Triage template；Independent/Assisted no-mock regressions。
- **Acceptance Criteria / 验收标准:** unavailable 明确；visible/hidden counts 仍排除 unavailable；人类表单不预填。
- **Risks and Regression Scope / 风险与回归范围:** Triage source, visibility, summary。
- **Git / PR Record / Git 与 PR 记录:** 当前 hardening 分支；candidate/PR/CI 待填写。
- **Final Outcome / 最终结果:** 自动化与两项原 QA 人工复测通过；状态 `VERIFIED`。

#### FCR-041 — Batch Results linked Support Triage entry

- **Basic Information / 基本信息:** Batch-to-Triage workflow；状态 `IMPLEMENTED`。
- **Current Behavior / 当前行为:** Batch Results 提供带当前 batch token 的 `Prepare Support Triage`；成功解析记录即使 NLP provider 失败也可成为 snapshot。
- **Manual Observation / 人工观察:** 原 `triage-workspace` 被缺失入口阻塞，并阻塞 workspace privacy Phase B。
- **User Impact / 用户影响:** 恢复已存在 linked workflow 的正常用户入口。
- **Core Assessment / 核心评估:** 冻结前 blocker；涉及可发现性与 privacy verification dependency。
- **Decision / 决定:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`。
- **Rationale / 理由:** 后端已支持 token；拒绝新 ticket 来源、connector 或 persistence。
- **Implementation Scope / 实施范围:** Batch link、linked workspace route tests、provider-failed parsed row regression。
- **Acceptance Criteria / 验收标准:** main/edge batch 可从 UI 进入；失败推理行仍可选；signals/review/notes/metadata 仅作 supporting context。
- **Risks and Regression Scope / 风险与回归范围:** Batch/Triage token、expiry、privacy exports。
- **Git / PR Record / Git 与 PR 记录:** 当前 hardening 分支；candidate/PR/CI 待填写。
- **Final Outcome / 最终结果:** 自动化入口/资格测试与 V-04 委托技术复测通过；状态 `VERIFIED`。

### FCR-042–FCR-044 — 最新产品发现

#### FCR-042 — 分数列表排序

- **Basic Information / 基本信息:** 跨 Direct/结果分数列表；2026-08-13；状态 `OPEN`。
- **Current Behavior / 当前行为:** 分数按现有 contract/label 顺序展示，未提供按值排序。
- **Manual Observation / 人工观察:** reviewer 建议排序以提高扫描效率。
- **User Impact / 用户影响:** 轻度可读性影响，不影响数值、标签或可审计性。
- **Core Assessment / 核心评估:** 当前功能可用，非 Freeze blocker，无隐私/安全风险。
- **Decision / 决定:** Class `HARDENING`; Decision `Keep and harden`; Status `OPEN`。
- **Rationale / 理由:** 是独立产品可读性问题；不机械并入 blocker batch。
- **Implementation Scope / 实施范围:** 后续统一评估排序、键盘/读屏与 provenance；本轮不改。
- **Acceptance Criteria / 验收标准:** 若实施，排序规则清楚且 native/compact 身份不丢失。
- **Risks and Regression Scope / 风险与回归范围:** 结果渲染、截图/文档、可访问性。
- **Git / PR Record / Git 与 PR 记录:** 未实施；无 commit/PR/CI。
- **Final Outcome / 最终结果:** 保留到 Product Hardening，Feature Freeze 前无需关闭。

#### FCR-043 — 说明与错误信息视觉层级

- **Basic Information / 基本信息:** 跨页面信息层级；2026-08-13；状态 `OPEN`。
- **Current Behavior / 当前行为:** 说明、限制、warning 与 error 可见，但部分视觉权重相近。
- **Manual Observation / 人工观察:** reviewer 建议更明确地区分说明性文字与错误。
- **User Impact / 用户影响:** 轻度扫描/恢复效率影响；原 QA 未显示错误路径不可恢复。
- **Core Assessment / 核心评估:** 非 blocker accessibility/UX hardening，无数据风险。
- **Decision / 决定:** Class `HARDENING`; Decision `Keep and harden`; Status `OPEN`。
- **Rationale / 理由:** 属于跨页面设计系统调整，需独立回归，不塞入窄修复。
- **Implementation Scope / 实施范围:** 后续颜色、层级、ARIA/contrast 评估；本轮不改。
- **Acceptance Criteria / 验收标准:** warning/error/secondary copy 可区分且满足键盘/对比度要求。
- **Risks and Regression Scope / 风险与回归范围:** 全站 CSS、响应式、可访问性。
- **Git / PR Record / Git 与 PR 记录:** 未实施；无 commit/PR/CI。
- **Final Outcome / 最终结果:** 保留到 Product Hardening，Feature Freeze 前无需关闭。

#### FCR-044 — Triage 返回与默认导航

- **Basic Information / 基本信息:** Triage ticket navigation；2026-08-13；状态 `OPEN`。
- **Current Behavior / 当前行为:** ticket 可完成并返回 workspace，但默认位置/返回效率可改进。
- **Manual Observation / 人工观察:** reviewer 请求更直接的 return/default navigation。
- **User Impact / 用户影响:** 重复 ticket 操作增加少量导航成本，核心 lifecycle 不受阻。
- **Core Assessment / 核心评估:** 非 blocker workflow ergonomics，无隐私/完整性风险。
- **Decision / 决定:** Class `HARDENING`; Decision `Keep and harden`; Status `OPEN`。
- **Rationale / 理由:** 与 FCR-041 的缺失入口不同，是独立的完成后导航改进。
- **Implementation Scope / 实施范围:** 后续评估 return target、focus/anchor；本轮不改。
- **Acceptance Criteria / 验收标准:** 返回位置可预测，不改变 draft/final/revision 状态。
- **Risks and Regression Scope / 风险与回归范围:** Triage routes、browser history、focus。
- **Git / PR Record / Git 与 PR 记录:** 未实施；无 commit/PR/CI。
- **Final Outcome / 最终结果:** 保留到 Product Hardening，Feature Freeze 前无需关闭。

**2026-08-13 Decision update / 决定更新：** PR #16 人工复测确认 Triage 的
Source & Guide、Workspace、Ticket、Summary 四个内部界面均没有可发现的主应用
返回链接，并造成重大操作困难；Moderation 的深层 Session/Results 也存在同类结构。
这推翻了“非 blocker”的初始影响评估，但不产生新 FCR ID，因为根因仍是同一个
嵌套工作流全局导航缺口。FCR-044 现为 pre-freeze blocker，Status 更新为
`IMPLEMENTED`：所有非主页面使用明确、可键盘操作的
`← Social Text Intelligence home` 链接，Triage/Moderation 深层页面将全局导航与
工作流 subnav 分开。该时点 FCR-002 重新打开 verification；targeted route
regression 通过，人工返回测试尚未完成。下方 final verification update 已取代
这一中间状态。

**Git / PR update：** FCR-044 implementation commit `67eaa33`，Draft PR #16；
最终 head 与 CI 以 PR checks 为准。

**2026-08-13 Final verification update / 最终验证更新：** 在 tested behavioral
SHA `16acb0f5931b022b57f0c5cdbe4501973aa3ad11` 上完成 final-head smoke
test，FCR-044 人工复测 PASS；四个 Triage 内部界面与同类深层页面均可明确返回
Social Text Intelligence home，临时 workspace 状态保持。FCR-044 Status 更新为
`VERIFIED`，FCR-002 navigation verification 重新关闭为 `VERIFIED`。V-01 已由
该 exact SHA 满足。后续治理文档 commit 不改变 behavioral candidate。

### FCR-045 — 临时 Batch 状态完整性

- **Basic Information / 基本信息:** Batch process-memory store；2026-08-13；状态 `VERIFIED`。
- **Current Behavior / 当前行为:** Phase 0 基线在容量满时静默删除最早到期 workspace；长时间分析先读取、后计算、再忽略 `replace()` 失败，可能把未保存结果表现为成功路径。
- **Manual Observation / 人工观察:** Product Hardening Phase 0 technical audit 以容量探针、TTL/write-back 探针及路由检查复现两种失败模式。
- **User Impact / 用户影响:** 未导出的 Batch、Review、Insights 及其关联来源可能无提示失效；已完成的本地推理可能没有保存却被误认为成功。
- **Core Assessment / 核心评估:** release-blocking data-integrity hardening；不重新打开 Feature Freeze，不新增功能域。
- **Decision / 决定:** Class `HARDENING`; Decision `Keep and harden`; Status `VERIFIED`。
- **Rationale / 理由:** FCR-036 只覆盖用户主动 clear 的确认；PH-001 与 PH-002 共享 Batch store 缺少容量阻止与 active-operation 状态保证的根因，因此合并为一个新的永久 finding，而不重复或改写 FCR-036。
- **Implementation Scope / 实施范围:** 容量达到上限时以 409 阻止新 upload；active analysis 使用独占 lease，在同步请求期间免于 TTL purge，并只允许持有当前 lease 的结果原子提交；冲突写回明确返回 409；仍为 process-memory、TTL、无数据库/后台任务。
- **Acceptance Criteria / 验收标准:** `capacity+1` 不删除既有 workspace；过期的非 active workspace 正常清除；active analysis 跨 TTL 可提交；清理/重复分析冲突被阻止；写回失败不显示成功；显式 clear 释放容量；既有 Review、Insights 与 linked workspace 不因新 upload 消失。
- **Risks and Regression Scope / 风险与回归范围:** Batch store lifecycle、upload/analyze/clear routes、Review/Insights 可达性、linked Moderation/Triage 来源；不触及模型、阈值、privacy export 或其他 hardening finding。
- **Git / PR Record / Git 与 PR 记录:** `hardening/product-hardening-cycle`；PR #18 已合并到 main SHA `1b36fe8c024823c1f4829621a7bcc733b2915c93`；初始 A1 SHA `163af519e37eaff10c2b481dbbfc49a6e38ae39c` remote CI PASS；error-render correction/tested behavioral SHA `729318c6c253ea8eee8351e766bbcfe7a335c297` remote CI PASS。
- **Final Outcome / 最终结果:** 最小状态完整性修复与窄 error-render regression 已验证；targeted Batch routes 6 passed，full suite 132 passed / 2 opt-in real-model tests skipped，Ruff、strict MyPy、compileall、pip check 通过，PR #18 Python 3.11/3.12/3.13 CI 全绿；FCR-045 关闭为 `VERIFIED`。

### FCR-046 — 完整输入推理真实性

- **Basic Information / 基本信息:** Cardiff sentiment、SamLowe emotion、combined analysis、Direct、Batch 与 CLI；2026-08-13；状态 `VERIFIED`。
- **Current Behavior / 当前行为:** Phase 0 基线的两个 Transformers runtime 均传入 `truncation=True, max_length=512`，合法但 encoded sequence 超限的文本会被静默截断，随后仍生成看似覆盖完整输入的成功结果。
- **Manual Observation / 人工观察:** Product Hardening Phase 0 代码审计定位到两个 provider 的相同 truncation 路径；真实离线模型探针确认 SamLowe tokenizer 声明 512，而 pinned Cardiff tokenizer 使用 unknown-limit sentinel、模型配置提供 514 个 RoBERTa position slots。
- **User Impact / 用户影响:** 用户可能把部分文本的 sentiment/emotion scores、Review、Insights 与 export 当作整篇文本分析，破坏结果真实性与失败行语义。
- **Core Assessment / 核心评估:** release-blocking correctness/data-integrity hardening；不重新打开 Feature Freeze，不新增 long-form 能力。
- **Decision / 决定:** Class `HARDENING`；Decision `Keep and harden`；Status `VERIFIED`。
- **Rationale / 理由:** FCR-003、FCR-006 与 FCR-008 分别覆盖输入恢复、模型限制说明与 Batch 局部失败，但没有任何一项定义所有 provider/入口共享的完整输入成功 invariant；PH-003 因此建立为新的永久 FCR-046，而不是重复局部 finding。
- **Implementation Scope / 实施范围:** 两个 pinned provider 使用经审计的 512-token encoded-input budget；tokenizer 启用 special tokens、关闭 truncation 并对真实 encoded length 校验；combined 在任一模型推理前预检所有 required providers；Direct/CLI 明确拒绝，Batch 仅该 row 失败且 export 不写入 AI scores/provenance。20,000-character application safety ceiling 保持独立。
- **Acceptance Criteria / 验收标准:** encoded length 512 成功、513 明确 `model_input_too_long`；special tokens 纳入计数；Cardiff、SamLowe、combined、Direct、mixed Batch、export 与 CLI 一致；既有未超限输出 label/score/provenance 不变；不新增 chunking、aggregation、summarization、模型、revision、threshold、持久化或成功结果 truncation 字段。
- **Risks and Regression Scope / 风险与回归范围:** tokenizer/model metadata compatibility、Cardiff documented preprocessing、双 provider 预检顺序、首次模型加载、Batch row isolation/export、CLI error handling 与 UI copy；PH-004 及其他 hardening 不在范围内。
- **Git / PR Record / Git 与 PR 记录:** `hardening/product-hardening-cycle`；behavioral candidate `31b5e6cf7fc6d551bb72680900976595008d9d7c`；PR #19 已合并到 main SHA `1c9764ba7bcd45b07a07a93077b86070e358a0ab`；behavioral review、closure-head CI 与 post-merge CI PASS。
- **Final Outcome / 最终结果:** A2 complete-input 合同、targeted/full regression、真实离线模型 smoke、behavioral code review 与 PR CI 均通过；FCR-046 在 exact behavioral SHA 上关闭为 `VERIFIED`。Feature Freeze 保持 PASS；PH-004 未开始。

### FCR-047 — 全局 HTTP request-body 边界

- **Basic Information / 基本信息:** Local Flask Direct、Batch、Review、Insights、Moderation 与 Triage HTTP POST boundary；2026-08-13；状态 `VERIFIED`。
- **Current Behavior / 当前行为:** Phase 0 基线只在解析后执行 20,000-character Direct limit、2 MiB CSV payload limit 及各 workflow 字段限制；在此之前没有统一 request-body ceiling，异常大的 form/multipart body 可进入框架解析。
- **Manual Observation / 人工观察:** Product Hardening Phase 0 代码审计确认 app config 未设置 `MAX_CONTENT_LENGTH` 或等价框架边界，且各 blueprint/route 分别读取 `request.form` / `request.files`。
- **User Impact / 用户影响:** 即使应用只绑定 loopback，异常大的本地请求仍可能在业务验证前造成不必要的内存压力；若错误页回显内容或绕过 no-store，还会破坏隐私合同。
- **Core Assessment / 核心评估:** release-risk availability/privacy hardening；不重新打开 Feature Freeze，不扩展为 Web-security redesign。
- **Decision / 决定:** Class `HARDENING`；Decision `Keep and harden`；Status `VERIFIED`。
- **Rationale / 理由:** FCR-025 管理 privacy/local-state 一致性，FCR-029 管理既有 error/recovery states；两者均未定义 form/multipart 解析前的跨入口容量根因。PH-004 因此建立为永久 FCR-047，而不是改写或复制局部 finding。
- **Implementation Scope / 实施范围:** 默认 `MAX_CONTENT_LENGTH=3 MiB`；比 2 MiB CSV payload limit 多 1 MiB（50%）multipart/form encoding 余量；CLI 可配置且必须大于 CSV limit。`before_request` 在 route/state logic 前拒绝已声明超限 body，Flask 在读取阶段执行同一 ceiling；统一固定文案 413 handler 继承 no-store/no-cache。
- **Acceptance Criteria / 验收标准:** oversized Direct、Batch multipart、Review、Insights note 与 Triage decision 均返回 413；不回显原始内容、traceback 或内部路径；不创建/修改 ephemeral state；正常请求保持原语义；2 MiB CSV byte limit 继续独立；不实现 CSP、Origin/Host policy、账户、远程部署、数据库、后台任务或持久化。
- **Risks and Regression Scope / 风险与回归范围:** Flask request parsing、multipart overhead、所有 POST route、413 headers/copy、Batch/Review/Insights/Moderation/Triage stores、CLI configuration 与 CSV limit distinction；PH-005、PH-007 及其他 hardening 不在范围内。
- **Git / PR Record / Git 与 PR 记录:** `hardening/product-hardening-cycle`；behavioral candidate `def0577feb3c43d4e9e81577003c43da821b6ba2`；PR #20 已合并到 main SHA `552be0012300ce0d40714b739bbb9e27248c8bca`；behavioral review、closure-head CI 与 post-merge CI PASS。
- **Final Outcome / 最终结果:** A3 HTTP request-body boundary、targeted/full regression、behavioral code review 与 PR CI 均通过；FCR-047 在 exact behavioral SHA 上关闭为 `VERIFIED`。Feature Freeze 保持 PASS；PH-005 后续由 FCR-048 证据关闭。

### FCR-048 — 真实模型 Batch 容量与性能证据

- **Basic Information / 基本信息:** 固定 Cardiff sentiment + SamLowe emotion 的本地 CPU Batch 容量；2026-08-13；状态 `VERIFIED`。
- **Current Behavior / 当前行为:** frozen product 以单进程同步方式逐行运行两个真实模型，Batch 上限 500 行；A1 active-analysis lease 保护长运行写回，但此前没有 1/50/500 行真实模型的耗时、吞吐、RSS 与 TTL 证据。
- **Manual Observation / 人工观察:** Windows 11、Python 3.12.13、Intel i7-12700H、约 16 GB RAM、PyTorch 2.13 CPU-only 环境，以本地 cache 强制 offline。初始化到首个结果 3.626 秒；warm 1/50/500 行分别 0.075/3.763/39.636 秒，500/500 成功、0 失败；峰值 RSS 约 0.99 GiB，加载后到 500 行仅增长约 2.97 MiB。
- **User Impact / 用户影响:** 缺乏证据会让 500 行承诺、同步等待和内存需求无法进入 RC 判断；实测证明定义明确的短 social-text workload 在目标桌面环境可交付，同时避免把该结果误写为所有硬件/文本长度的 SLA。
- **Core Assessment / 核心评估:** measurement/evidence hardening；不修改 frozen product behavior，不预设或实施性能优化。
- **Decision / 决定:** Class `HARDENING`；Decision `Keep and harden`；Status `VERIFIED`。
- **Rationale / 理由:** FCR-045 只定义 Batch 容量阻止与 active-operation 状态完整性，FCR-046 只定义完整输入推理真实性；均不提供真实模型容量、吞吐或 RSS 的发布证据。PH-005 因此建立为永久 FCR-048，而不是重复已有 finding。
- **Implementation Scope / 实施范围:** 增加普通 CI 不执行的 opt-in offline benchmark harness 与可审计证据；运行 production `AnalysisService`、`analyze_batch` 和 `EphemeralBatchStore` lease/write-back；使用 synthetic English fixture；不修改 `src/`、模型、revision、threshold、Batch limit 或 runtime architecture。
- **Acceptance Criteria / 验收标准:** 分开记录冷加载/首推理与 warm 1/50/500；记录环境、吞吐、成功/失败、process RSS；active lease 在 1 秒探针 TTL 下跨期并成功提交；提出具备余量且限定 fixture/profile 的 RC budget；heavy probe 不进入普通 CI。
- **Risks and Regression Scope / 风险与回归范围:** 结果依赖硬件与输入长度，不能外推成全局 SLA；measurement harness、offline cache、两个 pinned revision、顺序 Batch 与 A1 lease 是本项范围；PH-006、PH-007、FCR-042/043、async、parallelism、quantization、GPU 与 persistence 均排除。
- **Git / PR Record / Git 与 PR 记录:** `hardening/product-hardening-cycle`；Product Hardening Batch A4 PR #21 已合并到 main SHA `5778f8f8804c3014f16940af1d7254c202dbcf41`；本地真实 probe、full quality suite、review 与 CI PASS。
- **Final Outcome / 最终结果:** [真实模型容量证据](REAL_MODEL_CAPACITY_EVIDENCE.md)充分支持保留 `MAX_BATCH_ROWS=500`：500 行约 39.636 秒、12.61 rows/s、峰值约 0.99 GiB，所有结果跨探针 TTL 保持并提交。PH-005 关闭为 `VERIFIED`，无需 corrective product work；Feature Freeze 保持 PASS；PH-006 后续由 FCR-049 承载。

### FCR-049 — 并发 workspace mutation 完整性

- **Basic Information / 基本信息:** Batch、Moderation、Triage process-memory workspace 并发写入；2026-08-13；状态 `VERIFIED`。
- **Current Behavior / 当前行为:** A5 前，多条 POST route 会先读取 workspace、在锁外派生完整新对象，再整体 replace；两个请求从同一旧快照出发时，后写入者可能静默擦除先接受的 mutation。
- **Manual Observation / 人工观察:** Phase 0 代码审计发现 Batch column selection、Review/Insights、Moderation 和 Triage 均存在同一 read/derive/replace 根因；确定性 nested interleaving 测试复现了 stale snapshot 风险并验证修复后的最终保存状态。
- **User Impact / 用户影响:** 多 tab、重复提交或并发请求可能丢失 review、note、training decision 或 triage decision，同时界面仍表现为成功，属于 release-blocking data-integrity 风险。
- **Core Assessment / 核心评估:** current hardening correctness/data integrity；不重新打开 Feature Freeze，不增加数据库、后台任务或分布式并发架构。
- **Decision / 决定:** Class `HARDENING`；Decision `Keep and harden`；Status `VERIFIED`。
- **Rationale / 理由:** FCR-045 只覆盖 Batch capacity、TTL 与 active-analysis lease/write-back；它没有承载跨 Batch/Moderation/Triage 的普通 workspace mutation lost-update 根因。PH-006 因此建立为永久 FCR-049，而不是改写或重复 FCR-045。
- **Implementation Scope / 实施范围:** 三个 store 复用单一 atomic mutation primitive：在 store lock 内读取 current workspace、执行纯 mutation callback 并原子保存。保护 Batch selection、Review、持久 Insight selection/note、全部 Moderation state action 与全部 Triage state action。GET navigation、filter、summary、export 和纯 request-local presentation state 不纳入，因为它们不替换持久 workspace。
- **Acceptance Criteria / 验收标准:** 独立 mutation 均保留；one-shot 规则在提交时 current state 上复验；不可安全合并的竞争返回 409；conflict 不破坏新状态；expired/cleared 保持 404；A1 active lease 不被绕过；显式 revision 与 single-tab workflow 保持正常。
- **Risks and Regression Scope / 风险与回归范围:** store lock 中 callback 必须保持纯内存且短时；deterministic tests 验证最终保存状态。process-memory、bounded capacity、TTL、loopback 和无 persistence 边界保持；PH-007、WebSocket、distributed lock、external cache、async、FCR-042/043 均排除。
- **Git / PR Record / Git 与 PR 记录:** `hardening/product-hardening-cycle`；Product Hardening Batch A5 PR #22；behavioral candidate `a3ec11b674c11148d66be73475b43d0796329a54`；current-state mutation/concurrency integrity review PASS；behavioral-head Python 3.11/3.12/3.13 CI PASS；已合并到 main SHA `3a0bb9c9460379b55a6488f966034419e40cf91d`。
- **Final Outcome / 最终结果:** atomic current-state mutation 与明确 409 conflict 已通过 behavioral review 与 CI，FCR-049 在固定 behavioral SHA 上关闭为 `VERIFIED`。本次 closure 仅修改治理文档；FCR-048 保持 `VERIFIED`，Feature Freeze 保持 PASS；PH-007 后续由 FCR-050 承载。

### FCR-050 — 本地浏览器安全边界

- **Basic Information / 基本信息:** loopback Flask Host、unsafe-method same-origin 与全局 response headers；2026-08-14；状态 `VERIFIED`。
- **Current Behavior / 当前行为:** A6 前 CLI 只绑定 `127.0.0.1`，但 Flask 未配置 trusted hosts，unsafe browser POST 没有 Origin/Referer 边界，响应除 no-store/no-cache 外缺少统一 CSP、nosniff、referrer 与 anti-framing headers。
- **Manual Observation / 人工观察:** Phase 0 审计确认所有 CSS/JavaScript 已 self-hosted，唯一严格 CSP 冲突是 Insights 的动态 inline width style；Direct 和全部临时 workflow mutation 都通过普通 browser POST 进入。
- **User Impact / 用户影响:** 即使服务只绑定 loopback，恶意页面仍可能尝试向本地端口发送请求；未验证 Host 或明确跨源 unsafe request 可能触发 inference、改变临时状态，缺失浏览器 headers 也会扩大 framing、MIME sniffing 和资源注入风险。
- **Core Assessment / 核心评估:** release-risk browser boundary hardening；不重新打开 Feature Freeze，不扩展为 authentication、session、TLS、remote deployment 或 production-server security。
- **Decision / 决定:** Class `HARDENING`；Decision `Keep and harden`；Status `VERIFIED`。
- **Rationale / 理由:** FCR-047 仅覆盖 HTTP request-body capacity，FCR-049 仅覆盖已进入业务层后的并发 mutation integrity；均不定义 Host、browser same-origin 或 response security-header 根因。PH-007 因此建立为永久 FCR-050。
- **Implementation Scope / 实施范围:** Flask `TRUSTED_HOSTS` 只接受 `127.0.0.1`/`localhost`；`POST`/`PUT`/`PATCH`/`DELETE` 要求 exact same-origin Origin，Origin 缺失时已有 Referer 必须同源，两者都缺失则按 trusted-Host 后的本地非浏览器请求兼容；全局增加 self-only CSP、`nosniff`、`Referrer-Policy: same-origin`、CSP `frame-ancestors 'none'` 与 `X-Frame-Options: DENY`；把唯一 inline style 改为本地 CSS 控制的原生 progress。
- **Acceptance Criteria / 验收标准:** approved local Host 与 same-origin workflow 正常；非可信 Host 固定 400，显式跨源/`null`/malformed Origin 或不匹配 Referer 固定 403；拒绝发生在 inference、body parsing 与 mutation 前且不回显用户数据/路径；HTML、redirect、error/413、CSV、CSS/JS 均带统一 headers；CSP 无 wildcard、external source、`unsafe-inline`；A3/A5 合同保持。
- **Risks and Regression Scope / 风险与回归范围:** Origin 缺失兼容仅面向 trusted-Host 本地非浏览器客户端，不是远程访问或认证合同；已完成的真实浏览器 smoke 确认 console 无 CSP violation 或 blocked local resource。HSTS、CORS、TLS、LAN、reverse proxy、production WSGI、account/session、CSRF framework、reporting service、后续 PH 与 FCR-042/043 均排除。
- **Git / PR Record / Git 与 PR 记录:** `hardening/product-hardening-cycle`；Product Hardening Batch A6 PR #23；behavioral candidate `1a2d25fafc532215b45cf8d6310e8e1b2b16140d`；Host/same-origin/CSP/security-header code review PASS；behavioral-head Python 3.11/3.12/3.13 CI PASS；real-browser smoke PASS；PR #23 已合并到 main SHA `cfcd13ef582996b8c75aa20524dcc212e2ab8922`。
- **Final Outcome / 最终结果:** trusted Host、same-origin unsafe-method gate、严格统一 headers 与 CSP-compatible template 已通过 review、CI 和真实浏览器 smoke；Direct、Batch/Review、Insights progress/note、Moderation/Triage、CSV 均正常，DevTools Console 无 CSP violation 或 blocked local resource。FCR-050 在固定 behavioral SHA 上关闭为 `VERIFIED`；PR #23 已合并。FCR-049 保持 `VERIFIED`，Feature Freeze 保持 PASS；后续 PH-008 由既有 FCR-030 承载。

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

### 2026-08-13 正式 Feature Freeze 决定

```text
Feature Freeze decision: Social Text Intelligence 0.10.0
Decision date: 2026-08-13
Tested behavioral SHA: 16acb0f5931b022b57f0c5cdbe4501973aa3ad11
Decision: PASS
Governance closure SHA: 2a701f87b167d5a112184b1ffedb4f8f7a12d95e
Open current-version blockers: None
Approved exceptions: FCR-042 and FCR-043 are non-blocking Product Hardening backlog
Deferred next-version items: French/multilingual, long-form/transcripts, connectors, persistence, accounts/shared/cloud, and other approved future expansions
Required regression: Final-head smoke PASS; 127 tests passed and 2 opt-in real-model tests skipped; Ruff, strict MyPy, compileall, pip check, documentation/privacy checks, and GitHub CI passed
Approver: User / project owner
Evidence: PR #16 candidate-specific manual evidence; exact behavioral SHA above; FCR-044/FCR-002 final verification; Python 3.11/3.12/3.13 CI
```

此 PASS 仅冻结上述 tested behavioral SHA。其后的 closure commits 只记录治理与
状态，不是新的 behavioral candidate。FCR-042、FCR-043 留在 Product Hardening
backlog，不阻碍本次 Feature Freeze；Release readiness 仍为 No。

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

- Current phase: **Product Hardening**
- Feature Freeze: **PASS (explicit user approval on 2026-08-13)**
- Release readiness: **No**
- Repeatable operational checklist:
  [Manual QA](../manual-qa/manual_review_questionnaire.html)
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
| FCR-002 | Top-level navigation | Are all major workflows discoverable and consistently organized? | VERIFIED |
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
| FCR-030 | Documentation consistency | Do README, Charter, ROADMAP, Development, Project Status, and CLI responsibilities and current state agree? | VERIFIED; A7 review and final-head CI passed |
| FCR-031 | Current-version scope | Must any capability be added, removed, merged, hidden, or simplified? | OPEN |
| FCR-032 | Deferred scope | Are French, long-form, connectors, persistence, and other expansion isolated? | OPEN |
| FCR-033 | Local model-cache redundancy | Can pinned models run offline without duplicate weights or an unaudited conversion revision? | VERIFIED |
| FCR-034 | Emotion neutral fallback semantics | Is neutral explicit as threshold fallback rather than highest raw score? | VERIFIED |
| FCR-035 | Batch filter result position | Do filters return to Results rather than the page top? | VERIFIED |
| FCR-036 | Batch clear confirmation | Is linked temporary state explained and confirmed before destruction? | VERIFIED |
| FCR-037 | Human Review completion | Is queue completion explicit? | VERIFIED |
| FCR-038 | Context Note UTC visibility | Does the note card expose UTC created_at? | VERIFIED |
| FCR-039 | Insight failure group counts | Are success, reliably assigned failure, and unassigned failure explicit? | VERIFIED |
| FCR-040 | Triage no-mock state | Is unavailable explicit without misleading assisted copy? | VERIFIED |
| FCR-041 | Linked Batch-to-Triage entry | Can normal UI preserve the batch token into Triage? | VERIFIED |
| FCR-042 | Score-list ordering | Would stronger score ordering improve scanability? | OPEN; non-blocking |
| FCR-043 | Explanatory/error hierarchy | Are secondary copy, warnings, and errors visually distinct enough? | OPEN; non-blocking |
| FCR-044 | Nested-workflow return navigation | Do all four Triage internals and comparable deep views expose an explicit application-home link? | VERIFIED; manual retest passed |
| FCR-045 | Ephemeral Batch state integrity | Can capacity, TTL, or active analysis silently destroy or lose existing work? | VERIFIED; PR #18 correction CI passed |
| FCR-046 | Complete-input inference truthfulness | Can valid long text be silently truncated and returned as whole-text analysis? | VERIFIED; behavioral candidate review and CI passed |
| FCR-047 | Global HTTP request-body boundary | Are abnormal form and multipart bodies rejected before field validation or temporary-state operations? | VERIFIED; behavioral candidate review and CI passed |
| FCR-048 | Real-model Batch capacity and performance evidence | Can 500 rows complete with both real models, stable memory, and TTL-safe commit? | VERIFIED; A4 offline CPU probe evidence sufficient |
| FCR-049 | Concurrent workspace mutation integrity | Can a stale workspace mutation silently overwrite newer accepted state? | VERIFIED; A5 behavioral review and CI passed |
| FCR-050 | Local browser security boundary | Can an untrusted Host, cross-origin unsafe request, or missing headers bypass the loopback browser boundary? | VERIFIED; A6 code review, CI, and real-browser smoke passed |

Do not mark an item passed from automated coverage alone. Record its manual
evidence and disposition.

## 5. Feature decision index

| ID | Decision Class | Decision | Status | Short rationale | Implementation/verification reference |
| --- | --- | --- | --- | --- | --- |
| FCR-030 | `HARDENING` | Keep and harden | `VERIFIED` | Make Project Status the only live ledger and separate Charter, Roadmap, README, Development, and CLI responsibilities to prevent repeated current-state drift | behavioral SHA `cce3133d7a2dcf9d1d06fe2e11a190c79dd22a1c` review PASS; PR #24 reviewed-head CI PASS |
| FCR-033 | `HARDENING` | Keep and harden | `VERIFIED` | Remove redundant cache artifacts and pin the audited sentiment weight format without product or model-output changes | Provider regression, full quality suite, and real offline two-model tests |
| FCR-034 | `HARDENING` | Keep and harden | `VERIFIED` | Explain neutral threshold fallback without changing model semantics | Targeted regression and final-candidate manual retest passed |
| FCR-035 | `HARDENING` | Keep and harden | `VERIFIED` | Return filter submissions to the Results anchor | Batch route regression and manual retest passed |
| FCR-036 | `HARDENING` | Keep and harden | `VERIFIED` | Require explicit confirmation and explain linked state | Batch clear regression and delegated technical retest passed |
| FCR-037 | `HARDENING` | Keep and harden | `VERIFIED` | Surface review-queue completion | Review route regression and manual retest passed |
| FCR-038 | `HARDENING` | Keep and harden | `VERIFIED` | Show timezone-aware UTC created_at on note cards | Insights route regression and manual retest passed |
| FCR-039 | `HARDENING` | Keep and harden | `VERIFIED` | Separate reliably grouped and unassigned failures without guessing | Insights service/route regression and manual retest passed |
| FCR-040 | `HARDENING` | Keep and harden | `VERIFIED` | Mark absent mocks unavailable and condition assisted copy | Triage route regression and manual retest passed |
| FCR-041 | `HARDENING` | Keep and harden | `VERIFIED` | Add a Batch Results Triage entry that preserves the token | Linked Batch/Triage regression and manual privacy retest passed |
| FCR-042 | `HARDENING` | Keep and harden | `OPEN` | Score ordering is an independent readability improvement, not a current contract blocker | Later Product Hardening |
| FCR-043 | `HARDENING` | Keep and harden | `OPEN` | Information hierarchy is cross-page visual hardening; recovery behavior did not fail | Later Product Hardening |
| FCR-044 | `HARDENING` | Keep and harden | `VERIFIED` | Retest proved that missing return paths cause material operating difficulty; every nested workflow now has an explicit home link | Exact behavioral SHA manual retest and CI passed |
| FCR-045 | `HARDENING` | Keep and harden | `VERIFIED` | Capacity blocks instead of evicting; active analysis commits atomically across TTL or fails explicitly; error rendering retains configured limits | Product Hardening Batch A1 targeted/full regression; PR #18 correction-head CI PASS |
| FCR-046 | `HARDENING` | Keep and harden | `VERIFIED` | Reject over-budget complete input by real tokenizer length; prohibit silent truncation and partial-text success | Product Hardening Batch A2 behavioral SHA review PASS; PR #19 CI PASS |
| FCR-047 | `HARDENING` | Keep and harden | `VERIFIED` | Apply a 3 MiB Flask-wide ceiling before form/multipart parsing and state operations; keep the 2 MiB CSV payload limit separate | Product Hardening Batch A3 behavioral SHA review PASS; PR #20 CI PASS |
| FCR-048 | `HARDENING` | Keep and harden | `VERIFIED` | An opt-in offline real-model probe demonstrates 500-row completion, stable post-load RSS, and atomic active-lease commit across a short TTL; no product patch is required | [A4 capacity evidence](REAL_MODEL_CAPACITY_EVIDENCE.md); PR #21 review/CI passed and merged |
| FCR-049 | `HARDENING` | Keep and harden | `VERIFIED` | A shared store-level atomic mutation always uses current state; safe independent changes serialize and incompatible one-shot races return an explicit 409 | behavioral SHA `a3ec11b674c11148d66be73475b43d0796329a54` review PASS; PR #22 behavioral-head CI PASS |
| FCR-050 | `HARDENING` | Keep and harden | `VERIFIED` | Trust loopback Hosts only, apply a lightweight same-origin gate to unsafe methods, and give every response strict self-only CSP and security headers | behavioral SHA `1a2d25fafc532215b45cf8d6310e8e1b2b16140d` review/CI PASS; real-browser smoke PASS |

### 2026-08-13 latest-feedback classification

**Git delivery update:** The FCR-034–041 implementation commit is `31c16c0`
in Draft PR #16 from `hardening/pre-freeze-manual-qa`. This update supersedes
the creation-time pending Git/PR placeholders below; the final remote head and
CI status are authoritative in the PR checks.

| Feedback | Classification | Treatment |
| --- | --- | --- |
| `manual-qa/`, tracked samples/guidance, private results | QA infrastructure / governance | Standard structure added; repository `.gitignore` protects `results/` |
| Questionnaire sidebar and previous/next session | QA infrastructure / governance | Tracked questionnaire updated; no FCR created |
| One-click BAT launcher | Release / RC ergonomics | Implemented after explicit user request as a project-relative root launcher; no FCR or product-contract change |
| Small score change after adding arrow characters | QA guidance | The analyzed input changed; document exact-input comparison, no FCR |
| Score-list ordering | Product FCR / Hardening | FCR-042, non-blocking |
| Explanatory/error text hierarchy | Product FCR / Hardening | FCR-043, non-blocking |
| Triage/nested-workflow return to application home | Product FCR / Hardening | FCR-044; pre-freeze blocker corrected and manually passed on the exact behavioral SHA |

### 2026-08-13 existing-FCR disposition map

- `VERIFIED / Keep as-is`: FCR-001–002, 004, 006–013, 016, 018–020,
  022, 025, 027–029, 032–033.
- `VERIFIED / Keep and harden`: FCR-034–041 and FCR-044; final-candidate
  manual or delegated technical retesting is complete.
- `OPEN verification`: FCR-003, 005, 014, 015, 017, 021, 023, 026, 031.
  FCR-002 is re-closed by the FCR-044 final-head smoke test; V-01 is satisfied
  by the exact tested behavioral SHA, and V-03–V-06 are covered by automated,
  static, or delegated technical retest evidence.
- `VERIFIED / Keep and harden`: FCR-030; Product Hardening Batch A7 passed
  review and reviewed-head CI, closing PH-008.
- `OPEN / non-blocking Hardening`: FCR-042–043.
- `VERIFIED / Product Hardening`: FCR-045; targeted/full local validation and
  PR #18 remote CI passed on the exact correction SHA, and PR #18 merged to main
  at `1b36fe8c024823c1f4829621a7bcc733b2915c93`.

### FCR-030 — Documentation and CLI current-state consistency

- **Basic Information:** Lifecycle documents, contributor instructions, and `sti about`; Product Hardening PH-008; status `VERIFIED`.
- **Current Behavior:** `PROJECT_STATUS.md` is the only canonical live execution state. Roadmap owns the mutable lifecycle plan; Charter owns stable boundaries; README provides a concise current overview; Development owns contributor discipline; CLI reports the installed version, completed feature boundary, and capabilities, then points to Project Status.
- **Manual Observation:** The A7 audit found README, Roadmap, Charter, and CLI still describing Feature Complete Review or Feature Freeze as pending, while Project Status still presented merged PR #23 as the next action.
- **User Impact:** Conflicting current state can misdirect development, review, and release decisions and forces repeated wording repairs at each lifecycle transition.
- **Core Assessment:** PH-008 and existing FCR-030 have the same documentation-consistency root cause; FCR-051 is not created.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `VERIFIED`.
- **Rationale:** Concentrating volatile facts in one live ledger is more durable than copying gates, PRs, and SHAs into Charter or CLI. Historical records retain statements that were accurate at the time.
- **Implementation Scope:** Correct current README, ROADMAP, Charter, Development, Project Status, and `sti about`; synchronize the A6 merge and FCR-050 `VERIFIED`; do not churn Contracts, Privacy, or Architecture where no contradiction exists.
- **Acceptance Criteria:** Current surfaces agree on 0.10.0, Milestones 1–10 complete, FCR Completed, Freeze PASS, Product Hardening, Manual Acceptance/RC Not started, and Release readiness No. CLI does not claim freeze pending or impersonate the live ledger. Manual QA uses the tracked canonical path.
- **Risks and Regression Scope:** CLI about output, current-state responsibilities, tracked Markdown relative links, canonical Manual QA path, and preservation of historical records; no model or workflow behavior.
- **Git / PR Record:** `hardening/product-hardening-cycle`; Product Hardening Batch A7 PR #24; behavioral candidate `cce3133d7a2dcf9d1d06fe2e11a190c79dd22a1c` lifecycle/CLI consistency review PASS; reviewed head `371b41bec0c6418bc07748a36d34e46dd4392664` Python 3.11/3.12/3.13 final-head CI PASS.
- **Final Outcome:** Targeted consistency regression, review, and reviewed-head CI all passed, closing FCR-030 as `VERIFIED`. `PROJECT_STATUS.md` remains the only canonical live execution ledger; FCR-045–050 remain `VERIFIED`, Feature Freeze remains PASS, and PH-009 is not started.

### FCR-034–FCR-041 — fixed audit records

Every record below preserves the fixed template. Common review data: date
2026-08-13; reviewer alias manual reviewer + Codex engineering review; baseline
`main` at `dc70857`; phase Feature Complete Review. Branch, candidate commit,
PR, and CI are finalized during Git delivery.

#### FCR-034 — Emotion neutral threshold-fallback semantics

- **Basic Information:** Direct analysis; status `IMPLEMENTED`.
- **Current Behavior:** The UI says dominant `neutral` is a fallback when no non-neutral compact score reaches threshold, not a claim that raw neutral is highest; model, revision, scores, and threshold are unchanged.
- **Manual Observation:** `direct-multilabel` was N/A with an observed ambiguity; retest fallback and an existing non-empty secondary case on the candidate.
- **User Impact:** Prevents misreading fallback as the highest-probability emotion.
- **Core Assessment:** Current-version pre-freeze blocker; misleading-output risk, no privacy/security impact.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`.
- **Rationale:** Copy restores the existing contract; model/threshold/label changes rejected.
- **Implementation Scope:** Result explanation and targeted route tests only; no emotion expansion.
- **Acceptance Criteria:** Fallback and raw ranking are distinguishable; secondary/native/threshold semantics remain intact; automated and manual checks pass.
- **Risks and Regression Scope:** Direct template; direct routes and full regression.
- **Git / PR Record:** `hardening/pre-freeze-manual-qa`; candidate/PR/CI pending delivery.
- **Final Outcome:** Targeted regression and final-candidate manual retest passed; status `VERIFIED`.

#### FCR-035 — Batch filter result-position usability

- **Basic Information:** Batch filter; status `IMPLEMENTED`.
- **Current Behavior:** Filter submission targets `#results` without changing filter/data semantics.
- **Manual Observation:** Original check passed but returned to the page top; non-blocking UX finding.
- **User Impact:** Reduces repeated scrolling; no correctness impact.
- **Core Assessment:** In scope, not a freeze blocker, no privacy/data risk.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`.
- **Rationale:** Safe to bundle with same-page corrections; Batch redesign rejected.
- **Implementation Scope:** Anchor and route regression only.
- **Acceptance Criteria:** Filters return to Results and retain semantics.
- **Risks and Regression Scope:** Batch navigation; Batch route tests.
- **Git / PR Record:** Current hardening branch; candidate/PR/CI pending.
- **Final Outcome:** Implemented; not a Freeze blocker.

#### FCR-036 — Temporary Batch clear confirmation

- **Basic Information:** Batch destructive action; status `IMPLEMENTED`.
- **Current Behavior:** Copy identifies removed batch/review/insight/linked state and requires a checkbox; omission returns 400 and preserves state.
- **Manual Observation:** Original `batch-clear` failed because destruction was immediate.
- **User Impact:** Prevents accidental loss of temporary work; unrelated workspaces remain intact.
- **Core Assessment:** Current-version blocker; data-integrity concern without persistence expansion.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`.
- **Rationale:** Explicit confirmation fits the temporary lifecycle; undo/database/history rejected.
- **Implementation Scope:** Form confirmation, route validation, targeted tests.
- **Acceptance Criteria:** No deletion without confirmation; confirmed token expires; unrelated workspaces remain.
- **Risks and Regression Scope:** Batch clear and linked state; full route regression.
- **Git / PR Record:** Current hardening branch; candidate/PR/CI pending.
- **Final Outcome:** Automated check passed; manual `batch-clear` retest pending.

#### FCR-037 — Human Review completion affordance

- **Basic Information:** Human Review queue; status `IMPLEMENTED`.
- **Current Behavior:** A completion status appears when all reviewable records are reviewed.
- **Manual Observation:** The queue worked but completion was inferred only when Next stopped advancing.
- **User Impact:** Improves workflow-end discoverability without changing decisions/denominators.
- **Core Assessment:** Non-blocking hardening; no privacy/security risk.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`.
- **Rationale:** Narrow feedback addition; new workflow state machine rejected.
- **Implementation Scope:** Review template and route regression.
- **Acceptance Criteria:** Completion is explicit; saved human decisions remain unchanged.
- **Risks and Regression Scope:** Review navigation and summary.
- **Git / PR Record:** Current hardening branch; candidate/PR/CI pending.
- **Final Outcome:** Implemented; not a Freeze blocker.

#### FCR-038 — Context Note UTC timestamp visibility

- **Basic Information:** Insights Context Notes; status `IMPLEMENTED`.
- **Current Behavior:** Each current note card shows timezone-aware UTC `created_at`.
- **Manual Observation:** Note behavior worked, but the reviewer could not directly confirm UTC semantics.
- **User Impact:** Improves provenance/auditability without changing note content/lifecycle.
- **Core Assessment:** Non-blocking hardening; audit-transparency concern.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`.
- **Rationale:** Reuses the existing contract field; editing history/persistence rejected.
- **Implementation Scope:** Insights template and route regression.
- **Acceptance Criteria:** ISO timestamp and UTC are explicit; export remains unchanged.
- **Risks and Regression Scope:** Context Notes UI/export.
- **Git / PR Record:** Current hardening branch; candidate/PR/CI pending.
- **Final Outcome:** Implemented; not a Freeze blocker.

#### FCR-039 — Insight failed/unassigned group counts

- **Basic Information:** Insights grouping; status `IMPLEMENTED`.
- **Current Behavior:** Cards show successful, reliably assigned failed, and grouping-wide unassigned failed counts, with no guessed group.
- **Manual Observation:** Original `insights-failures` failed because users had to infer failures from eligible/total.
- **User Impact:** Prevents failed rows from appearing absent in group context.
- **Core Assessment:** Pre-freeze blocker; denominator/data-integrity transparency.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`.
- **Rationale:** Displays the existing safe grouping rule; text-derived guessing rejected.
- **Implementation Scope:** Insight card and assigned/unassigned route regression.
- **Acceptance Criteria:** Counts are explicit; raw metrics/denominators/filters remain unchanged.
- **Risks and Regression Scope:** Insight group summaries/export consistency.
- **Git / PR Record:** Current hardening branch; candidate/PR/CI pending.
- **Final Outcome:** Automated and manual retesting passed; status `VERIFIED`.

#### FCR-040 — Support Triage explicit no-mock state

- **Basic Information:** Triage ticket/mock; status `IMPLEMENTED`.
- **Current Behavior:** Missing mocks say `Mock unavailable`; visible-mock assisted copy renders only when a mock exists; human forms stay blank.
- **Manual Observation:** `triage-mock-source` and `triage-visibility` failed because copy implied a nonexistent suggestion.
- **User Impact:** Removes mock provenance/availability ambiguity.
- **Core Assessment:** Pre-freeze blocker; transparency issue, no real-model change.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`.
- **Rationale:** Conditional rendering fixes the root cause; fabricating/inferencing a mock rejected.
- **Implementation Scope:** Triage template and Independent/Assisted no-mock regressions.
- **Acceptance Criteria:** Unavailable is explicit; unavailable stays outside visible/hidden counts; form remains unfilled.
- **Risks and Regression Scope:** Triage source, visibility, and summary.
- **Git / PR Record:** Current hardening branch; candidate/PR/CI pending.
- **Final Outcome:** Automated checks and both original QA manual retests passed; status `VERIFIED`.

#### FCR-041 — Linked Support Triage entry from Batch Results

- **Basic Information:** Batch-to-Triage workflow; status `IMPLEMENTED`.
- **Current Behavior:** Batch Results exposes `Prepare Support Triage` with its token; parsed records remain snapshot-eligible even after NLP provider failure.
- **Manual Observation:** `triage-workspace` and workspace privacy Phase B were blocked by the missing entry.
- **User Impact:** Restores normal access to an existing linked workflow.
- **Core Assessment:** Pre-freeze blocker and privacy-verification dependency.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `IMPLEMENTED`.
- **Rationale:** Backend token support already existed; new sources/connectors/persistence rejected.
- **Implementation Scope:** Batch link, linked-workspace route tests, provider-failed parsed-row regression.
- **Acceptance Criteria:** Main/edge batches enter from UI; failed-inference parsed rows remain eligible; context remains supporting only.
- **Risks and Regression Scope:** Batch/Triage token, expiry, privacy exports.
- **Git / PR Record:** Current hardening branch; candidate/PR/CI pending.
- **Final Outcome:** Automated entry/eligibility tests and V-04 delegated technical retest passed; status `VERIFIED`.

### FCR-042–FCR-044 — latest product findings

#### FCR-042 — Score-list ordering

- **Basic Information:** Cross-result score lists; 2026-08-13; status `OPEN`.
- **Current Behavior:** Scores follow existing contract/label order, without value sorting.
- **Manual Observation:** The reviewer suggested ordering for faster scanning.
- **User Impact:** Minor readability impact; values, labels, and auditability remain intact.
- **Core Assessment:** Usable current behavior; not a Freeze blocker; no privacy/security risk.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `OPEN`.
- **Rationale:** Independent readability finding, not mechanically added to the blocker patch.
- **Implementation Scope:** Later unified ordering, screen-reader, and provenance review; no current change.
- **Acceptance Criteria:** Any implementation states its ordering and preserves native/compact identity.
- **Risks and Regression Scope:** Result rendering, documentation/screenshots, accessibility.
- **Git / PR Record:** Not implemented; no commit/PR/CI.
- **Final Outcome:** Retained for Product Hardening; not required before Feature Freeze.

#### FCR-043 — Explanatory and error information hierarchy

- **Basic Information:** Cross-page information hierarchy; 2026-08-13; status `OPEN`.
- **Current Behavior:** Explanations, limitations, warnings, and errors are visible but sometimes share similar weight.
- **Manual Observation:** The reviewer requested stronger distinction between explanatory and error copy.
- **User Impact:** Minor scan/recovery efficiency impact; QA did not show unrecoverable error paths.
- **Core Assessment:** Non-blocking accessibility/UX hardening; no data risk.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `OPEN`.
- **Rationale:** Cross-page design-system work needs separate regression and does not belong in the narrow patch.
- **Implementation Scope:** Later color, hierarchy, ARIA, and contrast review; no current change.
- **Acceptance Criteria:** Warning/error/secondary copy is distinguishable and keyboard/contrast safe.
- **Risks and Regression Scope:** Global CSS, responsive behavior, accessibility.
- **Git / PR Record:** Not implemented; no commit/PR/CI.
- **Final Outcome:** Retained for Product Hardening; not required before Feature Freeze.

#### FCR-044 — Triage return and default navigation

- **Basic Information:** Triage ticket navigation; 2026-08-13; status `OPEN`.
- **Current Behavior:** Tickets can complete and return to the workspace, but default position/return efficiency can improve.
- **Manual Observation:** The reviewer requested a more direct return/default path.
- **User Impact:** Small navigation cost across repeated tickets; lifecycle completion is not blocked.
- **Core Assessment:** Non-blocking workflow ergonomics; no privacy/integrity risk.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `OPEN`.
- **Rationale:** Unlike FCR-041's missing entry, this is an independent post-ticket navigation improvement.
- **Implementation Scope:** Later return-target and focus/anchor review; no current change.
- **Acceptance Criteria:** Return position is predictable without changing draft/final/revision state.
- **Risks and Regression Scope:** Triage routes, browser history, focus behavior.
- **Git / PR Record:** Not implemented; no commit/PR/CI.
- **Final Outcome:** Retained for Product Hardening; not required before Feature Freeze.

**2026-08-13 Decision update:** PR #16 manual retest confirmed that Source &
Guide, Workspace, Ticket, and Summary all lacked a discoverable return to the
application home and caused material operating difficulty; deep Moderation
Session/Results views shared the structural gap. This overturns the initial
non-blocking impact assessment but does not create a new FCR ID because the root
cause remains nested-workflow global navigation. FCR-044 is now a pre-freeze
blocker with Status `IMPLEMENTED`: every non-root view uses an explicit,
keyboard-operable `← Social Text Intelligence home` link, and deep Triage and
Moderation views separate global navigation from workflow subnavigation.
At that point FCR-002 was reopened for verification. Targeted route regression
passed and manual return-navigation retest remained pending. The final
verification update below supersedes that intermediate status.

**Git / PR update:** FCR-044 implementation commit `67eaa33` in Draft PR #16;
final head and CI are authoritative in the PR checks.

**2026-08-13 Final verification update:** Final-head smoke testing passed on
tested behavioral SHA `16acb0f5931b022b57f0c5cdbe4501973aa3ad11`.
FCR-044 manual retest is PASS: all four internal Triage views and comparable
deep views expose a clear return to Social Text Intelligence home without
clearing temporary workspace state. FCR-044 is `VERIFIED`, FCR-002 navigation
verification is re-closed as `VERIFIED`, and V-01 is satisfied by that exact
SHA. Later governance-document commits do not move the behavioral candidate.

### FCR-045 — Ephemeral Batch state integrity

- **Basic Information:** Batch process-memory store; 2026-08-13; status `VERIFIED`.
- **Current Behavior:** At the Phase 0 baseline, reaching capacity silently deleted the earliest-expiring workspace. Long analysis read state, performed inference, ignored `replace()` failure, and could follow the success redirect without saving its result.
- **Manual Observation:** Product Hardening Phase 0 technical audit reproduced both failure modes with capacity and TTL/write-back probes plus route inspection.
- **User Impact:** Unexported Batch, Review, Insights, and linked source state could disappear without warning; completed local inference could be mistaken for a saved result.
- **Core Assessment:** Release-blocking data-integrity hardening; it does not reopen Feature Freeze or add a feature domain.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `VERIFIED`.
- **Rationale:** FCR-036 governs confirmation for user-initiated clear only. PH-001 and PH-002 share one missing Batch-store capacity/active-operation integrity contract, so they become one permanent finding rather than duplicating or rewriting FCR-036.
- **Implementation Scope:** Return 409 and block new uploads at capacity; protect synchronous active analysis with an exclusive lease that survives TTL purge and permits only the current lease to commit; return an explicit 409 on write-back conflict; retain process memory, TTL, and no database/background tasks.
- **Acceptance Criteria:** `capacity+1` preserves existing work; inactive expiry still clears state; active analysis can commit across TTL; clear/duplicate-analysis conflicts are blocked; write-back failure is never success; explicit clear releases capacity; existing Review, Insights, and linked workspaces survive a blocked upload.
- **Risks and Regression Scope:** Batch store lifecycle, upload/analyze/clear routes, Review/Insights reachability, and linked Moderation/Triage sources; models, thresholds, privacy exports, and other hardening findings remain unchanged.
- **Git / PR Record:** `hardening/product-hardening-cycle`; PR #18 merged to main SHA `1b36fe8c024823c1f4829621a7bcc733b2915c93`; initial A1 SHA `163af519e37eaff10c2b481dbbfc49a6e38ae39c` remote CI PASS; error-render correction/tested behavioral SHA `729318c6c253ea8eee8351e766bbcfe7a335c297` remote CI PASS.
- **Final Outcome:** Minimal state-integrity correction and the narrow error-render regression are verified; targeted Batch routes 6 passed, full suite 132 passed with 2 opt-in real-model tests skipped, Ruff, strict MyPy, compileall, and pip check passed, and PR #18 Python 3.11/3.12/3.13 CI is green; FCR-045 is closed as `VERIFIED`.

### FCR-046 — Complete-input inference truthfulness

- **Basic Information:** Cardiff sentiment, SamLowe emotion, combined analysis, Direct, Batch, and CLI; 2026-08-13; status `VERIFIED`.
- **Current Behavior:** At the Phase 0 baseline, both Transformers runtimes passed `truncation=True, max_length=512`; valid text with an over-budget encoded sequence could be silently shortened and still produce a result presented as covering the complete input.
- **Manual Observation:** Product Hardening Phase 0 code inspection found the shared truncation path. Real offline-model probes confirmed that SamLowe declares 512 while the pinned Cardiff tokenizer exposes an unknown-limit sentinel and its model configuration exposes 514 RoBERTa position slots.
- **User Impact:** Partial-text sentiment/emotion scores, Review, Insights, and exports could be mistaken for whole-text analysis, breaking result truthfulness and failed-row semantics.
- **Core Assessment:** Release-blocking correctness/data-integrity hardening; Feature Freeze remains closed and no long-form capability is added.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `VERIFIED`.
- **Rationale:** FCR-003, FCR-006, and FCR-008 cover recoverable input, model-limit communication, and Batch partial failure separately, but none defines the cross-provider, cross-entry complete-input success invariant. PH-003 therefore becomes permanent FCR-046 rather than duplicating a local finding.
- **Implementation Scope:** Use an audited 512-token encoded-input budget for both pinned providers; enable tokenizer special tokens, disable truncation, and validate real encoded length; preflight every required provider before combined inference; reject Direct/CLI explicitly; fail only the affected Batch row and leave its exported AI scores/provenance blank. Keep the 20,000-character application safety ceiling separate.
- **Acceptance Criteria:** Encoded length 512 succeeds and 513 returns explicit `model_input_too_long`; special tokens count; Cardiff, SamLowe, combined, Direct, mixed Batch, export, and CLI agree; existing within-budget labels/scores/provenance do not change; no chunking, aggregation, summarization, model, revision, threshold, persistence, or successful-result truncation field is added.
- **Risks and Regression Scope:** Tokenizer/model metadata compatibility, documented Cardiff preprocessing, two-provider preflight order, first model load, Batch row isolation/export, CLI error handling, and UI copy; PH-004 and all other hardening are excluded.
- **Git / PR Record:** `hardening/product-hardening-cycle`; behavioral candidate `31b5e6cf7fc6d551bb72680900976595008d9d7c`; PR #19 merged to main SHA `1c9764ba7bcd45b07a07a93077b86070e358a0ab`; behavioral review, closure-head CI, and post-merge CI PASS.
- **Final Outcome:** The A2 complete-input contract, targeted/full regression, real offline-model smoke, behavioral code review, and PR CI passed. FCR-046 is closed as `VERIFIED` on the exact behavioral SHA. Feature Freeze remains PASS and PH-004 is unstarted.

### FCR-047 — Global HTTP request-body boundary

- **Basic Information:** Local Flask Direct, Batch, Review, Insights, Moderation, and Triage HTTP POST boundary; 2026-08-13; status `VERIFIED`.
- **Current Behavior:** The Phase 0 baseline enforced the 20,000-character Direct limit, 2 MiB CSV payload limit, and workflow field limits only after parsing. It had no global request-body ceiling before abnormal form/multipart bodies entered framework parsing.
- **Manual Observation:** Product Hardening Phase 0 code inspection confirmed that app config had no `MAX_CONTENT_LENGTH` or equivalent framework boundary while routes and blueprints independently read `request.form` and `request.files`.
- **User Impact:** Even on loopback, an abnormal local request could create avoidable memory pressure before business validation. An echoing or cacheable error page would also violate the privacy contract.
- **Core Assessment:** Release-risk availability/privacy hardening; Feature Freeze remains closed and this is not a Web-security redesign.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `VERIFIED`.
- **Rationale:** FCR-025 governs privacy/local-state consistency and FCR-029 governs existing error/recovery states; neither defines the cross-entry capacity root cause before form/multipart parsing. PH-004 therefore becomes permanent FCR-047 rather than rewriting or duplicating a local finding.
- **Implementation Scope:** Default `MAX_CONTENT_LENGTH=3 MiB`, leaving 1 MiB (50 percent) multipart/form encoding capacity above the 2 MiB CSV payload limit; CLI configuration must remain greater than the CSV limit. A `before_request` gate rejects declared oversized bodies before route/state logic, Flask enforces the same ceiling while reading, and one fixed 413 handler inherits no-store/no-cache.
- **Acceptance Criteria:** Oversized Direct, Batch multipart, Review, Insights note, and Triage decision requests return 413; no source content, traceback, or internal path is echoed; no ephemeral state is created or changed; normal requests retain current semantics; the 2 MiB CSV byte limit remains independent; no CSP, Origin/Host policy, account, remote deployment, database, background task, or persistence work is added.
- **Risks and Regression Scope:** Flask request parsing, multipart overhead, all POST routes, 413 headers/copy, Batch/Review/Insights/Moderation/Triage stores, CLI configuration, and CSV-limit distinction; PH-005, PH-007, and other hardening are excluded.
- **Git / PR Record:** `hardening/product-hardening-cycle`; behavioral candidate `def0577feb3c43d4e9e81577003c43da821b6ba2`; PR #20 merged to main SHA `552be0012300ce0d40714b739bbb9e27248c8bca`; behavioral review, closure-head CI, and post-merge CI PASS.
- **Final Outcome:** The A3 HTTP request-body boundary, targeted/full regression, behavioral code review, and PR CI passed. FCR-047 is closed as `VERIFIED` on the exact behavioral SHA. Feature Freeze remains PASS; PH-005 was subsequently closed by FCR-048 evidence.

### FCR-048 — Real-model Batch capacity and performance evidence

- **Basic Information:** Local CPU Batch capacity with pinned Cardiff sentiment and SamLowe emotion; 2026-08-13; status `VERIFIED`.
- **Current Behavior:** The frozen product runs both real models sequentially in one synchronous process with a 500-row Batch ceiling. The A1 active-analysis lease protects long write-back, but no 1/50/500-row real-model timing, throughput, RSS, or TTL evidence previously existed.
- **Manual Observation:** On Windows 11, Python 3.12.13, an Intel i7-12700H, about 16 GB RAM, and PyTorch 2.13 CPU-only, the probe forced offline local-cache use. Initialization through first result took 3.626 seconds; warm 1/50/500 rows took 0.075/3.763/39.636 seconds, with 500/500 successes and zero failures. Peak RSS was about 0.99 GiB, with about 2.97 MiB growth from the first loaded result through 500 rows.
- **User Impact:** Without evidence, the 500-row promise, synchronous wait, and memory requirement cannot be judged for RC. The measurement shows that the defined short social-text workload is deliverable on the reference desktop while avoiding a false all-hardware/all-input SLA.
- **Core Assessment:** Measurement/evidence hardening; no frozen product behavior change and no assumed or implemented optimization.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `VERIFIED`.
- **Rationale:** FCR-045 defines capacity blocking and active-operation state integrity, while FCR-046 defines complete-input truthfulness. Neither supplies real-model capacity, throughput, or RSS release evidence. PH-005 therefore becomes permanent FCR-048 rather than duplicating an existing finding.
- **Implementation Scope:** Add an opt-in offline benchmark harness excluded from ordinary CI plus auditable evidence. Exercise production `AnalysisService`, `analyze_batch`, and `EphemeralBatchStore` lease/write-back with synthetic English fixtures. Do not modify `src/`, models, revisions, thresholds, Batch limits, or runtime architecture.
- **Acceptance Criteria:** Separate cold initialization/first inference from warm 1/50/500; record environment, throughput, success/failure, and process RSS; retain and commit an active lease beyond a 1-second probe TTL; propose a headroom-bearing RC budget scoped to the fixture/profile; keep the heavy probe outside ordinary CI.
- **Risks and Regression Scope:** Hardware and input length affect results, so this is not a universal SLA. The measurement harness, offline cache, two pinned revisions, sequential Batch, and A1 lease are in scope. PH-006, PH-007, FCR-042/043, async, parallelism, quantization, GPU, and persistence are excluded.
- **Git / PR Record:** `hardening/product-hardening-cycle`; Product Hardening Batch A4 PR #21 merged to main SHA `5778f8f8804c3014f16940af1d7254c202dbcf41`; local real-model probe, full quality suite, review, and CI passed.
- **Final Outcome:** [Real-model capacity evidence](REAL_MODEL_CAPACITY_EVIDENCE.md) supports retaining `MAX_BATCH_ROWS=500`: 500 rows took about 39.636 seconds at 12.61 rows/s with about 0.99 GiB peak RSS, and every result survived the probe TTL and committed. PH-005 closes as `VERIFIED` without corrective product work. Feature Freeze remains PASS; PH-006 is subsequently carried by FCR-049.

### FCR-049 — Concurrent workspace mutation integrity

- **Basic Information:** Concurrent writes to Batch, Moderation, and Triage process-memory workspaces; 2026-08-13; status `VERIFIED`.
- **Current Behavior:** Before A5, multiple POST routes read a workspace, derived a complete replacement outside the lock, and then replaced it. Two requests starting from one old snapshot could let the later writer silently erase the earlier accepted mutation.
- **Manual Observation:** The Phase 0 code audit found the same read/derive/replace root cause in Batch column selection, Review/Insights, Moderation, and Triage. Deterministic nested interleaving tests reproduce the stale-snapshot risk and verify final stored state after the fix.
- **User Impact:** Multiple tabs, repeated submits, or concurrent requests could lose a review, note, training decision, or triage decision while appearing successful, which is a release-blocking data-integrity risk.
- **Core Assessment:** Current hardening for correctness and data integrity. Feature Freeze stays closed, with no database, background work, or distributed concurrency architecture.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `VERIFIED`.
- **Rationale:** FCR-045 covers Batch capacity, TTL, and the active-analysis lease/write-back contract. It does not cover ordinary workspace mutation lost updates across Batch, Moderation, and Triage. PH-006 therefore becomes permanent FCR-049 rather than rewriting or duplicating FCR-045.
- **Implementation Scope:** The three stores reuse one atomic mutation primitive that reads current workspace state, executes a pure mutation callback, and saves atomically under the store lock. It protects Batch selection, Review, persisted Insight selection/notes, every Moderation state action, and every Triage state action. GET navigation, filters, summaries, exports, and request-local presentation state stay outside because they do not replace persisted workspace state.
- **Acceptance Criteria:** Preserve independent mutations; revalidate one-shot rules against current state at submit time; return 409 for races that cannot be merged safely; preserve newer state after conflicts; retain 404 for expired/cleared workspaces; do not bypass the A1 active lease; preserve explicit revision and normal single-tab workflows.
- **Risks and Regression Scope:** Callbacks under the store lock remain short and in-memory; deterministic tests assert final stored state. Process-memory, bounded capacity, TTL, loopback, and no-persistence boundaries remain. PH-007, WebSocket, distributed locks, external cache, async, and FCR-042/043 are excluded.
- **Git / PR Record:** `hardening/product-hardening-cycle`; Product Hardening Batch A5 PR #22; behavioral candidate `a3ec11b674c11148d66be73475b43d0796329a54`; current-state mutation/concurrency integrity review PASS; behavioral-head Python 3.11/3.12/3.13 CI PASS; merged to main SHA `3a0bb9c9460379b55a6488f966034419e40cf91d`.
- **Final Outcome:** Atomic current-state mutation and explicit 409 conflicts passed behavioral review and CI, closing FCR-049 as `VERIFIED` on the fixed behavioral SHA. This closure changes governance documentation only. FCR-048 remains `VERIFIED`, Feature Freeze remains PASS; PH-007 is subsequently carried by FCR-050.

### FCR-050 — Local browser security boundary

- **Basic Information:** Loopback Flask Host, unsafe-method same-origin, and global response headers; 2026-08-14; status `VERIFIED`.
- **Current Behavior:** Before A6, the CLI bound only to `127.0.0.1`, but Flask had no trusted-host configuration, unsafe browser POSTs had no Origin/Referer boundary, and responses lacked unified CSP, nosniff, referrer, and anti-framing headers beyond no-store/no-cache.
- **Manual Observation:** The Phase 0 audit confirmed that CSS and JavaScript are already self-hosted. The only strict-CSP conflict was a dynamic inline width style in Insights. Direct inference and every temporary-workspace mutation are reachable through ordinary browser POSTs.
- **User Impact:** Even with loopback binding, a malicious page can try to send requests to a local port. Without Host and explicit cross-origin unsafe-request validation, such a request could trigger inference or change temporary state. Missing browser headers also increases framing, MIME-sniffing, and resource-injection exposure.
- **Core Assessment:** Release-risk browser-boundary hardening. Feature Freeze remains closed, and this is not authentication, sessions, TLS, remote deployment, or production-server security.
- **Decision:** Class `HARDENING`; Decision `Keep and harden`; Status `VERIFIED`.
- **Rationale:** FCR-047 covers only HTTP request-body capacity, and FCR-049 covers concurrent mutation integrity after business dispatch. Neither defines the Host, browser same-origin, or response security-header root cause. PH-007 therefore becomes permanent FCR-050.
- **Implementation Scope:** Flask `TRUSTED_HOSTS` accepts only `127.0.0.1` and `localhost`. `POST`, `PUT`, `PATCH`, and `DELETE` require an exact same-origin Origin; when Origin is absent, an existing Referer must be same-origin; when both are absent, compatibility is limited to a local non-browser request behind trusted Host. Add global self-only CSP, `nosniff`, `Referrer-Policy: same-origin`, CSP `frame-ancestors 'none'`, and `X-Frame-Options: DENY`. Replace the sole inline style with a native progress element controlled by local CSS.
- **Acceptance Criteria:** Approved local Hosts and same-origin workflows operate normally; untrusted Host returns fixed 400; explicit cross-origin, `null`, or malformed Origin and mismatched Referer return fixed 403; rejection occurs before inference, body parsing, or mutation and echoes no user data/path; HTML, redirect, error/413, CSV, CSS, and JavaScript carry unified headers; CSP has no wildcard, external source, or `unsafe-inline`; A3/A5 contracts remain intact.
- **Risks and Regression Scope:** Missing-Origin compatibility is only for local non-browser clients behind trusted Host; it is not remote access or authentication. The completed real-browser smoke confirms no CSP violation or blocked local resource in the console. HSTS, CORS, TLS, LAN, reverse proxy, production WSGI, account/session, a CSRF framework, reporting service, later PH work, and FCR-042/043 are excluded.
- **Git / PR Record:** `hardening/product-hardening-cycle`; Product Hardening Batch A6 PR #23; behavioral candidate `1a2d25fafc532215b45cf8d6310e8e1b2b16140d`; Host/same-origin/CSP/security-header code review PASS; behavioral-head Python 3.11/3.12/3.13 CI PASS; real-browser smoke PASS; PR #23 merged to main SHA `cfcd13ef582996b8c75aa20524dcc212e2ab8922`.
- **Final Outcome:** Trusted Host, the same-origin unsafe-method gate, strict global headers, and the CSP-compatible template passed review, CI, and real-browser smoke. Direct, Batch/Review, Insights progress/notes, Moderation/Triage, and CSV operated normally, with no CSP violation or blocked local resource in DevTools Console. FCR-050 closes as `VERIFIED` on the fixed behavioral SHA, and PR #23 is merged. FCR-049 remains `VERIFIED`, Feature Freeze remains PASS; later PH-008 is carried by existing FCR-030.

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

### 2026-08-13 formal Feature Freeze decision

```text
Feature Freeze decision: Social Text Intelligence 0.10.0
Decision date: 2026-08-13
Tested behavioral SHA: 16acb0f5931b022b57f0c5cdbe4501973aa3ad11
Decision: PASS
Governance closure SHA: 2a701f87b167d5a112184b1ffedb4f8f7a12d95e
Open current-version blockers: None
Approved exceptions: FCR-042 and FCR-043 are non-blocking Product Hardening backlog
Deferred next-version items: French/multilingual, long-form/transcripts, connectors, persistence, accounts/shared/cloud, and other approved future expansions
Required regression: Final-head smoke PASS; 127 tests passed and 2 opt-in real-model tests skipped; Ruff, strict MyPy, compileall, pip check, documentation/privacy checks, and GitHub CI passed
Approver: User / project owner
Evidence: PR #16 candidate-specific manual evidence; exact behavioral SHA above; FCR-044/FCR-002 final verification; Python 3.11/3.12/3.13 CI
```

This PASS freezes only the tested behavioral SHA above. Later closure commits
record governance/status only and are not a new behavioral candidate. FCR-042
and FCR-043 remain Product Hardening backlog and do not block this gate. Release
readiness remains No.

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
