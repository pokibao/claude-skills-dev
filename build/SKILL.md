---
name: build
description: "Use when the user explicitly asks to run /build, Build 2, or a gated role-based delivery pipeline with Memory Anchor recall instead of direct implementation."
version: "4.0.0"
triggers:
  - "/build"
  - "Build 2"
  - "用 build"
  - "按 build"
  - "走 build"
---

# Build 2

## What This Is

Build 2 不是“把任务交给一堆 agent 祈祷成功”，而是三层能力的合体：

- **Harness Engineer**：负责门控、证据、降级链、context compression，让流水线不失控。
- **Hermes Engineer**：负责 single source of truth、progressive disclosure、技能化编排，不让 command / skill / agent 三套文案互相打架。
- **Memory Anchor**：负责历史召回、断点续跑、结果回写，让 `/build` 不是每次都从零开始。

再往前一步，Build 2.3 要做到的是：

- 默认 **静默启动**：先查记忆、先续跑、先看风险，不把内部动作都端到用户面前
- 默认 **静默复盘**：完成后自动提炼经验，不要求用户每次都听一遍流水账
- 默认 **静默回灌**：可复用的方法先变成候选规则，再在足够证据后晋升

Build 2 的目标不是更重，而是 **更稳**：
- 小任务不被大流程拖垮
- 大任务不在模糊需求里直接开写
- 任何拓扑都不会因为“缺 Requirement Card / 缺 Architecture Doc”而自我矛盾
- 任何完成声明都必须有证据
- 方法论会随着任务逐步沉淀，并回灌到后续执行

## When To Use

只在下面场景使用 Build 2：

- 用户明确说 `/build`
- 用户明确说“用 build”“按 build 流水线”“走 Build 2”
- 任务需要显式门控、角色分工、记忆闭环

**不要**因为泛泛的“帮我做个功能”“改个页面”就自动套 Build 2。那类请求默认还是直接做，除非用户明确要这套流水线。

## Non-Goals

- 不追求所有任务都走全 Agent Team
- 不追求把需求放大成 PRD
- 不把 Memory Anchor 当日志垃圾桶
- 不为了“像流程”而牺牲速度

---

## Core Rules

> **元原则（曾国藩战法 · 贯穿所有 Rules）**：
> - **结硬寨**：一个主题一个分支一个 commit，不做综合 commit（每 ~100 LOC 的 PR > 一个 +1000 LOC 的 PR）
> - **打呆仗**：每步 local CI 全绿才开下一寨（`fmt + clippy -D warnings + test` 不绿不 push）
> - **先侦察，后动手**：动手前 Read 目标参考源码做 scope 验证，不依赖 coordinator 记忆术语（自造术语 = agent 伪工作）
> - **审 diff 不盲信**：Agent/Codex 产出的每个 hunk 必须 Read 读懂再 Edit，禁止整块盲 apply
> - **敢撤兵**：发现 scope 错/大假设被 probe 推翻，立刻弃坑重规划（沉没成本不是继续理由）
>
> 来源：Gate F Sprint 2026-04-19，7 PR/+862 LOC/4 次主动纠错

### Rule 1: Single Source Of Truth

- `/build` command 只做入口，不再复制整套逻辑
- `~/.claude/skills/build/SKILL.md` 是唯一真相来源
- agents 只定义各自角色，不再各写一套拓扑规则

### Rule 2: One Unified Contract For All Topologies

任何拓扑进入 Dev 前，都必须有一个统一的 **Execution Brief**。

FULL 拓扑可以额外有：
- Requirement Card
- Architecture Packet

但 **Dev / QA / Ship 的最低依赖永远是 Execution Brief**，不是强绑 Requirement Card / Architecture Doc。

这条规则用来彻底修复：
- LIGHT / STANDARD 理论上能跑
- Dev / Ship 却因为“没有架构文档”自锁死

### Rule 3: Evidence Before Transition

阶段切换前必须有证据：

- Clarify → 明确确认
- **Scope 验证 → Read 目标参考源码（Python / 规范 / Agent 情报）再 brief 下游**；禁止只凭 coordinator 记忆术语（自造术语 = 伪工作；Gate F Sprint Task #1 "Raw 层" / #2 "decision tree" 都是此坑）
- Dev → 测试/运行/截图/curl；每个 commit message 引用目标源码位置（`backend/xxx.py:LINE`）
- QA → 实测证据
- Ship → 最终 smoke test + 用户确认

### Rule 4: Memory Is Operational, Not Decorative

Memory Anchor 在 Build 2 里不是“任务做完顺手记一下”，而是四个固定用途：

1. 开始前：`get_context` + `search_checkpoints` + `search_rules`
2. 中途中断：`save_checkpoint`
3. 完成后：`add_rule` 写 `BUILD-SUCCESS / BUILD-FAILURE`
4. 历史被证伪：`report_outcome`

