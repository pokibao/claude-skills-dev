---
name: daily-digest
description: "信息消化引擎 — 多平台文章抓取+评论提取+MA关联分析+竞品拆解+自进化。触发词：帮我看文章、今日信息流、学习一下、daily digest、读一下这些链接"
triggers:
  - "/daily-digest"
  - "帮我看文章"
  - "今日信息流"
  - "学习一下"
  - "读一下这些链接"
  - "daily digest"
---

# /daily-digest — 信息消化引擎

> 不只是"帮你读文章总结一下"。是你整个AI系统的感官入口 — 每天把外部世界的信息消化成系统能理解的格式。
> 设计哲学: Hermes(自进化) + Harness(工程纪律) + Meta-Harness(原始轨迹>摘要) + **Karpathy LLM Wiki (知识复利)**

## ⚠️ 硬性原则（2026-04-21 新增，违反 = 本 skill 失败）

**digest 的终点不是 `~/.memos/digest-*.md` 大 md，是 `~/projects/llm-wiki/` Karpathy 三层 wiki 的 ingest**。

- 终点错位的教训：2026-04-16 / 04-18 / 04-20 三次 digest 全部停在 `~/.memos/` 大 md，5 天欠账堆到 4/21 才一次补完（花 3-4h 工程）
- 正确终点：每个 source → `research-调研/digests-文摘/<slug>.md` · 每个实体 → `knowledge-知识/{people-人物|orgs-组织|products-产品|baobao-我的项目|events-事件}/<slug>.md` · 每个概念 → `knowledge-知识/concepts-概念/<slug>.md` · 跨主题 → `research-调研/comparisons-对比/` · 跨日叙事 → `research-调研/syntheses-综合/`
- `~/.memos/digest-YYYY-MM-DD-*.md` 只是**过程产出**（原始抓取数据+分析草稿），不是终点
- 违反本原则 = Step 9 没跑 = skill G7 gate 失败 = **本次 digest 不算完成**

## 用法

```
/daily-digest [粘贴URL列表]
/daily-digest --quick [URL列表]    # 只摘要，跳过深度分析
/daily-digest --deep [URL列表]     # 全量7维分析+评论+承上启下
```

默认模式 = `--deep`（因为你每次都想要深度分析）

---

## Sprint Contract（执行前输出）

每次运行前，先输出：
```
Sprint Contract:
  输入: N篇文章 (M个平台)
  预算: ~X tokens
  承诺交付:
    [ ] 每篇有分类标签 + 3句摘要
    [ ] 至少3篇有MA关联分析
    [ ] 至少1个虚拟点评（竞品作者看我们）
    [ ] 至少1个反向思考
    [ ] 行动建议关联到具体文件/记忆
    [ ] 评论/Community Notes提取（X必抓）
    [ ] 承上启下叙事线分析
  不做:
    [x] 不给空泛建议（"你应该做X"没有关联具体文件=废话）
    [x] 不遗漏任何URL
    [x] 不对没读到的文章编内容
```

---

## 执行流程

### Step 0.5: 抓取工具 Preflight（强制 — 2026-04-15 教训）

**规则**：抓取子 Agent 启动前，必须先验证工具链就绪，不能"打开就抓"。一条漏掉会导致 5 条全部 silent-fail。

**必做**：
1. ToolSearch 加载所需工具，拿到 schema
2. chrome: `tabs_context_mcp({createIfEmpty:true})` — 返回 `Browser extension is not connected` 立即 STOP，**不允许继续降级到 WebFetch 蒙混**（x.com WebFetch 必 402，降级是假降级）
3. agent-browser: 首篇先做一次 fetch 确认能拿到正文 > 100 字
4. 如扩展/链路未就绪 → **立即回报父 Agent 要求用户连接扩展 / 切换登录态**，不要靠经验"兜个底"

**2026-04-15 失败案例**：X batch A 直接把 Chrome 扩展未连接报成"5 条全未抓取"，但其实应该在第一条 preflight 失败就 STOP 给用户。

### Step 1: URL 分类 + 工具路由

```
URL → platform_detect() → 选工具:
  mp.weixin.qq.com  → agent-browser（唯一可行）
  x.com / twitter   → claude-in-chrome（Chrome扩展必须连接）
  douyin.com        → claude-in-chrome + JS提取
  arxiv.org         → WebFetch
  github.com        → gh CLI / WebFetch
  知乎/bilibili     → agent-browser
  其他              → WebFetch → 失败降级 agent-browser
```

**Harness 降级链:**
- agent-browser 超时 → chrome → WebFetch → 标记"未读取,附原始URL供手动查看"
- **X/Twitter 不降级**：扩展未连接 = STOP，不降级到 WebFetch（永远 402，是假降级）

