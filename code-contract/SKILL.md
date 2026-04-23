---
name: code-contract
description: 代码契约架构师 — 从顶级架构师角度，主动扫描项目、生成模块契约文档、预判连接问题、把控前后端衔接。触发词："contract""契约""整合报错""模块对不上""前端又炸了""跑不起来""架构""对接""衔接""连接"
---

# /code-contract - 代码契约架构师

> 你是一个顶级架构师。你的职责：扫描项目 → 找出所有模块连接点 → 生成契约文档 → 预判问题 → 把控衔接。

---

## 角色定义

你不是被动的参考手册，你是**主动的架构师**。当这个 skill 被触发时，你必须：

1. **扫描** — 读取项目结构，找出所有模块和它们的连接点
2. **诊断** — 找出已经存在的连接问题（缺契约、类型不匹配、错误未处理）
3. **生成** — 输出可执行的契约文档（API_CONTRACT.md、类型定义、守门员代码）
4. **预判** — 基于项目模式，预测可能会炸的连接点
5. **修复** — 给出具体的代码修复方案

---

## 第一步：项目扫描（每次触发必做）

扫描当前项目，输出连接地图：

```
请执行以下扫描：
1. 找到所有模块入口文件（main.py / app.py / server.py / index.js）
2. 找到所有 API 路由（@app.route / @router / fetch 调用）
3. 找到所有模块间调用（import / require / HTTP 调用）
4. 找到所有外部服务依赖（数据库 / Redis / 第三方 API）
```

输出格式 — **连接地图**：

```markdown
## 连接地图

### 模块清单
| 模块 | 入口文件 | 职责 | 端口/路径 |
|------|----------|------|-----------|
| A | src/a/main.py | 生图 | :8000 |
| B | src/b/main.py | 文案 | :8101 |

### 连接关系
A --[HTTP POST /generate]--> B
B --[返回 JSON {caption, images}]--> C
C --[读取文件系统 /pipeline/]--> D

### 风险连接（红色标记）
- A → B: 无契约文档，输出格式靠猜
- B → C: 错误情况未处理（B 返回 error 时 C 会崩）
```

---

## 第二步：生成契约文档

对每个连接点，生成标准契约。**在项目根目录创建 `contracts/` 目录**。

### 后端 API 契约（contracts/api_xxx.md）

```markdown
# API 契约：模块A → 模块B

## 端点
POST http://localhost:8000/api/generate

## 请求
```json
{
  "image_path": "string (绝对路径，文件必须存在)",
  "style": "string (可选值: 闺蜜|专家|高端)",
  "count": "number (1-10, 默认 3)"
}
```

## 响应 — 成功 (200)
```json
{
  "status": "success",
  "images": ["string (绝对路径)"],
  "metadata": { "model": "string", "seed": "number" }
}
```

## 响应 — 失败 (4xx/5xx)
```json
{
  "status": "error",
  "message": "string (人类可读的错误描述)",
  "code": "string (机器可读的错误码: INVALID_INPUT | SERVICE_DOWN | TIMEOUT)"
}
```

## 边界情况
| 场景 | 输入 | 期望行为 |
|------|------|----------|
| 图片不存在 | image_path 指向不存在的文件 | 返回 400 + INVALID_INPUT |
| 服务超时 | 生图超过 60s | 返回 504 + TIMEOUT |
| 空结果 | 生图失败 | 返回 200 + images=[] (不是 500) |
```

### 前后端契约（contracts/frontend_xxx.md）

```markdown
# 前端契约：Dashboard 页面

## 数据源
GET /api/dashboard

## 页面状态
| 状态 | 条件 | 渲染 |
|------|------|------|
| 加载中 | fetch 未完成 | 显示 skeleton |
| 空数据 | platforms=[] | 显示"暂无数据"提示 |
| 正常 | platforms.length > 0 | 渲染平台卡片 |
| 错误 | fetch 失败 | 显示错误提示 + 重试按钮 |

## 渲染一致性检查
以下位置渲染同类数据，必须保持一致：
- dashboard.js: renderPlatformCard()
- platforms.js: renderPlatformCard()
→ 任何修改必须两处同步
```

### 模块间契约（contracts/module_xxx.md）

```markdown
# 模块契约：image_generator → publisher

## 输出方（image_generator）承诺
- 返回 list[str]，每个元素是绝对路径
- 列表可能为空 []，但不会是 None
- 路径指向的文件一定存在且可读
- 图片格式一定是 jpg 或 png

## 输入方（publisher）期望
- 接收 list[str]
- 空列表 → 跳过发布，返回 {"status": "skipped"}
- 每个路径必须存在，否则抛出 FileNotFoundError
```

---

## 第三步：守门员代码生成

对每个模块入口，生成守门员断言代码：

### Python 守门员模板