### Rule 5: Harness Protects The Floor, Not The Ceiling

Harness 的作用是：
- 防止乱写
- 防止乱扩 scope
- 防止没证据就说完成

不是把所有任务都升级成重流程。

### Rule 6: Quiet By Default

Build 2 的记忆召回、checkpoint、复盘、经验抽象，**默认静默执行**。

只有以下情况才显式告诉用户：

- 命中 active checkpoint，需要确认是否续跑
- 历史失败会导致本次拓扑升一级
- 历史成功会导致本次可以安全降级
- 出现新的高价值方法结论，值得直接同步给用户

### Rule 7: Learn Method, Not Just Task

每次 `/build` 结束后，至少要回答两个问题：

1. 这次任务本身有没有完成？
2. 这次有没有学到一条可以复用的方法？

前者进入 `BUILD-SUCCESS / BUILD-FAILURE`。
后者先进入 `BUILD-RULE-CANDIDATE`，证据足够后再晋升为持久规则。

### Rule 8: Gate Integrity — 球门不准移 / Scope 错了立刻撤

Sprint Contract / benchmark / QA gate 设了就是铁门：

- **Gate FAIL = STOP + escalate**，禁止发明 alternative gate 绕过
- Benchmark 设计阶段必须先验算 N（样本量能不能让 gate 物理上达成），不够就提高 N 或换 metric
- Synthetic benchmark 只能证 mechanism correctness（单元测试也能做），不要假装它证了 real-world value
- 跑完发现过不了 → 诚实汇报，不是"优先让流水线继续"

**Scope 撤兵纪律（曾国藩战法蒸馏）**：

- **发现 scope 本身错了**（伪任务 / 方向错）→ 立刻 `git checkout -- .` 重建分支，不硬推
- **大假设被 probe 推翻**（如 "模型差异" 被证明是 "L2 normalize 差异"）→ 立刻废弃原大工程，改最小修法
- **沉没成本不是继续的理由**：Codex 已经写的 910 行代码 + probe 已经跑的 1 小时都不值得绑架接下来的决策

> 来源：BR-移动球门 CORRECTION (2026-04-09) + Gate F Sprint 2026-04-19（C5 L2 norm 发现省了 1-2 周 Ollama HTTP 重写）

### Rule 9: Lesson Must Have Delivery Path

MA 里的 `[CORRECTION]` / `[FAILURE]` 教训必须同时设计投递路径，否则只是"写给 MA 看的日记"：

- SessionStart hook 硬注入（高优，每次都看到）
- UserPromptSubmit hook 情境触发（中优，匹配时出现）
- Skill search_rules hint（低优，build 启动时查）

写教训 → 立刻确认注入点 → 没有注入点就不算完成。

> 来源：BR-004 (2026-04-08)，教训写了但下个 session 完全没看到

### Rule 10: Experiment Isolation

实验/优化/AutoResearch 代码不得直接改写共享生产配置：

- 候选配置必须走临时快照或返回值传递
- 只有显式 promote 才能覆盖主配置
- 否则实验态和生产态隐式串扰

> 来源：BRC-006 (2026-04-09)，fstack autoresearch 改了生产配置

### Rule 11: Classify Before Route — 不要通杀一套流程

进入 Dev 前，用 **廉价模型（Haiku/Sonnet）** 做一次结构化分类：

```text
classify(task) → { type: bug|feature|refactor|config|docs, risk: low|medium|high }
```

分类结果决定执行路径：
- `bug` → 跳过 PM，直接 investigate → fix → validate
- `feature` → 走正常 Brief → Dev → QA 流程
- `refactor` → 强制只读分析阶段 + PostToolUse 验证 hook
- `config/docs` → MICRO 拓扑，跳过 QA

**不要**对所有任务都跑同一条 pipeline。分类只需 ~100 token（Haiku），比跑错整条流程便宜 1000 倍。

> 来源：Archon archon-fix-github-issue 的 classify 节点 + output_format JSON Schema 条件路由 (2026-04-13 源码分析)

### Rule 12: Read-Only Guards — 规划阶段禁止写代码

PM 和 Architect 阶段的 agent **必须**被限制为只读：

- PM：只能 Read / Grep / Glob / WebSearch / AskUserQuestion
- Architect：只能 Read / Grep / Glob / WebSearch / Bash(只允许 git/ls/wc 等读命令)

实现方式（按优先级）：
1. **Agent spawn 时设 `mode: "plan"`**（Claude Code 原生支持）
2. 如果 mode 不可用，在 agent prompt 顶部硬注入：`HARD CONSTRAINT: You MUST NOT use Write, Edit, or Bash(except read-only commands). Violation = immediate task failure.`
3. 如果 hooks 可用，配置 `PreToolUse` hook 拦截 Write/Edit 调用

