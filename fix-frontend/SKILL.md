---
name: fix-frontend
description: |
  前端 Bug 修验闭环工作流。结合 Glance MCP（浏览器眼睛）+ Hermes 经验引擎（越用越聪明）+ git 原子操作（秒回滚），
  系统化解决"修A坏B"问题。每次修 bug 自动：搜经验→截基线→诊断根因→原子修复→视觉对比→回归检测→存经验。
  Use when fixing frontend bugs, CSS issues, animation bugs, layout regressions, or any visual UI problem.
  Triggers: "修前端", "fix frontend", "UI bug", "样式问题", "动画bug", "布局错位", "修A坏B", "前端回归"
  Voice triggers: "fix the frontend", "UI is broken", "fix this bug"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
---

# /fix-frontend — 前端 Bug 修验闭环（Hermes 自进化）

> 核心公式：**搜经验 → 截基线 → 诊断根因 → 原子修复 → 视觉对比 → 回归门控 → 存经验**
> 架构：Glance MCP（眼睛）+ Memory Anchor Hermes（大脑）+ git（安全网）
> 设计原则：修一个 bug 绝不能引入另一个 bug。做不到就 revert。

---

## 触发方式

```bash
/fix-frontend                           # 交互式：描述 bug 或丢截图
/fix-frontend 按钮点击没反应              # 直接描述 bug
/fix-frontend --page /dashboard         # 指定页面
/fix-frontend --component InventoryTable # 指定组件
```

---

## 执行流程（7 个 Phase，严格顺序）

### Phase 0: 加载经验（每次自动执行，静默）

```
必须执行（不可跳过）：
1. ToolSearch("memory-anchor") → 加载 MA 工具
2. search_experiences(query="前端 bug {用户描述的关键词}", limit=5) → 查历史经验
3. get_experience_surfaces(target="hermes", topic="frontend-bug-fix") → 读 Hermes 经验包

如果命中相关经验（search_score > 0.5）：
  → 显示："找到类似经验：{title}，上次根因是 {root_cause}，修复方案是 {fix}"
  → 问用户："要直接应用这个方案吗？(y/n)"
  → y → 跳到 Phase 3 直接修复
  → n → 继续正常流程

如果无命中：
  → 静默继续，不打扰用户
```

### Phase 1: 截基线（修之前的状态）

```
目标：记录修改前所有相关区域的视觉状态，作为回归对比的基准

工具选择（按优先级）：
  1. Glance MCP (browser_navigate + browser_screenshot) — 首选，截图返回 base64，AI 能直接看
  2. Peekaboo (mcp__peekaboo__see) — 备选，macOS 层面截屏
  3. gstack browse — 备选，无头浏览器

操作：
  1. 确认 dev server 在跑（检查端口 3000/5173/8080）
  2. 导航到 bug 所在页面
  3. 截图保存：
     - 整页截图 → /tmp/fix-frontend/baseline/full_{timestamp}.png
     - bug 区域截图 → /tmp/fix-frontend/baseline/target_{timestamp}.png
     - 如果用户提到了其他可能受影响的页面，也截图
  4. 记录当前 git hash：git rev-parse HEAD

输出给用户：
  "[基线] 已截图 N 个区域。当前 git: {hash}"
```

### Phase 2: 诊断根因（只看不改）

```
铁律：此阶段 **禁止修改任何代码文件**。只读、只分析。

步骤：
  1. 读 bug 相关组件代码（Read tool）
  2. 读 CSS/样式文件
  3. 如果是动画 bug → 检查 transition/animation/transform 属性
  4. 如果是布局 bug → 检查 flex/grid/position/z-index
  5. 如果是链路 bug → 检查 useEffect/useState/props 传递链

输出（必须包含以下 4 项）：
  1. **根因**：一句话说清楚为什么出 bug
  2. **涉及文件**：列出要改的文件路径和行号
  3. **修改方案**：具体改什么、怎么改
  4. **影响范围**：这个改动可能影响哪些其他组件/页面

用 AskUserQuestion 确认：
  "我的诊断如上。确认方向对吗？确认后我开始修复。(y/n/调整方向)"
  
  用户说 n → 重新诊断，不要硬改
  用户说调整 → 按用户指示调整方案
```

### Phase 3: 原子修复（只改一个文件）