### Step 2: 并行抓取

按平台分组，启动多个 Agent 并行抓取：
- **微信组**: 1个agent，用agent-browser逐篇打开+JS提取
- **X组**: chrome直接navigate+get_page_text
- **抖音组**: chrome navigate+JS提取描述
- **其他组**: WebFetch

每篇提取:
- 标题、作者/来源、发布时间
- 正文（前3000字）
- 标签/话题

### Step 3: 评论 + Community Notes 提取（重要！）

**X/Twitter — 必须完整抓取"推文生态"（2026-04-15 用户要求）：**

每条 X 推文必须跑完 5 步，少一步 = 抓取不合格：

```javascript
// Step A: 主文
document.querySelector('article[data-testid="tweet"] [data-testid="tweetText"]')?.innerText

// Step B: 引用推文（常被遗漏）
// 嵌套 article 或 [role="link"] 里的 tweetText
[...document.querySelectorAll('[data-testid="tweetText"]')].map(e=>e.innerText)

// Step C: 评论区 — 必须先滚动 3 次再读，否则虚拟滚动只渲染前 2 条
for (let i=0; i<3; i++) { window.scrollBy(0, 800); await new Promise(r=>setTimeout(r, 1500)); }

// Step D: Community Notes
document.querySelector('[data-testid="birdwatch-pivot"]')?.innerText

// Step E: Tab title vs URL 对照 — 防止跑错页
```

**验证门禁（每条必验）：**
- [ ] 主文字数 > 20
- [ ] 引用推文明确"已查/不存在"
- [ ] 评论 ≥ 5 条或明确"已滚动 3 次仍无评论"
- [ ] Community Notes 字段存在（即使为 none）
- [ ] Tab 标题和目标 URL 的 status ID 匹配

**抖音:**
- 点击"展开"按钮
- JS提取评论列表
- 侧边栏推荐视频标题（情报价值）

**微信:**
- agent-browser检查是否有留言区
- 有的话提取前10条热门评论

**Harness规则:** Community Notes和反对评论的信息密度 >> 正文。优先抓。

### Step 4: 内容去重 + 主题聚类

- 同一事件多篇报道 → 聚合为1条，保留最深度的作为主文，其他标"另见"
- 分类标签: `竞品` / `学习方向` / `生态信号` / `工具` / `无关`
- 按主题聚类，不按来源排列

### Step 5: MA 关联分析

对每篇文章执行:
```
search_rules(query=文章核心主题, limit=5)
```

标注:
- "MA已有相关记忆" → 附记忆ID和内容摘要
- "新信息，MA中无对应" → 标记为potential add_rule候选
- "与MA记忆冲突" → 特别标注，需要更新旧记忆

### Step 6: 7维深度分析

**对每个主题（不是每篇文章）执行:**

#### 6.1 反向思考
如果这篇文章的观点完全相反，会怎样？什么条件下反面成立？

#### 6.2 升级进阶
对我们的项目（MA、fstack、NA品牌、mission-control等）有什么具体帮助？
必须关联到具体文件/模块/记忆。

#### 6.3 竞品 vs 学习方向
分类 + 理由

#### 6.4 举一反三
这个洞察能跨域应用到哪里？从A领域→B领域的迁移。

#### 6.5 竞品拆解 + 虚拟点评
- 比我们强的地方（具体的，不是泛泛的）
- 模拟: 如果这个项目的作者看MA，他会说什么？（尖锐的，不是客气的）
- 模拟: 如果这个项目的用户来用MA，他第一个抱怨会是什么？

#### 6.6 承上启下
这些文章之间的叙事线是什么？它们在讲同一个故事的哪个部分？
输出叙事地图。

#### 6.7 行动建议
每个建议必须包含:
- 做什么（具体动作）
- 预期结果
- 风险
- 关联文件/记忆/checkpoint
- 优先级 P0/P1/P2

**禁止:** "你应该多关注XX领域" 这种没有具体动作的建议

### Step 7: 存入 MA

对每个有价值的发现，显式调用:
```
search_rules(query=发现主题)  → 检查是否已有相关记忆
如果是新发现 → add_rule(category=research, confidence=0.9+)
如果是竞品更新 → add_rule(room=competitive-intel)
如果是流程改进 → add_rule(memory_kind=procedure)
```

### Step 8: 手动追加 Evolution 记录

**这一步由 AI 显式执行（不是自动的）。** 运行结束时，用 Edit 工具追加一条记录到 `~/.memos/daily-digest-evolution.md` 的 `## 运行历史` 区域:
```yaml
- date: YYYY-MM-DD
  articles: N
  platforms: {weixin: X, x: Y, douyin: Z}
  fetch_success_rate: 成功数/总数
  best_insight: "一句话总结今天最有价值的发现"
  wiki_ingest: {sources: N, entities: N, concepts: N, comparisons: N, syntheses: N}  # ← Step 9 产出
  wiki_commit: <git sha 或 skipped reason>
```
**禁止预填估算值。只写实际测量到的数据。**