**为什么不靠 prompt 劝阻**：AI 在"分析"阶段经常忍不住直接开改——这不是能力问题，是 prompt 约束弱于工具约束。Archon 用 `denied_tools: [Write, Edit, Bash]` 在 YAML 层面硬拦，效果远好于 prompt 里写"请不要改代码"。

> 来源：Archon archon-refactor-safely 的 denied_tools + permissionDecision:deny 机制 (2026-04-13 源码分析)

### Rule 13: PostToolUse Verification — 改了就验 / Read-before-Edit 节点同步

Dev 阶段**每次 Write/Edit 后**，必须立刻验证：

**Edit 前先 Read（曾国藩战法蒸馏）**：

- Edit 工具报 "File has been modified since read" = 节点状态过期（用户 / linter / agent 改过文件）。必须重新 Read 再 Edit
- 禁止 `git checkout stash@{0} -- <file>` 整块盲 apply Agent/Codex 产出——每个 hunk 必须 Read 读懂再决定 keep / edit / reject
- 禁止基于陈旧 Read 记忆做 Edit —— 同一 session 内改过的文件，再改前重新 Read
- **剔除 Agent 作用域蔓延**：Agent 自作主张删字段（如 Codex 删 `NoteInsert.version/root_id`）/ route 到伪方向模块（如 Codex 的 `memory_policy.rs` 错方向）—— 识别后立刻剔除，不因为"Agent 已经写了"保留

验证动作（按项目类型）：
- Python 项目：`uv run pytest -x --timeout=30`（快速 smoke）
- TypeScript 项目：`bun run type-check`（类型检查）
- 无测试框架：`python -c "import module"` 或 `node -e "require('./module')"`（至少验证不报错）

实现方式：
1. **首选：hooks 配置**（settings.json 的 `PostToolUse` hook，matcher: `Write|Edit`）
2. 次选：Dev agent prompt 硬注入 `After EVERY Write or Edit, immediately run the project's test/type-check command. Do NOT proceed to the next file until verification passes.`

**不要**等写完所有文件再一次性跑测试——错误会累积，到最后无法定位是哪次改动引入的。

> 来源：Archon archon-refactor-safely 的 PostToolUse hook + systemMessage 注入 (2026-04-13 源码分析)

### Rule 14: Concurrent Sessions & Review Routing — 多 session / Codex / Gate 协同

2026-04-19 Phase 1b Kickoff 单日三线并行（主会话 + peer Rust 会话 + Codex review bot）蒸馏 4 条纪律：

**14a. Worktree isolation for concurrent sessions**

- 感知到 peer session 并发（他在主工作区切分支）→ 立刻 `git worktree add /tmp/ma-<task> -b <my-branch> origin/<base>` 隔离
- 在 worktree 做 edit + commit + push，绝不在共享主 working tree 做会被 commit 的改动
- Peer 推到我的 PR 分支且非我 scope → 不 rebase 掉（惹 peer + 丢他工作），在 PR body 承认 scope 扩展让 reviewer 决定 squash / cherry-pick
- Cross-branch push（`git push origin mine:peer-target`）需要 owner 显式授权，不 self-authorize

**14b. Narrow-scope fix must protect happy path**

- 每次 narrow 修要两条测试：failing case pass + happy case 不回归
- 修 env / config / flag 变量时先列所有 legitimate consumer，决定修 source / transport / consumer 哪层
- 污染类问题优先从源头（如 conftest.py setdefault）修，不在传输层一刀切
- Codex 对同一 PR **再次** P1 = 第一次修的 scope 判断错了，回查根因而不是二次 patch

**14c. Review bot routing**

- 同一 PR 新 P1 finding → 立刻 review 自己的 scope 选择，可能要缩范围或换位置
- Merged PR 上的 post-merge finding → 开 GitHub Issue 追踪，不 re-open merged PR
- 多 finding 在同一 function → 一个 PR 合修；scope 隔离的开独立 PR
- Finding 在 peer scope → PR 下 comment 转告 evidence + patch suggestion，不越界改代码

**14d. Project-specific gate discovery**

- 不要假设所有项目都用 GitHub Actions 作 push gate
- memory-anchor 特例：Actions CI 已删（main @ `164919e`），**local CI 是唯一 gate**；Actions 红 ≠ blocker
- 进入新项目时 read 该项目 CLAUDE.md 的 "Push gate" 段（或等价 SOP），不照搬其他项目经验

> 来源：phase1b-kickoff-2026-04-19 单日高产蒸馏。MA id：`ab53c633`（过度修复）+ `af870837`（worktree 并发）+ `85ec8271`（Actions 非 blocker）+ `32f308eb`（单日方法论总纲）+ `project_phase1b_kickoff_lessons.md` 完整索引。

---

## Step -1: Silent Memory Bootstrap

**在任何评分前，先尝试加载 Memory Anchor。**

### 1a. Load Tools

```text
ToolSearch("memory-anchor")
```