```
铁律：
  - 一次只改一个文件（如果需要改多个文件，拆成多轮，每轮走完整的 Phase 3-5）
  - 不"顺手优化"任何不相关的代码
  - 不加 !important（除非是覆盖第三方库样式的唯一办法）
  - 不加 setTimeout/requestAnimationFrame 作为"修复"（这是掩盖问题）
  - 不硬编码 px 值来"对齐"（找到布局系统的正确用法）

操作：
  1. git stash（保护未提交的其他改动）
  2. Edit 工具修改目标文件
  3. 等待 HMR 热更新（如果 dev server 在跑）

禁止列表（症状修复，不是根因修复）：
  ❌ 加 !important 来覆盖样式冲突
  ❌ 加 setTimeout 来"等 DOM 渲染完"
  ❌ 硬编码 width/height/margin/padding 的像素值
  ❌ 复制粘贴组件来"隔离"问题
  ❌ 改 z-index 到 9999
  
  如果发现自己要用以上任何一种 → 停下来，回到 Phase 2 重新诊断根因
```

### Phase 4: 视觉验证（修之后截图）

```
操作：
  1. 等 2 秒让 HMR 完成
  2. 用与 Phase 1 相同的工具和位置重新截图
     - 整页截图 → /tmp/fix-frontend/after/full_{timestamp}.png
     - bug 区域截图 → /tmp/fix-frontend/after/target_{timestamp}.png
     - Phase 1 截过的其他页面也要重新截

  3. AI 视觉对比（核心步骤）：
     读取 baseline 和 after 的截图，逐区域对比：
     
     对于每个截图区域，回答：
     a) bug 修好了吗？ (fixed / partial / not_fixed)
     b) 其他地方有新问题吗？ (clean / regression_detected)
     c) 如果有 regression → 具体描述什么变了

  4. 如果有 Glance MCP → 用 visual_compare 做像素级对比
     如果没有 → 用 AI 视觉能力（读两张图对比）

输出：
  "[验证] Bug 修复状态: {fixed/partial/not_fixed} | 回归检测: {clean/regression_detected}"
```

### Phase 4.5: Santa Method 双盲审查（STANDARD/FULL 拓扑时执行）

```
核心问题：同一个 AI 写代码又审代码，携带相同的盲点和偏差。
解决方案：spawn 第二个独立 Agent 做审查，不共享修复上下文。

触发条件：
  - 改动涉及 3+ 个文件
  - 改动涉及状态管理/数据流
  - 已经是第 2+ 轮重试

流程：
  1. 主 Agent 完成 Phase 4 视觉验证后，输出修复摘要
  2. Spawn 独立 Reviewer Agent（用 Agent tool，subagent_type=general-purpose）
     Prompt 只包含：
     - 原始 bug 描述
     - 修改的 diff（git diff）
     - Phase 4 的截图
     - DESIGN.md 约束
     ** 不包含 **：Phase 2 的诊断过程、修复思路、已排除的方案
  3. Reviewer 独立判断：
     a) 修复是否正确？（不是"看起来对"而是"逻辑上对"）
     b) 是否引入新的副作用？
     c) 是否有更简单的修复方案？
     d) 代码是否符合 DESIGN.md？
  4. 评分：PASS / CONCERN / FAIL
     - PASS → 进入 Phase 5 commit
     - CONCERN → 列出具体担忧，主 Agent 决定是否处理
     - FAIL → revert，采纳 Reviewer 建议的替代方案

关键原则（来自 ECC Santa Method）：
  "Make a list, check it twice. Naughty or Nice."
  两个独立审查者（无共享上下文、相同评分标准）都通过才能发布。
```

### Phase 5: 回归门控（通过/回滚）

