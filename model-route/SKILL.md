---
name: model-route
description: 模型选择路由。涉及"用什么模型""Opus 还是 Sonnet""模型选择""Claude/GPT/Gemini 选哪个"时使用。
---

# /model-route - 模型路由
>
> **重要**：模型信息可能过时，配置前必须验证（Hook 会自动提醒）

---

## Claude 内部模型路由

### 最新模型 ID（需验证）

| 模型 | API ID | 用途 |
|------|--------|------|
| **Sonnet 4.6** | `claude-sonnet-4-6-*` | 常规开发、复杂 Agent |
| **Haiku 4.5** | `claude-haiku-4-5-*` | 快速任务、格式转换 |
| **Opus 4.6** | `claude-opus-4-6-*` | Vibe coding、架构、关键决策 |

### 强制 Opus 场景

| 场景 | 触发条件 |
|------|---------|
| 架构设计 | backend-architect, system-architect |
| 代码审查 | code-reviewer（生产代码） |
| 复杂规划 | Plan agent + 任务 >5 步 |
| 难题攻坚 | "难"、"复杂"、"搞不定" |
| 关键决策 | 数据库迁移、API 设计 |
| 安全相关 | 认证、授权、加密 |
| **Vibe 理解** | 模糊意图、品牌调性、"感觉" |

### 触发词（自动升级 Opus）

"用 Opus"、"要准确"、"不能出错"、"复杂"、"难"、"架构"、"安全"、"生产环境"、"vibe"、"感觉"、"风格"

---

## 外部 AI 路由

### 快速决策表

| 任务特征 | 推荐工具 | 原因 |
|---------|---------|------|
| 模糊意图/品牌调性 | Claude Opus | 理解 vibe，深度推理 |
| 明确代码执行 | Codex | 稳定生产级，免费 |
| 大文件/视频理解 | Gemini | 1M 窗口 + 原生多模态，免费 |
| **中文文案/小红书** | **Kimi K2.5** | **懂中文互联网生态，成本低** |
| **图片分析/OCR** | **Kimi K2.5** | **OCR 92.3% 全场最强** |
| **批量并行任务** | **Kimi K2.5** | **Agent Swarm 100并行** |
| 英文文案(IG/Shopify) | Claude Opus | 英文地道，品牌把控准 |
| 复杂任务 | 多工具联合 | 各取所长 |

### Kimi K2.5 专属路由（新增）

| 场景 | 触发条件 |
|------|---------|
| 小红书文案 | "小红书"、"种草"、"文案"、"笔记" |
| 竞品分析 | "竞品"、"分析XX品牌"、批量扫描 |
| 图片理解 | "看图"、"OCR"、"识别"、产品图分析 |
| 批量任务 | "批量"、"100个"、"并行"、Agent Swarm |

### 调用命令

```bash
# Kimi K2.5（中文文案、视觉、批量任务）
uv run ~/.claude/skills/kimi/scripts/kimi.py "<prompt>" [workdir]

# Gemini（第二视角、图片、长上下文）
uv run ~/.claude/skills/gemini/scripts/gemini.py "<prompt>" [workdir]

# Codex（明确任务执行）
uv run ~/.claude/skills/codex/scripts/codex.py "<task>" [workdir]
```

---

## 风险感知路由（灵感: OpenAEON CouplingVector）

根据当前状态动态调整策略，不要一成不变：

### 三种模式

| 模式 | 触发条件 | 策略 |
|------|---------|------|
| **Conservative** | 生产环境/安全/数据操作/连续失败 | Opus + high thinking，禁止冒险 |
| **Balanced** | 正常开发任务 | Sonnet/Opus 按复杂度选，中等 thinking |
| **Aggressive** | 调研/探索/头脑风暴/原型 | Sonnet + low thinking，追求速度和广度 |

### 自动升级规则

```
连续失败 3 次 → Conservative（升级模型+思考深度）
混沌状态（目标不清）→ 先暂停，search_rules 查历史
探索完成 → 回退到 Balanced
```

### 子 Agent 模型选择

| 子任务类型 | 推荐模型 | thinking |
|-----------|---------|----------|
| 代码搜索/grep | Sonnet/Haiku | low |
| 深度分析/架构 | Opus | high |
| 并行调研 | Sonnet × N | medium |
| 品牌审核 | Opus | high |

## 回退规则

| 场景 | 回退方案 |
|------|---------|
| Claude 不稳定 | 重启会话，精简上下文 |
| Codex 不懂意图 | Claude 先翻译成明确 spec |
| Gemini 翻车 | 拆小上下文分批处理 |
| Kimi 文案质量不行 | 回退到 Opus 写文案 |
| Kimi Agent Swarm 超时 | 降级为单 Agent 模式 |
| 外部 AI 全挂 | 回退到 Claude 单独处理 |