如果 ToolSearch 失败：
- 标注 `memory_mode = off`
- 继续执行，但把评分置信度降一级

### 1b. Pull Context

```text
get_context()
search_checkpoints(query="{功能关键词或 task_slug}")
search_rules(query="{功能关键词} BUILD-SUCCESS BUILD-FAILURE")
```

优先看四类信息：

- 是否有 **active checkpoint**
- 是否有相似的 `BUILD-FAILURE`
- 是否有相似的 `BUILD-SUCCESS`
- 当前项目最近的关键事实 / 活跃任务 / 失败记忆

### 1c. Resume Logic

如果命中相关 checkpoint：

- `blocked / in_progress`：优先按“续跑”处理
- `completed`：当作历史参考，不续跑
- `stale`：先告诉用户“这个断点可能过期”，不要盲续

### 1d. Internal Understanding First

先在内部形成一条 `memory_bootstrap_note`：

```text
任务理解：[具体到页面/模块/脚本/接口级别的描述]
历史命中：[无 / active checkpoint / 相似成功 / 相似失败]
建议路由：[新开 / continuation / 升一级 / 降一级]
```

**默认不要把这整段都说给用户。**

只有三种情况才显式复述并确认：

- 命中 active checkpoint
- 记忆会改变本次拓扑或风险判断
- 你对用户真实意图仍不够确定

如果请求足够清晰且记忆没有改变路由，直接进入评分，并把记忆结论写进 `Execution Brief`。

---

## Step 0: Harness Triage

先给原始分，再用记忆修正。

### 0a. Classify → Route (Rule 11)

如果任务描述足够清晰（不是模糊的"帮我做个XX"），先用廉价模型做分类：

```text
任务类型: bug / feature / refactor / config / docs
风险级别: low / medium / high
```

分类结果影响路由（见 Rule 11）。分类不是强制的——模糊任务仍走 0b 人工评分。

### 0b. Raw Score

```
┌─ 评估 5 个维度（每项 0-2 分，总分 0-10）─────────────────┐
│ 1. 涉及几个文件？     0=1-2个  1=3-10个  2=>10个          │
│ 2. 有新 API/数据模型？ 0=无    1=改现有   2=新建           │
│ 3. 涉及外部依赖？     0=无    1=已用过的  2=新引入          │
│ 4. 用户需求清晰度？    0=一句话够 1=需确认1-2点 2=模糊      │
│ 5. 失败影响？         0=本地/可逆 1=影响用户 2=影响数据/钱   │
└───────────────────────────────────────────────────────────┘
```

### 0b. Memory Adjustment

记忆命中后，允许如下修正：

- 命中相似 `BUILD-FAILURE`，且失败点与当前任务直接相关 → **风险 +1 或拓扑升一级**
- 命中相似 `BUILD-SUCCESS`，且记录写明“应该更轻” → **允许降一级**
- 命中 active checkpoint → **标记 continuation，不重新发明流程**
- Memory Anchor 不可用 / checkpoint 明显过期 / 自己拿不准 → **评分置信度 = low，保守升一级**

### 0c. Routing

| 拓扑 | 分数 | 阶段 | 适用 |
|------|------|------|------|
| `MICRO` | 0-2 | Team Lead Brief → Dev → Ship | 改文案、改样式、改单配置、小脚本 |
| `LIGHT` | 3-5 | Team Lead Brief → Dev → QA → Ship | Bug fix、小功能、单文件逻辑 |
| `STANDARD` | 6-7 | Clarify(1-2问) → Brief → Dev → QA → Ship | 中等任务、需求还差1-2个关键答案 |
| `FULL` | 8-10 | PM → Architect → Brief → Dev → QA → Ship | 新系统、新 API、多模块 |
| `DESIGN` | 用户指定 | PM → Architect | 只规划，不写代码 |

### 0d. Mandatory Output

内部必须记录完整评分：

```text
🎯 复杂度评分: [X]/10 → 拓扑: [MICRO/LIGHT/STANDARD/FULL/DESIGN]
  文件范围: [0-2]  API/数据: [0-2]  外部依赖: [0-2]  需求清晰度: [0-2]  失败影响: [0-2]
  评分置信度: [high/medium/low]
  记忆修正: [无 / 升一级 / 降一级 / continuation]
  理由: [一句话]
```

用户默认只看一条压缩说明：

```text
我会按 [拓扑] 处理这次任务，因为 [一句话理由]。
```

只有以下情况再展开完整评分细节：

- 用户主动追问
- 拓扑不直观，可能引发误解
- 用户要覆盖拓扑

用户可以覆盖拓扑，但 Team Lead 必须说清风险。

---

## Step 1: Create The Execution Brief

**Execution Brief 是 Build 2 的统一交接契约。所有拓扑都必须有。**

### Build Brief Template