```
决策树：

  bug_fixed=yes AND regression=none AND (santa=PASS OR santa=skipped):
    → ✅ git add {changed_file} && git commit -m "fix({component}): {一句话描述}"
    → 输出："✅ 修复成功，已提交。"
    → 进入 Phase 6

  bug_fixed=yes AND regression=detected:
    → ⚠️ 输出："bug 修好了，但检测到回归：{描述}"
    → AskUserQuestion: "接受这个 tradeoff 提交？还是回滚重新来？(commit/revert)"
    → commit → git commit
    → revert → git checkout -- {changed_file} → 回到 Phase 2 换方案

  bug_fixed=no AND regression=none:
    → ❌ git checkout -- {changed_file}
    → 输出："修复无效，已回滚。重新诊断中..."
    → 回到 Phase 2，但标记 "方案A 无效，换思路"

  bug_fixed=no AND regression=detected:
    → ❌❌ git checkout -- {changed_file}
    → 输出："修复无效且引入新问题，已回滚。"
    → 回到 Phase 2，但标记 "方案A 不仅无效还有副作用"

重试上限：
  同一个 bug 最多重试 3 轮（Phase 2-5）。
  3 轮后仍未修复 → 输出完整诊断报告 + 已尝试方案列表，让用户决定下一步。
```

### Phase 6: 存经验（Hermes 自进化）

```
每次 Phase 5 结束后（无论成功失败），都存经验：

成功时：
  add_rule(
    content="[SUCCESS] 前端Bug修复: {组件} | 现象: {bug描述} | 根因: {root_cause} | 修复: {具体改动} | 文件: {file_path}:{line}",
    memory_kind="procedure",
    category="bug",
    confidence=0.95,
    steps=[诊断步骤, 修复步骤, 验证步骤],
    activation_cues=[bug现象关键词, 组件名, 错误表现],
    success_signal="截图对比无回归 + 目标bug消失",
    failure_modes=[Phase 2 中排除的错误方向]
  )

失败时：
  add_rule(
    content="[FAILURE] 前端Bug修复: {组件} | 现象: {bug描述} | 尝试方案: {what_was_tried} | 失败原因: {why_it_failed} | 路由: {知识层/编排层/门控层}",
    memory_kind="procedure",
    category="bug",
    confidence=0.9,
    steps=[尝试的步骤],
    activation_cues=[bug现象关键词],
    failure_modes=[为什么这个方案不行]
  )

周期性（每 5 次修复后，或用户主动触发）：
  build_experience_artifacts(target="hermes", topic="frontend-bug-fix")
  → 编译所有前端修 bug 的经验为 Hermes 经验包
  → 下次 Phase 0 自动加载
```

---

## 工具优先级

| 场景 | 首选 | 备选1 | 备选2 |
|------|------|-------|-------|
| 截图 | Glance `browser_screenshot` | Peekaboo `see` | gstack `browse` |
| 导航 | Glance `browser_navigate` | claude-in-chrome `navigate` | gstack `browse` |
| 像素对比 | Glance `visual_compare` | AI 视觉对比（读两张图） | 手动确认 |
| 代码修改 | Edit tool | — | — |
| 回滚 | `git checkout -- {file}` | `git stash pop` | — |
| 经验存取 | Memory Anchor | — | — |

---

## 反模式检测（自动触发警告）

在 Phase 3 修改代码时，如果检测到以下模式，**立即停止并警告用户**：

```
⚠️ ANTI-PATTERN: 正在添加 !important — 这通常是症状修复，不是根因修复
⚠️ ANTI-PATTERN: 正在添加 setTimeout — 这通常是竞态掩盖，不是正确的生命周期处理
⚠️ ANTI-PATTERN: 正在硬编码像素值 — 这通常是布局系统没用对
⚠️ ANTI-PATTERN: 正在设置 z-index > 100 — 这通常是层叠上下文没理清
⚠️ ANTI-PATTERN: 正在修改超过 2 个文件 — 原子修复应该只改 1 个文件
⚠️ ANTI-PATTERN: 已经是第 3 轮重试 — 可能需要换思路或请人帮忙
```

---

## 快捷模式

```bash
/fix-frontend quick     # 跳过 Phase 0 经验搜索，直接开始（紧急 bug 用）
/fix-frontend learn     # 手动触发 build_experience_artifacts 编译经验包
/fix-frontend history   # 查看最近 10 次修复的成功/失败记录
/fix-frontend revert    # 撤销最近一次修复（git revert HEAD）
```

---

## 与现有 Skill 的关系

- `/qa` — 发现 bug 的工具。`/qa` 发现 → `/fix-frontend` 修复 → `/qa` 验证
- `/design-review` — 设计层面的审查。与 `/fix-frontend` 互补
- `/investigate` — 深度调试。如果 `/fix-frontend` 3 轮搞不定，升级到 `/investigate`
- `/ship` — 上线验收。所有 bug 修完后用 `/ship` 做最终验收
