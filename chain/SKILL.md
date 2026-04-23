---
name: chain
description: "Multi-step workflow tracker — create, advance, block, resume, complete chains across sessions"
triggers:
  - "/chain"
  - "链路"
  - "工作流"
---

# /chain — 多步骤工作流追踪

跨会话持久化的工作流链路管理。解决"小任务能跑，大链路跑不通"的核心痛点。

## 用法

- `/chain new "批量发小红书" --steps "选图,写文案,审核,发布,验证"` — 创建链路
- `/chain new "lookbook生成" --template lookbook_gen` — 从模板创建
- `/chain status` — 查看所有活跃链路
- `/chain advance xhs_batch "30/50 完成"` — 推进步骤
- `/chain block xhs_batch "cookie expired"` — 标记阻塞
- `/chain resume xhs_batch` — 从断点恢复
- `/chain done xhs_batch` — 完成归档
- `/chain list` — 列出所有链路（含已完成）

## 执行步骤

### `/chain new`

```bash
python3 ~/.claude/skills/chain/scripts/chain_manager.py new \
  --name "批量发小红书" \
  --steps "选图,写文案,审核,发布,验证"
```

或从模板:
```bash
python3 ~/.claude/skills/chain/scripts/chain_manager.py new \
  --name "批量发小红书" \
  --template xhs_publish
```

### `/chain status`

```bash
python3 ~/.claude/skills/chain/scripts/chain_manager.py status
```

输出格式:
```
## Active Chains

1. [批量发小红书] Step 3/5: 审核
   Updated: 2h ago | Created: 2026-03-18
   History: 选图 ✓ → 写文案 ✓ → 审核 ● → 发布 ○ → 验证 ○

2. [lookbook生成] Step 1/4: 选款 ⛔ BLOCKED
   Blocker: 等待用户选款确认
   Updated: 1d ago | Created: 2026-03-17
```

### `/chain advance`

```bash
python3 ~/.claude/skills/chain/scripts/chain_manager.py advance \
  --id xhs_batch \
  --note "30/50 完成"
```

### `/chain block`

```bash
python3 ~/.claude/skills/chain/scripts/chain_manager.py block \
  --id xhs_batch \
  --reason "cookie expired"
```

### `/chain resume`

```bash
python3 ~/.claude/skills/chain/scripts/chain_manager.py resume --id xhs_batch
```

输出当前状态 + 下一步提示，方便 AI 在新会话中续接。

### `/chain done`

```bash
python3 ~/.claude/skills/chain/scripts/chain_manager.py done --id xhs_batch
```

归档到 `pulse/data/chains/archive/`。

## Chain JSON Schema

```json
{
  "chain_id": "xhs_batch_20260318_143000",
  "name": "批量发小红书",
  "template": "xhs_publish",
  "steps": ["选图", "写文案", "审核", "发布", "验证"],
  "current_step": 2,
  "status": "in_progress",
  "blocker": null,
  "created_at": "2026-03-18T14:30:00",
  "updated_at": "2026-03-18T15:00:00",
  "history": [
    {"step": 0, "action": "advance", "note": "选了30张图", "at": "2026-03-18T14:35:00"},
    {"step": 1, "action": "advance", "note": "30/50 文案写完", "at": "2026-03-18T14:50:00"}
  ]
}
```

## 预置模板

| Template ID | Steps |
|-------------|-------|
| `xhs_publish` | 选图 → 写文案 → 品牌审核 → 发布 → 验证 |
| `lookbook_gen` | 选款 → 配模特 → 生图 → 验图 → 排版 |
| `ig_publish` | 选图 → 写IG文案 → 发Story → 发Post → 验证 |
| `trend_research` | 抓秀场 → 分析趋势 → 匹配DNA → 出报告 |

## 数据存储

- 活跃链路: `~/.claude/skills/pulse/data/chains/*.json`
- 归档链路: `~/.claude/skills/pulse/data/chains/archive/*.json`
- 被 session-start.py 和 stop-flush.py 共享读取