```markdown
# Execution Brief

- task_slug: build2-{feature-slug}
- topology: MICRO / LIGHT / STANDARD / FULL / DESIGN
- memory_mode: on / off
- learning_mode: silent
- request_summary: 用户要做什么
- continuation_context: 这是续跑还是新任务
- scope_in:
  - 明确要做的点
- scope_out:
  - 明确不做的点
- constraints:
  - 技术栈 / 现有代码 / 依赖限制 / 风险点
- memory_findings:
  - 命中的 BUILD-SUCCESS / BUILD-FAILURE / checkpoint / 项目事实
- artifacts_required:
  - 是否需要 Requirement Card
  - 是否需要 Architecture Packet
- verification_plan:
  - 这次如何证明完成
- sprint_contract_target:
  - MICRO=0 / LIGHT=3 / STANDARD=5 / FULL=10
```

### By Topology

- `MICRO`：Team Lead 直接写 Brief
- `LIGHT`：Team Lead 直接写 Brief
- `STANDARD`：Team Lead 先问 1-2 个关键问题，再写 Brief
- `FULL`：PM 出 Requirement Card，Architect 出 Architecture Packet，Team Lead 再压缩成 Brief
- `DESIGN`：PM + Architect，不进入 Dev

---

## Step 2: Clarify Only As Much As Needed

### MICRO / LIGHT

不额外追问。Step -1 的复述确认足够。

### STANDARD

Team Lead 自己问 1-2 个关键问题，不 spawn PM：

- 完成后长什么样？
- 现在最痛的点是什么？

每个问题都必须带建议：

```text
我理解你需要 [X]。
我建议先按 [Y] 做，因为 [Z]。
你确认，还是要改成别的？
```

### FULL

Spawn PM agent。PM 只问最多 3 个问题，逐个 AskUserQuestion，不许一次甩文字墙。

如果 AskUserQuestion 不可用：
- 退化为 Team Lead 逐个短问

---

## Step 3: Optional Team Scaffolding

如果 `TeamCreate / TaskCreate` 可用，就建 team；不可用就直接串行跑 phases。

**重要**：稳定性来自 artifacts，不来自 team UI。本步骤不是硬依赖。

---

## Step 4: Architect Only When Architecture Is Actually Needed

Architect 只在两种情况出现：

- `FULL`
- `DESIGN`

Architect 输出的是 **Architecture Packet**，不是长篇推理。

必须包含：

- 架构摘要
- Mermaid 图
- 模块边界
- API / 数据模型（如果有）
- 文件结构
- Naming conventions
- 风险与 trade-off

如果 Codex CLI 不可用或超时：

- 先降级到 Architect 自己出 `Architecture Packet Lite`
- 再不行，Team Lead 自己出简化版并显式告诉用户

---

## Step 5: Dev Phase

Dev 永远吃 **Execution Brief**。

**PR 粒度 — 最小可推独立 PR（曾国藩战法蒸馏）**：

- 一个主题 → 一个分支 → 一个 commit → 一个 PR（每 ~100 LOC 级别，不做 +1000 LOC 综合 commit）
- 发现当前分支工作超出单主题 → `git stash` 剩余部分，下个分支接力
- PR 之间有依赖（B 依赖 A 尚未 merge）→ `git checkout -b B origin/A`，PR body 标 "depends on #A"
- 每个 PR 的 commit message 必须引用目标源码位置（`backend/xxx.py:LINE`），方便 reviewer cross-verify
- 全 CI 绿才 push：`cargo fmt && cargo clippy --all-targets -- -D warnings && cargo test --workspace && ./scripts/local-ci.sh --fast`。禁止 "先 push 让 CI catch"

附加材料按拓扑决定：

- `FULL`：Execution Brief + Requirement Card + Architecture Packet
- `STANDARD`：Execution Brief
- `LIGHT`：Execution Brief
- `MICRO`：Execution Brief

### Sprint Contract Scaling

| 拓扑 | Sprint Contract |
|------|-----------------|
| `MICRO` | 不强制 |
| `LIGHT` | 3 条 |
| `STANDARD` | 5 条 |
| `FULL` | 10 条 |

规则：

- 每条必须直接对应用户需求
- 不许为了凑数发明无关标准
- Dev 报告里必须带 `changed_files / tests_run / manual_checks / known_limits / sprint_contract / evidence`

**时序规则（Sprint Contract = 承诺，不是总结）**：
- Dev 必须在第一行代码之前输出 `Draft Sprint Contract`，从 Brief 的 `scope_in` 和 `verification_plan` 提炼
- 实现完成后输出 `Final Sprint Contract`，标注 Draft vs Final 的差异及原因
- QA 会检查时序合规性。Draft 缺失 = 自评失效风险，QA 有权退回

### Dev Hard Gates

