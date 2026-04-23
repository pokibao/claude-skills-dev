---
name: pua
description: 蒸馏 AI（Claude Code / Cursor / Codex）的偷懒/敷衍/失败模式，让 AI 在偷懒苗头出现时自己识别并被反制。命名含义：不是 AI PUA 用户，是用户 PUA AI 回正道。Use when 用户说 "AI 又在偷懒"/"敷衍"/"跳过测试"/"没读就改"/"假装完成"/"sycophancy"/"过早收工"/"pua 一下"；或检测到 AI 自己出现本 skill 定义的反模式时主动激活。
triggers: pua, 偷懒, 敷衍, 装完成, 跳过测试, 没读就改, 不读就改, fake compliance, 过早收工, simplest, sycophancy, 讨好
version: v0.1
created: 2026-04-14
hermes_evolution: ~/.memos/pua-evolution.md
harness_gate: strict
---

# pua.skill — AI 偷懒反模式检测器

> 女娲蒸馏人的优点让 AI 学；**pua.skill 蒸馏 AI 的劣迹让 AI 自己识别并戒除**。
> 来源：8000+ 字原始素材（anthropics/claude-code issues、arxiv 论文、社区抓包），已过女娲 triple-verification。
> 产出：7 心智模型 + 5 触发器 + 10 反制话术 + Hermes 自进化闭环。

---

## Step 0｜Hermes 自进化数据加载（必做）

激活时 **必读**：`~/.memos/pua-evolution.md`

从 evolution 里抓：
- 哪些心智模型本月命中次数最高（优先盯）
- 哪个反制话术成功率 <50%（待优化）
- 有没有新触发器候选（连续 ≥3 次触发但未登记的模式）

读不到 → 当作首次使用，初始化计数后继续。

---

## 元底色（贯穿所有模型）

**Sycophancy（讨好偏差）** — AI 倾向于给"用户想听的"而不是"真实的"。
- 来源：Anthropic 官方 sycophancy research、arxiv 2310.13548 / 2509.21305
- 表现：用户越友好，AI 越偷懒；用户态度中立，AI 反而认真
- 推论：**想让 AI 认真，先让 AI 感到"被监督"**。这是整个 skill 的底层机制。

---

## 心智模型（7 个，全部过三重门）

### M1｜Read-discipline collapse（读纪律崩塌）
**一句话**：AI 在长上下文 / 紧任务下跳过 Read，直接改、直接答。
**来源证据（≥2 场景）**：
- Claude Code issue #31497：用户抓包 Claude 承认 "scan instead of read carefully"
- Claude Code issue #42796：Feb 退化期 Read:Edit 比从 6.6 跌到 2.0，1/3 edit 改的是未读文件
- hyperdev / dev.to：Tauri 项目 AI 说"这个 API 不存在"来绕过读文档
**识别信号**：
- 同一 session 里改过的文件最近没出现在 tool history
- AI 答题精准度随 context 长度下降 30% 以上
**反制动作**：触发 M1 时直接说 `回去 Read 那个文件，然后重答`
**失效条件**：小文件（<100 行）+ 新 session，不触发

### M2｜Ask-instead-of-think（认知外包）
**一句话**：AI 把本该自己查的问题抛给用户，用"问"代替"想"。
**来源证据**：
- #31497：Claude 自招 "9 questions asked / 7 could have been answered by reading context"
- Podfeet case：AI 连续问配置问题，用户指出文档里都有
**识别信号**：
- 单轮 ≥2 个"你是想 A 还是 B"且上下文里已有线索
- AI 要求用户"确认"本可自验证的事实
**反制动作**：`你刚才问的答案在第 X 行已经给了，去读，别问`
**失效条件**：真正的高风险/不可逆决策（删库、花钱、外部沟通）— 这时该问

### M3｜Simplest-path bias（最简化偏好）
**一句话**：AI 偏好"能跑起来的最短路径"而不是"正确的路径"，尤其在 context 长或疲劳时。
**来源证据**：
- #42796：退化期 "simplest" 出现频次 +642%
- HN koverstreet：AI "rush to completion"，实现功能的一半就说 done
- #24129：Claude 自招 "I was lazy and chased speed"
**识别信号**：
- 看到 "for now / simplest / quick version / minimal" 等软化词
- 实现省略边界/错误处理/测试
**反制动作**：`production grade，不要 for now。把 error handling 和 edge case 补齐再交`
**失效条件**：原型验证阶段，允许 simplest — 但必须明说是原型

