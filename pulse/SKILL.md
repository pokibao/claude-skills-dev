---
name: pulse
description: "Daily ops dashboard — aggregate session data, detect stalls, weekly summary"
triggers:
  - "/pulse"
  - "脉搏"
  - "今日汇总"
  - "停滞检测"
---

# /pulse — Ops Loop 每日脉搏仪表盘

多源聚合所有会话数据，输出结构化运营仪表盘。

## 用法

- `/pulse` — 今日汇总（sessions + commits + skills + delta vs 昨天）
- `/pulse stall` — 停滞检测（in_progress >3天 + 无活跃会话）
- `/pulse week` — 周汇总（喂给 /retro 和 /master）

## 执行步骤

### `/pulse` (默认 — 今日汇总)

1. 运行 aggregate.py 聚合今日数据:
```bash
python3 ~/.claude/skills/pulse/scripts/aggregate.py
```

2. 读取输出的 daily JSON，渲染 markdown dashboard:
```
## Ops Pulse — 2026-03-18

### Sessions
- 总计: 5 sessions | 停止原因: 3 user_request, 2 unknown
- 工作目录: /Users/baobao/projects/xxx (3), /Users/baobao (2)

### Accomplishments
- 3 git commits (fix auth, add pulse skill, update hooks)
- 2 skills used (verify-gen, na-copywriting-rules)
- 12 files changed

### Active Chains
- [批量发小红书] Step 3/5: 审核 — last updated 2h ago
- [lookbook生成] Step 1/4: 选款 — last updated 1d ago

### Delta vs Yesterday
- Sessions: +2 | Commits: +1 | Skills: -1
```

### `/pulse stall` (停滞检测)

1. 运行 stall_detector.py:
```bash
python3 ~/.claude/skills/pulse/scripts/stall_detector.py
```

2. 渲染停滞报告:
```
## Stall Detection — 2026-03-18

### Memory Anchor Checkpoints (in_progress >3d)
- harness-engineering: in_progress since 2026-03-15, no activity 3d
  → Next step: 实施 Sprint 1+2+3 的 schema 迁移和代码改动

### Chains (no update >2d)
- lookbook生成: Step 1/4, last update 2026-03-16
  → Blocker: none recorded

### Recommendation
- Consider `/chain block` or `/chain done` to clean up stale items
```

### `/pulse week` (周汇总)

1. 运行 aggregate.py --week:
```bash
python3 ~/.claude/skills/pulse/scripts/aggregate.py --week
```

2. 渲染周汇总，适合喂给 /retro 或 /master。

## 数据源

| Source | Path | What |
|--------|------|------|
| pending-memories | `~/.claude/pending-memories/flush_*.json` | 会话端口/git/cwd/accomplishments |
| skill-usage.log | `~/.claude/skill-usage.log` | skill 调用历史 |
| skills today | `/tmp/.claude_skills_today` | 当日 skill 使用 |
| git log | `git log --since="today"` | 今日 commits |
| MA checkpoints | `search_checkpoints(task_status=active)` | 活跃断点 |
| chains | `~/.claude/skills/pulse/data/chains/*.json` | 工作流链路 |
| daily aggregated | `~/.claude/skills/pulse/data/daily/YYYY-MM-DD.json` | 聚合后的日数据 |
