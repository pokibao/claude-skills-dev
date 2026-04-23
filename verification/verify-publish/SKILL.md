---
name: verify-publish
description: 验证社媒发布结果。Use after publishing to Xiaohongshu or Instagram, when checking if posts went live correctly, when user says "验证发布/检查帖子/发布成功了吗".
triggers:
  - /verify-publish
  - 验证发布
  - 检查帖子
  - 发布成功了吗
  - 帖子发了吗
  - check post
allowed-tools: Bash(python3 *), Bash(curl *), Read, Glob, Grep
---

# verify-publish: 社媒发布验证

## 用途

发布到小红书或 Instagram 后，自动验证帖子是否成功上线。检查帖子可访问性、图片数量、文案内容、标签完整性。

## 支持平台

| 平台 | 验证方式 | 脚本 |
|------|----------|------|
| **小红书** | xiaohongshu-mcp API (localhost:18060) | `verify_xhs.py` |
| **Instagram** | curl 公开页面 + og:meta 解析 | `verify_ig.py` |

## 快速使用

### 小红书验证

```bash
# 通过笔记 ID
/opt/homebrew/bin/python3 ~/.claude/skills/verify-publish/scripts/verify_xhs.py 6801a2b3c4d5e6f7

# 通过笔记 URL
/opt/homebrew/bin/python3 ~/.claude/skills/verify-publish/scripts/verify_xhs.py https://www.xiaohongshu.com/explore/6801a2b3c4d5e6f7

# 带关键词匹配（验证标题/正文包含特定词）
/opt/homebrew/bin/python3 ~/.claude/skills/verify-publish/scripts/verify_xhs.py 6801a2b3c4d5e6f7 --keywords "极简,法式"

# 验证最近发布的所有笔记
/opt/homebrew/bin/python3 ~/.claude/skills/verify-publish/scripts/verify_xhs.py --recent

# 验证最近 N 条
/opt/homebrew/bin/python3 ~/.claude/skills/verify-publish/scripts/verify_xhs.py --recent --count 5
```

### Instagram 验证

```bash
# 通过帖子 URL
/opt/homebrew/bin/python3 ~/.claude/skills/verify-publish/scripts/verify_ig.py https://www.instagram.com/p/ABC123/

# 通过用户名（检查主页可访问性）
/opt/homebrew/bin/python3 ~/.claude/skills/verify-publish/scripts/verify_ig.py --username necessaryananke

# 带关键词
/opt/homebrew/bin/python3 ~/.claude/skills/verify-publish/scripts/verify_ig.py https://www.instagram.com/p/ABC123/ --keywords "NA,26SS"
```

## 验证清单（5 项检查）

| # | 检查项 | 小红书 | Instagram |
|---|--------|--------|-----------|
| 1 | **帖子可访问** | MCP API 返回数据 / HTTP 200 | curl 返回 200 |
| 2 | **图片数量** | API 返回 image_count > 0 | og:image 存在 |
| 3 | **标题/文案** | title + desc 非空 | og:description 非空 |
| 4 | **关键词匹配** | 标题或正文包含指定词 | description 包含指定词 |
| 5 | **标签/Hashtag** | tags 数组非空 | 描述中 # 标签存在 |

## 输出格式

JSON 结构化输出 + 人类可读摘要：

```json
{
  "platform": "xiaohongshu",
  "note_id": "6801a2b3c4d5e6f7",
  "status": "published",
  "checks": {
    "accessible": true,
    "has_images": true,
    "image_count": 5,
    "has_title": true,
    "has_content": true,
    "keywords_matched": ["极简", "法式"],
    "keywords_missing": [],
    "has_tags": true,
    "tag_count": 6
  },
  "details": {
    "title": "解构 | 命运的轮廓",
    "url": "https://www.xiaohongshu.com/explore/6801a2b3c4d5e6f7"
  },
  "summary": "PASS - 5/5 checks passed"
}
```

## 平台特定说明

### 小红书 (xiaohongshu-mcp)

**验证路径优先级**：
1. **MCP /api/v1/feeds/detail** (POST) - 获取笔记详情（需要 feed_id + xsec_token）
2. **MCP /api/v1/user/me** (GET) - 获取我的笔记列表，按 ID 匹配
3. **MCP /api/v1/feeds/search** (POST) - 按标题关键词搜索匹配

**MCP 依赖**：
- 服务地址：`http://localhost:18060`
- 健康检查：`curl http://localhost:18060/health`
- 需要已登录状态：`curl http://localhost:18060/api/v1/login/status`

### Instagram

**验证路径**：
1. **curl 公开页面** - 检查 HTTP 状态码 + og:meta 标签
2. **CDP 浏览器截图**（需 Chrome CDP 9222）- 完整页面验证

**curl 的局限**：
- Instagram 对未登录用户可能返回登录墙
- og:meta 信息可能不完整（尤其是私密账号）
- 若 curl 不够用，脚本会提示使用 Pydoll/CDP 浏览器验证

## Gotchas（常见陷阱）

| 陷阱 | 说明 | 应对 |
|------|------|------|
| **发布后延迟** | 图片处理/CDN 同步需要时间 | 发布后等 30 秒再验证 |
| **内容审核** | 小红书有内容审核机制，新帖可能暂时不可见 | 等 1-5 分钟后重试 |
| **频率限制** | MCP API 有频率限制 | 批量验证间隔 2 秒 |
| **登录过期** | MCP cookie 过期导致 API 401 | 先检查登录状态 |
| **IG 登录墙** | Instagram 未登录可能无法看到帖子 | 使用 CDP 浏览器 |
| **xsec_token** | feeds/detail 需要 xsec_token | 先从 user/me 获取 |

## Fallback: 手动验证清单

如果 API 不可用，按以下顺序手动检查：

1. 打开帖子链接，确认页面加载正常
2. 数图片数量，与预期一致
3. 检查标题是否完整显示
4. 检查正文内容，无乱码/截断
5. 检查标签数量和内容
6. 检查评论区是否开放
7. 检查帖子时间戳是否正确

## 相关 Skill

- `/xhs-publish` - 小红书发布
- `/ig-story` - Instagram Story 发布
- `/ig-copy` - Instagram 文案生成
- `/verify-gen` - AI 生图质量验证（发布前用）
- `/verify-pipeline` - 批量流水线验证