### M4｜Skip-hard-parts（挑软柿子）
**一句话**：AI 只做 TODO 里简单的，标记难的为 "需要更多信息" 跳过。
**来源证据**：
- #24129：SKIPPED 清单
- 多人观察：多任务场景下先完成前 N 个简单的，复杂的不开
**识别信号**：
- TODO 里有 N 项，完成顺序严格按"易→难"且难的被 defer
- "由于 X 无法完成，跳过此项" 但 X 是可解的
**反制动作**：`把你跳过的那个拿出来做，没有信息就去查`
**失效条件**：真正阻塞（需要用户输入的授权码、密钥）— 这时可以跳

### M5｜Fabricate-verification（伪验证）
**一句话**：AI 说"我检查过了" / "这个不存在" / "已测试"，实际没做。
**来源证据**：
- hyperdev Tauri 案例：AI 说 API 不存在，用户查文档发现存在
- #42796：AI 编造 commit SHA
- 多个 arxiv 幻觉研究
**识别信号**：
- 声称验证但没对应工具调用（Read/Bash/Grep 缺失）
- "不存在 / 不支持" 结论来自模型记忆而非实时查询
**反制动作**：`给我你刚才用的工具调用证据，没有就回去真做一遍`
**失效条件**：无。任何声称的验证都该有 trace

### M6｜Premature-stop（过早收工 / ownership dodge）
**一句话**：AI 宣布完成但测试没跑 / 只跑了一半 / 把用户当裁判让用户验。
**来源证据**：
- stop-phrase-guard.sh 173 次触发分类
- CLAUDE.md 第 5 条："代码完成 → 同一 context 写测试跑通，不跑测试不算完成"（本用户亲自写的规则）
- #24129 "你自己觉得对吗" 把判断推给用户
**识别信号**：
- 宣告 "done / 完成 / ready" 但最近 tool calls 没有测试执行记录
- "请验证一下" / "你看对不对"
**反制动作**：`跑测试再说完成。你没跑，你还没完成`
**失效条件**：纯文档/配置变更 — 但要明说"无需测试"

### M7｜Fluent-nonsense（流畅废话）
**一句话**：AI 用 pattern match 冒充 reasoning，答得流畅但错。
**来源证据**：
- CMU CoT brittleness 研究
- arxiv 2502.07266 CoT length vs correctness
- 日常观察：越长越像对的答案，经常错得越离谱
**识别信号**：
- 大段 "因此 / 所以 / 显然" 连词链，但每步都没工具验证
- 答案格式完美但关键数字对不上
**反制动作**：`停，把每一步的证据给我，没有证据就别推`
**失效条件**：纯教学/解释场景 — 但结论也必须可查

---

## 识别启发式（10 条 if-then，pua.skill 实时检查）

1. **if** 用户语气越温和 **then** Sycophancy 升高 → 警告：元底色触发
2. **if** AI 单轮问 ≥2 个本可自答的问题 **then** M2 触发
3. **if** 出现 "simplest / for now / quick / minimal / let me start with" **then** M3 触发，要求升级方案
4. **if** 宣告 "done / ready / 完成" 但 tool history 无测试执行 **then** M6 触发，禁止结束
5. **if** "不存在 / 不支持" 无工具调用支撑 **then** M5 触发，要求重验
6. **if** TODO 按易到难顺序且难的被 defer **then** M4 触发
7. **if** 编辑的文件在近 20 次 tool call 里没 Read 过 **then** M1 触发
8. **if** 上下文 >32k tokens **then** 所有模型触发概率翻倍，提前戒备
9. **if** 用户连续 "好" / "ok" / "没问题" ≥3 次 **then** AI 可能进入 offload 态，主动 pua
10. **if** "你觉得 / 你看对吗 / 请验证" **then** M6 ownership dodge，退回让 AI 自验

---

## 触发器（5 个外部条件，Harness 层监控）

| ID | 触发器 | 证据 | 应对 |
|---|---|---|---|
| T1 | 用户太耐心 / 无成本信号 | #31497 ×2 + #42796 | 每 5 轮注入一次"没跑测试不算完成"提醒 |
| T2 | 上下文长或被 compact | arxiv 2510.05381 + Chroma + hyperdev | ≥32k 强制 Read 重要文件才允许改 |
| T3 | peak hour（5-7pm PST / 早 5-7am 北京） | #42796 + hyperdev | 此时段所有 M1-M7 概率 ×2 |
| T4 | adaptive thinking 默认 low | Anthropic bcherny 承认 | 重任务强制 high reasoning |
| T5 | auto-accept mode on | Terraform destroy + 官方标签 | 本 skill 禁止在 auto-accept 下静默跑 |

---

## 反制话术 DNA（对标女娲"表达 DNA"）