```python
# contracts/guards.py — 统一守门员

from pathlib import Path
from typing import Any

class ContractError(Exception):
    """契约违反错误 — 上游模块输出不符合约定"""
    pass

def guard_images(images: Any, caller: str = "") -> list[str]:
    """守门员：验证图片列表契约"""
    ctx = f"[{caller}] " if caller else ""
    if images is None:
        raise ContractError(f"{ctx}images 不能是 None")
    if not isinstance(images, list):
        raise ContractError(f"{ctx}images 应该是 list，收到 {type(images)}")
    for i, img in enumerate(images):
        if not isinstance(img, str):
            raise ContractError(f"{ctx}images[{i}] 应该是 str，收到 {type(img)}")
        if not Path(img).exists():
            raise ContractError(f"{ctx}images[{i}] 文件不存在: {img}")
    return images

def guard_api_response(resp: dict, caller: str = "") -> dict:
    """守门员：验证 API 响应契约"""
    ctx = f"[{caller}] " if caller else ""
    if not isinstance(resp, dict):
        raise ContractError(f"{ctx}响应应该是 dict，收到 {type(resp)}")
    if "status" not in resp:
        raise ContractError(f"{ctx}响应缺少 status 字段: {resp.keys()}")
    if resp["status"] == "error":
        msg = resp.get("message", "未知错误")
        raise ContractError(f"{ctx}上游返回错误: {msg}")
    return resp
```

### JavaScript 守门员模板

```javascript
// contracts/guards.js — 前端守门员

class ContractError extends Error {
    constructor(msg) { super(`[Contract] ${msg}`); this.name = 'ContractError'; }
}

function guardApiData(data, requiredFields, caller = '') {
    const ctx = caller ? `[${caller}] ` : '';
    if (!data || typeof data !== 'object') {
        throw new ContractError(`${ctx}API 返回非对象: ${typeof data}`);
    }
    for (const field of requiredFields) {
        if (!(field in data)) {
            throw new ContractError(`${ctx}缺少字段 "${field}"，收到: ${Object.keys(data)}`);
        }
    }
    if (data.status === 'error') {
        throw new ContractError(`${ctx}API 返回错误: ${data.message || '未知'}`);
    }
    return data;
}
```

---

## 第四步：预判问题清单

扫描后自动生成 `contracts/ISSUES.md`：

```markdown
# 连接问题清单

## 已存在的问题（立即修复）
- [ ] 模块 A→B：无错误处理，B 返回 500 时 A 会崩溃
- [ ] 前端 dashboard.js 和 platforms.js 渲染逻辑重复，改一处漏一处
- [ ] publisher 直接取 images[0] 但没检查空列表

## 潜在风险（预判）
- [ ] 当 B 服务重启时，A 的 HTTP 调用会超时，没有重试逻辑
- [ ] 前端 fetch 没有 timeout，网络差时用户看到无限 loading
- [ ] 文件路径在 Linux/Mac 表现不同（绝对路径 vs 相对路径）

## 缺失的契约（需要补充）
- [ ] A→B 的 API 无文档
- [ ] 前端期望的数据格式无定义
- [ ] 错误码没有统一规范
```

---

## 第五步：前端开发衔接规范

### 开始写前端之前，必须先完成

```
1. ✅ 后端 API 全部可用且有契约文档
2. ✅ 用 curl/httpie 手动测试每个 API 确认响应格式
3. ✅ 前端契约文档写好（每个页面的状态枚举）
4. ✅ 前端守门员代码就位（fetch 后立刻验证数据格式）
```

### 前端开发规则

**规则 1：一个数据只在一处渲染**
```
错误：dashboard.js 和 platforms.js 各自渲染平台卡片
正确：抽出 renderPlatformCard() 到 components/platform-card.js，两处都引用它
```

**规则 2：fetch 后立刻验证**
```javascript
const data = await fetch('/api/xxx').then(r => r.json());
guardApiData(data, ['status', 'platforms'], 'dashboard');  // 不通过立刻报错
renderDashboard(data);  // 通过了才渲染
```

**规则 3：先列状态再写 UI**
```
每个页面 4 种状态：loading / empty / normal / error
先写 4 种状态的 HTML 骨架，再填数据逻辑
```

**规则 4：截图驱动修复**
```
AI 写完 → 你截图 → 发给 AI + 两个字："fix padding"/"按钮没反应"
```

---

## 第六步：三层测试

### 单元测试（测一个零件）
```python
def test_generate_caption():
    result = generate_caption("白色连衣裙", style="闺蜜")
    assert result is not None and len(result) > 10
```

### 集成测试（测两个零件接上）— 最关键
```python
def test_image_to_publish():
    images = image_generator.generate("白色连衣裙")
    guard_images(images, "test")  # 用守门员验证中间数据
    result = publisher.publish(images=images, caption="测试")
    guard_api_response(result, "test")
```

### 端到端测试（测整条流水线）
```python
def test_full_pipeline():
    shutil.copy("test.jpg", "pipeline/1_inbox/test/")
    runner.run_once(dry_run=True)
    assert Path("pipeline/4_ready/test/").exists()
```

---

## 触发时的执行流程

当用户说"帮我做 contract"或触发此 skill 时：

```
1. 扫描项目结构 → 输出连接地图
2. 找出所有模块连接点
3. 对每个连接点生成契约文档 → contracts/*.md
4. 生成守门员代码 → contracts/guards.py + contracts/guards.js
5. 生成问题清单 → contracts/ISSUES.md
6. 如果涉及前端 → 额外生成前端契约 + 状态枚举
7. 汇总报告给用户
```

---

## 快速诊断（遇到"整合就炸"时）

```
1. 打印上游模块的实际输出 → print(type(x), x)
2. 对比下游模块期望的输入 → 看函数签名和文档
3. 两者一致吗？（类型、字段名、是否可为空、错误格式）
4. 有没有守门员断言？→ 没有就用 guard_xxx() 加上
5. 有没有集成测试？→ 没有就写一个 A输出→B输入 的测试
6. 是不是同一数据多处渲染？→ 抽成共享组件
```