- **测试路径隔离**：测试若需操作用户真实文件（`~/.claude/*.txt` 等），必须用 env 变量或 module 级常量注入测试路径，禁止"备份+恢复"真实文件（测试中断 = 污染生产）
- **降级路径必测**：至少 3 条 negative path（MA 不可用 / subprocess timeout / JSON 解析失败），不能只测 happy path
- **实验隔离**：实验/调参代码不得直接改写生产配置，候选配置走临时快照或返回值传递

### PostToolUse Verification (Rule 13)

每次 Write/Edit 后立刻跑验证。不等写完所有文件再一次性测试。见 Rule 13 实现方式。

### Verification Floor

- `MICRO`：纯文案 / 样式 / 配置改动可免测试，但必须有运行 / 截图 / curl 之类的证据
- 其余拓扑：先测试再写码；如果测试框架不存在，用最小验证脚本或手动 smoke evidence 替代

---

## Step 6: QA Phase

`MICRO` 默认不跑 QA agent。`LIGHT / STANDARD / FULL` 都跑 QA，但深度不同。

### QA Inputs

永远需要：

- Execution Brief
- Dev Report

按需需要：

- Requirement Card（仅 FULL）
- Architecture Packet（仅 FULL，或 Brief 标明 architecture_required=yes）

### QA Depth By Topology

| 拓扑 | QA 目标 |
|------|---------|
| `LIGHT` | 验 3 条 Sprint Contract + 核心 smoke + 1 次回归 spot check |
| `STANDARD` | 验 5 条 Contract + 回归 + quick security scan |
| `FULL` | 全量 Contract + requirement coverage + API/data contract + security + drift |

### QA Stability Rules

- 不允许因为“没有 Architecture Doc”去卡 `LIGHT / STANDARD`
- 如果 Dev 缺少该拓扑要求的 Sprint Contract，先退回补齐
- 如果 QA agent 不可用，Team Lead 按对应深度手动执行 QA checklist，并在报告中标注 `manual_qa`

---

## Step 7: Ship Phase

Ship 也是 topology-aware。

### Pre-Ship Checklist

- `MICRO`
  - Execution Brief 存在
  - Dev evidence 存在
  - 最终 smoke test 通过
  - 用户看过结果

- `LIGHT / STANDARD`
  - Execution Brief 存在
  - Dev evidence 存在
  - QA verdict = PASS
  - 用户看过结果

- `FULL`
  - Requirement Card confirmed
  - Architecture Packet confirmed
  - Dev evidence 存在
  - QA verdict = PASS
  - 用户看过结果

### Pre-Existing Test Failures

Ship 前如果有非本次引入的红色测试，必须显式处理（三选一）：

1. **立即修**：在本次 PR 内修复
2. **显式跳过**：加 `KNOWN-BROKEN` 注释 + skip 标记
3. **记录 tech-debt**：在汇报中标注"非本次 regression"并进入 tech-debt 清单

**禁止静默忽略**。

### Git Rules

- commit 之前必须用户确认
- push 只有用户明确说 push 才做
- 如果工作区有别人的脏改动，必须先提示范围风险

---

## Memory Anchor Integration

### A. Start Of Task

如果 Memory Anchor 可用，Build 2 开始时固定做：

```text
ToolSearch("memory-anchor")
get_context()
search_checkpoints()
search_rules()
```

默认静默执行，除非结果改变拓扑、风险或续跑决策。

### B. During Task

用同一个 `task_id = build2-{feature-slug}` 做 UPSERT checkpoint：

- 开始执行：`task_status = in_progress`
- 等用户确认 / 等外部依赖：`task_status = blocked`
- 完成：`task_status = completed`
- 放弃：`task_status = abandoned`

推荐补充字段：

- `task_specification`
- `files_and_functions`
- `workflow`
- `errors_and_corrections`
- `decisions`
- `living_docs`
- `trigger_patterns`
- `blocked_reason`
- `failed_assumption`
- `next_unblocker`
- `routing_feedback`
- `lessons_learned`

### C. End Of Task

完成后必须写一条压缩过的长期记忆：

**成功**

```text
[BUILD-SUCCESS] task_slug: {slug} | 任务: {功能描述} | 评分: {X}/10 | 拓扑: {拓扑} | 拓扑回顾: {合适/应该更重/应该更轻} | 跳过阶段: {PM/Architect/QA/无} | 跳过后果: {无问题/发现遗漏} | 耗时: {分钟} | 关键决策: {最重要的 1-3 条}
```

**失败**

```text
[BUILD-FAILURE] task_slug: {slug} | 任务: {功能描述} | 评分: {X}/10 | 拓扑: {选的} | 应该用: {回看应该用的} | 失败阶段: {Clarify/PM/Architect/Dev/QA/Ship} | 现象: {什么失败了} | 根因: {为什么} | 门控建议: {下次该升/降/保持} | 路由: {知识层/编排层/门控层}
```

推荐追加运行指标：

- `memory_hit`
- `clarify_count`
- `phase_skipped`
- `retry_count`
- `user_interruptions`
- `topology_hindsight`