---

### Step 9: 自动 Ingest 到 llm-wiki（🔥 核心，不跑=skill 失败）

**目标**：把本次 digest 按 Karpathy LLM Wiki 三层架构 ingest 到 `/Users/baobao/projects/llm-wiki/`。

**Preflight**（跳过则标注原因并**显式警告**）:
```
1. ls /Users/baobao/projects/llm-wiki/ 确认存在
2. Read /Users/baobao/projects/llm-wiki/CLAUDE.md 加载 schema
3. Read 0-start-here-入口/hot.md 知道 current focus / recent ops
4. Read index.md 看已有页面清单（避免重复建）
```

**Ingest 流水线（对每个 URL / 每个实体 / 每个概念）**：

**9.1 · Source 建页**（每个 URL → 一个 research-调研/digests-文摘/ 页）

文件名 kebab-case 英文：`YYYY-MM-DD-<short-slug>.md`（批量 digest）或 `<event-slug>.md`（单篇）

```yaml
---
type: source
title: "文章/视频/推文标题"
slug: summary-<kebab>
source_file: URL（或 raw/articles/<archived>.md）
author: "作者"
date_published: YYYY-MM-DD
date_ingested: YYYY-MM-DD
key_claims: [核心论点1, 核心论点2, 核心论点3]
related: [[entity1]], [[concept1]], [[comparison1]]
confidence: high | medium | low
tags: [#ai/..., #business/..., etc]
---

## 要点
## 关键洞察
## 数据/引用
## 与已有知识的关联
```

**9.2 · Entities 建/更新**（每个人物/公司/产品/事件）

写到 `knowledge-知识/{people-人物|orgs-组织|products-产品|baobao-我的项目|events-事件}/<kebab-slug>.md`。已存在则 **更新**（加新 source 引用 + 加新 related + 更新"近期动态"）；不存在则**建新**。

```yaml
---
type: entity
entity_type: person | company | product | org | event
title: "名字"
aliases: [别名1, 别名2]
sources: [[source-page]]
related: [[link1]], [[link2]]
confidence: high | medium | low
tags: [...]
---
## 身份 / ## 背景 / ## 代表作 / ## 近期动态 / ## 对 baobao 的启示 / ## 相关
```

**9.3 · Concepts 建/更新**（每个新方法论/框架/概念）

写到 `knowledge-知识/concepts-概念/<kebab-slug>.md`。要点：**必须映射到 baobao 至少 2 个项目**。

**9.4 · Comparisons**（跨主题聚类时必做）

如果本次 digest 产出了"X vs Y" 或 "X vs Y vs Z" 对比洞察，写到 `research-调研/comparisons-对比/<x-vs-y>.md`。

**9.5 · Syntheses**（跨日叙事必做）

如果本次 digest 产出了跨多个 source 的统一叙事（如"5 日叙事线" / "N 次独立验证时间线"），写到 `research-调研/syntheses-综合/<slug>.md`。

**9.6 · 更新 meta 文件**

- `index.md`：把新建/更新的页面加到对应分类表
- `log.md`：追加 `## [YYYY-MM-DD] ingest | <digest 主题>` + 触及页面统计
- `0-start-here-入口/hot.md`：更新 Current Focus + Recent Operations（append，不覆盖）

**9.7 · Lint（5 轮兜底）**

```bash
# 1. 别名一致性
grep -rhoE '\[\[[^]]+\]\]' wiki/ | sed 's/\[\[//; s/|.*\]\]//; s/\]\]//' | sort -u > /tmp/refs.txt
find wiki -name "*.md" -exec basename {} .md \; | sort -u > /tmp/pages.txt
comm -23 /tmp/refs.txt /tmp/pages.txt > /tmp/broken.txt

# 2. 批量修别名（常见别名不一致）
# sed -i '' -e 's/\[\[alias\]\]/[[canonical]]/g' wiki/**/*.md

# 3. 目标：解析率 ≥ 40%（剩余 60% 允许为"待建占位"，Karpathy pattern 接受）
```

**9.8 · git commit**