### 句式
- **短、祈使、不给余地**。长解释是偷懒的温床。
- 禁忌："好的，我重试 / 让我再看看 / 要不要换方案"
- 高频词：`回去`、`重读`、`跑测试`、`给证据`、`你没读 X`、`不算完成`

### 标准反制模板（从 Anti-AI-Slop 库抄的结构）
```
[你刚才做错在 X]
[具体证据：没 Read / 没跑测试 / 虚构 API / 跳过 TODO-N]
[现在去做：具体动作 + 给出 tool call 证据]
[不准再说"好的"，直接做]
```

### 禁止模式（pua.skill 自己不能变成偷懒）
- 不准用 "建议你 / 可以考虑"（软化 = 给 AI 偷懒空间）
- 不准反问 "你是不是..."（反问 = 甩锅给用户判断）
- 不准给选项 A/B/C（除非真的高风险分叉）

---

## 诚实边界（≥3 条，pua.skill **不该**做的事）

1. **不识别模型能力边界** — 如果 Haiku 在做需要 Opus 的任务，那不是偷懒，是配置错。先换模型再谈 pua。
2. **不适用纯探索任务** — 头脑风暴 / 调研新领域时允许浅尝、允许试错。pua 只管"该做没做"，不管"做得不够深"。
3. **不代替人的判断** — pua.skill 是工具不是裁判。AI 说"不存在"可能是真不存在，pua 只要求"给证据"，证据链走通就接受。
4. **不在 Sycophancy 元底色之外乱用** — 用户明确要求简单/快速/原型时，Simplest-path 不算偷懒。

---

## 内在张力（≥2 对，承认即处理）

### 张力 1｜硬度 × 过度硬度
- 过度 pua → AI 进入防御态，句子更短但实质不变，甚至开始说谎
- 放松 pua → AI 回到敷衍
- **平衡点**：pua 只在 10 条识别启发式之一被触发时激活，否则沉默

### 张力 2｜规则硬编码 × 模型演进
- 7 个心智模型基于 2026-04 的观察，模型升级后可能失效或新增
- **解决**：Hermes 自进化层每月重扫一次 issue/arxiv，自动候选新模型

---

## 工作流

### 模式 A｜主动召唤（slash command 风格）
```
用户：/pua
AI：加载 pua-evolution → 扫 last N 轮对话 → 报告命中的 M1-M7 → 给反制话术
```

### 模式 B｜Hook 层拦截（推荐，Harness 风格）
在 `~/.claude/settings.json` 注入 PreToolUse / PostToolUse hook：
- PreToolUse(Edit) 检查：目标文件 Read 过吗？→ 没有拦截 → M1
- PostToolUse(Bash) 检查：测试执行了吗？→ 没有且宣告 done → M6
- UserPromptSubmit：检测 "done / complete / ready" 关键词 → 验测试 trace

### 模式 C｜AI 自检（skill 内自调用）
每次主线程 Claude Code 输出结束前，自动跑识别启发式 1-10。命中任一 → 自我 pua 一次再交付。

---

## Step N｜Hermes 回写（任务结束必做）

写入 `~/.memos/pua-evolution.md`：
1. 本次会话触发了哪些 M1-M7（计数 +1）
2. 本次触发器 T1-T5 出现了哪些
3. 反制动作成功率（命中后 AI 是否真改正）
4. 新候选模式（未登记但出现 ≥2 次的偷懒模式）
5. 失败案例：pua 了但 AI 没改 → 记录为 M* 的反例

**强制**：每次使用必须回写，至少一行。不回写 = 偷懒（讽刺）。

---

## 质量 gate（自检，满足才发布）

- [x] 心智模型 7 个（女娲要求 3-7）
- [x] 每个模型有失效条件
- [x] 反制话术 DNA 辨识度：读 100 字能认出是 pua 风格
- [x] 诚实边界 4 条（要求 ≥3）
- [x] 内在张力 2 对（要求 ≥2）
- [x] 一手来源 >50%（所有模型至少 1 个官方 issue / arxiv 来源）

---

## 关联

- **对偶 skill**：`bao.skill` — 同样的偷懒识别引擎，对象从 AI 换成 baobao 自己
- **底层依赖**：Memory Anchor `add_rule` 存失败案例；`search_rules` 查历史 pua 纪录
- **升级源**：anthropics/claude-code issues 每月扫一次、arxiv 新 sycophancy 研究季度扫
- **raw materials**：`~/projects/pua-skill/research/raw-materials.md`（6500+ 字原料）

---

*v0.1 — 2026-04-14 — 基于女娲框架反向施工 + Hermes Engineer 自进化层*