### D. Outcome Feedback

如果这次执行直接证明某条旧的 `BUILD-*` 记忆判断错了：

```text
report_outcome(memory_id=旧记忆ID, outcome="corrected"|"outdated", reason="...")
```

这样 Hermes 进化不是“越记越多”，而是“会修正自己的旧判断”。

### E. Quiet Retrospective

每次任务关闭后，默认再做一次 **60 秒静默复盘**。

至少提炼这 5 件事：

- `topology_fit`：这次拓扑选得对不对
- `avoidable_rework`：有没有本来能提前避免的返工
- `missing_artifact`：有没有缺失的 brief / test / QA 证据
- `false_guardrail`：有没有过度门控或无效门槛
- `reusable_pattern`：有没有能复用到后续任务的方法

这一步默认不打扰用户，除非：

- 需要立刻调整下一步计划
- 发现了跨项目可复用的高价值规则

### F. Rule Candidate Memory

如果复盘提炼出了方法，不要立刻升成“永久规则”，先写成候选：

```text
[BUILD-RULE-CANDIDATE] topic: {routing|clarify|brief|dev|qa|ship|memory} | pattern: {观察到的模式} | recommendation: {建议动作} | confidence: {low|medium|high} | evidence_count: {N} | source_tasks: {task_slug1,task_slug2,...} | provenance: {memory_ids/brief notes}
```

原则：

- 单次任务提炼出的候选，默认 `confidence=low`
- 有明确失败复现或连续成功复现，才升到 `medium`
- 不允许因为一次巧合就改全局规则

### G. Review Windows And Promotion

Build 2 的经验晋升，按 **AutoResearch 风格** 做，不按“谁声音大”做。

触发静默 review window 的时机：

- 任意一次 `BUILD-FAILURE`
- 用户人工覆盖了拓扑
- 连续 3 次同形成功（例如都说明 `LIGHT` 比 `STANDARD` 更合适）
- 累计关闭 5 个 build 任务

review window 至少回答：

- 哪些做法重复成功
- 哪些做法重复失败
- 哪些 candidate 值得晋升
- 哪些旧规则应该降级或纠正

如果满足以下任一条件，可晋升为持久规则：

- 同一候选被 **3 个以上任务** 支持
- 或 **2 个任务 + 1 次明确纠错** 指向同一结论
- 且最好覆盖 **2 个以上会话或项目**

晋升动作：

1. 写一条 `[BUILD-REVIEW]`
2. 更新本地 ledger：`~/.claude/projects/memory/build_evolution.md`
3. 如有必要，再写持久规则：

```text
[BUILD-RULE] topic: {topic} | rule: {稳定后的规则表述} | evidence_count: {N} | promoted_from: {candidate_id or review_id}
```

如果后续被新事实推翻：

- `report_outcome(...)`
- 在 `build_evolution.md` 把状态改成 `corrected / outdated`

### H. Silent Start / Silent End

默认用户看到的是：

- 评分与拓扑
- 要做什么
- 做完了什么
- 风险与限制

默认用户**看不到**的是：

- 记忆 bootstrap 的内部细节
- checkpoint 的中间写回
- 候选规则的草稿
- review window 的中间推理

除非用户明确问“回忆一下 / 你学到了什么 / 给我看复盘”。

### I. User-Facing Summary Contract

不管内部跑了多少 phase，最终给用户的摘要默认压缩成 4 件事：

1. `what_changed`
2. `proof`
3. `risk`
4. `decision_needed`

这 4 个字段是用户态 contract。

- Dev / QA / Ship 都应该产出能压缩进这 4 项的材料
- 默认不要把 memory bootstrap、候选规则草稿、review window 中间推理原样展示给用户

### J. Experience Ownership Matrix

经验回灌时，先判断该改哪一层：

| 现象 | 默认回灌层 |
|------|-----------|
| 路由总是过重/过轻 | `SKILL.md` 的 triage / topology 规则 |
| PM / Dev / QA / Ship 某个角色反复做错 | 对应 agent 文件 |
| 某次任务的临时教训 | Memory Anchor |
| 已经跨任务复现的方法 | `build_evolution.md` → 再决定是否升到 `SKILL.md` |
| 只是项目局部事实，不适合全局化 | 只写 checkpoint / 项目记忆，不改 build 规则 |

Build 2 的优化，不应该停留在“知道有问题”，而必须落到“知道该改 skill、agent、还是 memory”。

---

## Context Compression Rules

只传结构化摘要，不传完整过程：

| 上游 → 下游 | 允许传递 | 不允许传递 |
|-------------|----------|------------|
| Team Lead → PM | 用户请求 + 已知上下文 | 长篇自我推理 |
| PM → Architect | Requirement Card | 逐问逐答全文 |
| Architect → Dev | Architecture Packet | 模型长推理 |
| Team Lead → Dev | Execution Brief | 冗长聊天记录 |
| Dev → QA | Dev Report + Sprint Contract + evidence | 调试碎片 |
| QA → Ship | QA Report | 大段扫描日志 |