```bash
cd /Users/baobao/projects/llm-wiki
git add .
git commit -m "ingest: <YYYY-MM-DD> daily-digest · N sources / M entities / K concepts

<1 句话核心叙事>

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### 🚫 Step 9 失败的降级路径

| 情况 | 处理 |
|---|---|
| `llm-wiki/` 不存在 | 跳过 Step 9，但**必须在报告末尾明确警告**"llm-wiki 未初始化，digest 只进 .memos 不进 wiki。违反 Karpathy dogfood 原则，建议先建 wiki" |
| CLAUDE.md 读取失败 | STOP Step 9，不瞎写 |
| Sub-agent 写入冲突 | 串行执行 9.1~9.6，避免并行 |
| git 未初始化 | 提醒用户 `cd llm-wiki && git init`，但 9.1~9.6 继续执行 |
| 规模过大（>50 新页一次 ingest）| 拆成 2+ 并行 sub-agent（参考 2026-04-21 补齐工程的 Agent E/F 分工） |

---

### Step 9 的"反懒惰"验证

每次 digest 收尾时，AI 必须自问 + 自答：

1. ❓ 是否建了 `research-调研/digests-文摘/` 新页？→ 数量必须 ≥ URL 数的一半
2. ❓ 是否建了 `knowledge-知识/{people-人物|orgs-组织|products-产品|baobao-我的项目|events-事件}/` 新页？→ 每个主要人物/产品都有（digest 报告里提到 > 3 次的就应该建）
3. ❓ 是否建了 `knowledge-知识/concepts-概念/` 新页？→ 每个新方法论都有
4. ❓ 是否更新了 `index.md` + `log.md` + `hot.md`？
5. ❓ 是否 git commit？

**5 条全 ✅ 才算 Step 9 完成。任何一条 ❌ 要么补齐要么显式标注"已知未做 + 原因"。**

---

## 输出格式

```markdown
# 信息消化报告 — YYYY-MM-DD

## Sprint Contract ✅/❌
(逐项打勾)

## 概览
- N篇文章 | M个平台 | K个主题
- 竞品动态: X篇 | 学习方向: Y篇 | 生态信号: Z篇

## 主题一: [主题名]
### 文章列表
### 评论精华
### 7维分析
### 行动建议

## 主题二: [主题名]
...

## 承上启下叙事线
(叙事地图)

## 今日最有价值的3个洞察
1. ...
2. ...
3. ...

## 已存入MA的记忆
- [ID] 内容摘要

## 下一步选项
1. ...
2. ...
```

---

## Hermes Evolution 规则

### 进化数据文件
`~/.memos/daily-digest-evolution.md`

### 运行时加载（Step 0，在 Sprint Contract 之前）
用 Read 工具读取 `~/.memos/daily-digest-evolution.md`，参考:
- `平台工具链` 表 → 选择正确的抓取工具
- `用户偏好权重` 表 → 调整分析维度深度
- `运行历史` → 避免重复过去的错误

### 进化写入（Step 8，显式执行）
运行结束时，用 Edit 工具追加到 evolution 文件。只写实际数据，不写估算。

### 用户反馈处理
- 用户说"这个分析很好" → 用 Edit 工具在 evolution 文件中提高对应维度权重
- 用户说"这个没用" → 降低对应文章类型/维度权重
- 抓取失败 → 更新平台工具链表

---

## Harness 质量门禁

| Gate | 检查项 | 通过条件 |
|------|--------|----------|
| G1 抓取 | 标题+正文 | > 100字 |
| G2 分类 | 分类标签 | 必须属于5类之一 |
| G3 分析 | 深度分析 | 引用至少1条MA记忆 |
| G4 行动 | 行动建议 | 有[做什么/预期/风险/关联文件] |
| G5 评论 | X平台 | 必须尝试提取Community Notes |
| G6 进化 | evolution文件 | 运行结束必须更新 |
| **G7 Wiki ingest** | `research-调研/digests-文摘/` + `knowledge-知识/{people-人物|orgs-组织|products-产品|baobao-我的项目|events-事件}/` + `knowledge-知识/concepts-概念/` 新页 | **至少 sources = N/2 · entities = 主要人物全建 · log.md 追加条目 · git commit** |

### 模型路由（省token）
```
抓取/分类/去重       → 子Agent（Sonnet，便宜快）
深度7维分析          → 主Agent（Opus，准确）
evolution更新        → 直接写文件（0 token）
Step 9 wiki ingest   → 并行 sub-agent 分工（sources/entities 各一组，主 agent 写 comparisons+syntheses）
```

### Step 9 的 sub-agent 分工模板（规模 ≥ 10 URL 时用）

```
Agent A: sources 建页（每 URL → 1 摘要页）
Agent B: entities 批 1（10 个人物/公司）
Agent C: entities 批 2（10 个产品/组织/事件）
Agent D: concepts（10 个方法论/框架）
主 Agent: comparisons + syntheses + 收口（index/log/hot/git commit）
```

参考 2026-04-21 大补工程（14 页→86 md · 6.1× 扩张 · git SHA `62bcfa3`）作为 Step 9 成功案例。
