---
name: memory-audit
description: 记忆审计与进化 — 空闲时自动审计记忆、检测矛盾、修剪过时知识。灵感来源于 OpenAEON Dreaming Mode + Logic Refinement。触发词："审计记忆""记忆清理""memory audit""dreaming""记忆矛盾""记忆冲突"
---

# /memory-audit — 记忆审计与进化系统

> 灵感: OpenAEON Dreaming Mode (server-evolution.ts:940-1079) + Logic Refinement (logic-refinement.ts)
> 核心: 定期审计记忆 → 发现矛盾 → 修剪过时 → 合并重复 → 提炼公理

---

## 四种操作模式

用户可指定模式，默认 `full`（全部执行）。

### 1. `audit` — 全面扫描

```
步骤:
1. ToolSearch("memory-anchor") 加载工具
2. get_context() 看整体状态
3. search_rules(query="*", min_score=0.1, limit=20) 拉最近记忆
4. 检查每条记忆:
   - 是否仍然准确？（命中 file-path/function → grep 验证）
   - 是否有矛盾对？（同主题不同结论）
   - 最后一次被召回是什么时候？
5. 输出审计报告
```

### 2. `prune` — 修剪过时记忆 (180 天规则)

```
规则:
- 超过 180 天未被召回 + confidence < 0.8 → 候选修剪
- 包含已删除的文件路径/函数名 → 候选修剪
- 标记为 "需验证" 但从未验证 → 候选修剪
- 修剪方式: report_outcome(memory_id, outcome="outdated", reason="...")

⚠️ 180 天阈值是硬规则（baobao 指定）:
   - 不用 30 天（太短，很多项目如金提黄签合同周期就要 60 天）
   - 项目记忆可能休眠很久但仍有价值
   - 只有同时满足"180天未召回 + 低置信度"才修剪
```

### 3. `conflict` — 矛盾仲裁

```
检测方法:
1. 对每个主题领域搜索记忆 (search_rules)
2. 找到相似度 > 0.7 但结论不同的记忆对
3. 对每对矛盾，判断:
   - merge: 两条可以合并成更完整的一条
   - prefer_latest: 新的覆盖旧的
   - keep_both: 确实是不同场景，都保留
   - flag: 无法自动判断，标记给用户
4. 执行仲裁:
   - merge → add_rule(合并内容) + report_outcome(旧的, "outdated")
   - prefer_latest → report_outcome(旧的, "outdated")
   - keep_both → 不动
   - flag → 输出给用户看

矛盾类型:
- 技术矛盾: "用 A 框架" vs "用 B 框架"（可能是不同项目，keep_both）
- 事实矛盾: "端口是 8080" vs "端口是 3000"（prefer_latest）
- 决策矛盾: "不做 X" vs "已经做了 X"（prefer_latest）
- 状态矛盾: "项目进行中" vs "项目已完成"（prefer_latest）
```

### 4. `crystallize` — 提炼公理

```
从多条零散记忆中提炼高阶规则:
1. 找到 3+ 条描述同一模式的记忆
2. 提炼为一条高置信度公理
3. add_rule(公理, confidence=0.95, category="routine")
4. 原始记忆标记 superseded

例子:
- 3 条 "Gemini 晚高峰 503" → 提炼 "Gemini API 8PM CST 后不可靠，batch 任务排凌晨"
- 5 条 "某工具成功" → 提炼 "[SUCCESS PATTERN] 工具+配置+拓扑组合"
```

---

## 执行协议

### 手动触发
```
用户: /memory-audit
用户: /memory-audit prune
用户: /memory-audit conflict
```

### Cron 自动触发（建议每周日凌晨）
```
schedule: "0 3 * * 0"    # 每周日凌晨 3:00
prompt: "/memory-audit full"
```

### 输出格式

```markdown
## 记忆审计报告 — {date}

### 扫描统计
- 总记忆数: N
- 活跃(180天内被召回): X
- 休眠(180天未召回): Y
- 矛盾对: Z

### 修剪候选 (需确认)
| ID | 内容摘要 | 最后召回 | 原因 |
|----|---------|---------|------|
| ... | ... | ... | 180天+低置信 |

### 矛盾仲裁
| 记忆A | 记忆B | 类型 | 建议动作 |
|-------|-------|------|---------|
| ... | ... | 事实矛盾 | prefer_latest |

### 提炼的公理
| 来源记忆数 | 公理内容 |
|-----------|---------|
| 3 | "Gemini 8PM后不可靠" |

### 建议下一步
- [ ] 确认修剪候选
- [ ] 审核矛盾仲裁结果
- [ ] 检查提炼的公理是否合理
```

---

## 搜索策略（多轮保证覆盖）

审计时必须多角度搜索，不能只搜一次：

```
Round 1: search_rules(query="架构 决策 技术", limit=20)
Round 2: search_rules(query="bug 修复 错误", limit=20)
Round 3: search_rules(query="项目 进度 状态", limit=20)
Round 4: search_rules(query="配置 端口 环境", limit=20)
Round 5: search_rules(query="品牌 NA 设计", limit=20)
Round 6: search_rules(query="成功 失败 教训", limit=20)
去重后合并为完整记忆列表
```

---

## 安全规则

1. **不自动删除** — 只标记 `outdated`，不物理删除
2. **矛盾仲裁结果展示给用户** — merge/prefer_latest 前先列出让用户确认
3. **L0 身份层绝对不碰** — 身份记忆走 propose_change 审批流程
4. **180 天硬阈值** — 不允许降低，宁可多留不误删