---

## Degrade Gracefully

### Memory

- `ToolSearch("memory-anchor")` 失败 → 继续跑，但标注 `memory_mode=off`

### Clarify

- `AskUserQuestion` 不可用 → Team Lead 用最短的 1 轮纯文本问题替代

### Team Shell

- `TeamCreate / TaskCreate` 不可用 → 直接串行 spawn agents

### Architect

- Codex 不可用 / 超时 → Lite 架构

### QA

- Gemini / 额外校验工具不可用 → 只跑核心 QA，并明确标注未交叉验证
- 测试框架缺失 → 用 curl / script / screenshot 做最小可证据验证

---

## Pitfalls

- 不要让 command、skill、agents 三套逻辑分叉
- 不要再让 `STANDARD` 为了 1-2 个问题就强行 spawn PM
- 不要让 `LIGHT` 因缺架构文档而卡住
- 不要让小任务写 10 条 Sprint Contract
- 不要把整段日志塞进 Memory Anchor
- 不要把“续跑”误当成“新任务”

---

## Self-Evolution Protocol

> Build 3.0 的核心升级：教训不再只是写在外挂台账里，会自动反哺进 SKILL.md 本体。

### 触发条件

自进化在以下时机自动执行（不需要用户手动触发）：

1. **Review Window 晋升 BR 时** — 候选规则通过晋升门槛后
2. **严重 CORRECTION 发生时** — 用户纠正了 build 的行为
3. **累计 5 个 BRC 未处理时** — 候选积压触发批量审查

### 自进化流程

```
Step 1: 识别变更类型
  ┌─ 新 BR 晋升 → 找到 SKILL.md 中应插入的位置（Core Rules / Dev / QA / Ship / Memory）
  ├─ CORRECTION → 找到 SKILL.md 中对应的旧规则，追加/修正
  └─ 旧 BR 被推翻 → 找到 SKILL.md 中对应规则，标记 outdated 或删除

Step 2: 生成 SKILL.md diff
  - 精确到要插入/修改的 section
  - 保持现有结构不变，只做增量
  - 新规则必须带 > 来源: BR-XXX / BRC-XXX / CORRECTION-日期

Step 3: 应用变更
  - 低风险（新增规则、补充说明）→ 直接 Edit，在复盘报告中标注
  - 高风险（删除规则、改变路由逻辑）→ 标注 [PENDING-USER-REVIEW]，等用户确认

Step 4: 同步台账
  - 更新 build_evolution.md 中对应 BR 的状态为 `absorbed`
  - 在 MA 中 add_rule: [BUILD-SELF-EVOLVE] 记录本次 SKILL.md 变更
```

### 版本号约定

自进化产生的变更自动 bump patch 版本：

- 新增规则：`3.0.x` → `3.0.x+1`
- 修正规则：`3.0.x` → `3.0.x+1`
- 删除/重构规则：需要 bump minor `3.x.0` → `3.x+1.0`，且需用户确认

### 防过度进化

- SKILL.md 总行数上限 **900 行**，超过时必须先精简再加新规则
- 同一个 Section 不超过 5 条规则，超过时合并或提炼更通用的表述
- 每次自进化最多改 3 处，防止一次性大改
- 自进化不能删除 Core Rules (Rule 1-7)，只能追加或修正 Rule 8+

### 与 /evolve 的关系

- `/evolve` 管 **instinct**（代码编辑模式、文件修改习惯）
- `/build` Self-Evolution 管 **build rules**（流水线门控、角色协作、QA 标准）
- 两者独立运行，但共享 Memory Anchor 作为数据源
- /evolve 发现的 instinct 如果与 build 流程相关（如"build 时总忘记跑 QA"），会被标记为 build-relevant，下次 build review window 时自动拉入

---

## Verification

Build 3 改完后，至少要满足这些自洽条件：

1. `/build` command 是薄入口，不再复制全量逻辑
2. `SKILL.md` 是唯一真相
3. Dev / QA / Ship 都以 `Execution Brief` 为最低共同契约
4. 任一拓扑都不会因为缺不存在的 artifact 而自锁
5. Memory Anchor 的 `get_context / search_checkpoints / add_rule / save_checkpoint / report_outcome` 都有明确位置
6. 任务关闭后有静默复盘与 `BUILD-RULE-CANDIDATE / BUILD-REVIEW` 机制
7. 本地 `build_evolution.md` 作为可审阅 ledger，与 Memory Anchor 形成双层闭环
8. **Self-Evolution Protocol 确保教训自动反哺进 SKILL.md，不再只停留在台账和 MA 里**
9. **新增规则都标注了来源（BR/BRC/CORRECTION），可追溯**
