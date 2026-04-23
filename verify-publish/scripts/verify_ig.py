#!/usr/bin/env /opt/homebrew/bin/python3
"""
Instagram 发布验证脚本

验证方式（按优先级）：
1. curl 公开页面 — 检查 HTTP 状态码 + og:meta 标签
2. CDP 浏览器 — 完整页面验证（需 Chrome --remote-debugging-port=9222）

注意：Instagram 对未登录请求可能返回登录墙，此时需要 CDP 浏览器验证。

用法：
  verify_ig.py <post_url>                                # 验证单条帖子
  verify_ig.py <post_url> --keywords "NA,26SS"           # 带关键词
  verify_ig.py --username necessaryananke                 # 检查主页
  verify_ig.py --username necessaryananke --keywords "NA" # 主页+关键词
"""

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

# Instagram 请求需要伪装浏览器 User-Agent
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

TIMEOUT = 15  # 秒


# ─────────────────────────────────────────────
# OG Meta Parser
# ─────────────────────────────────────────────

class OGMetaParser(HTMLParser):
    """从 HTML 中提取 Open Graph meta 标签"""

    def __init__(self):
        super().__init__()
        self.og_data = {}
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True

        if tag == "meta":
            attr_dict = dict(attrs)
            # og:* 标签
            prop = attr_dict.get("property") or ""
            if prop.startswith("og:"):
                self.og_data[prop] = attr_dict.get("content", "")
            # name="description" 标签
            name = attr_dict.get("name", "")
            if name == "description":
                self.og_data["meta:description"] = attr_dict.get("content", "")

    def handle_data(self, data):
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False


def parse_og_meta(html: str) -> dict:
    """解析 HTML 中的 OG meta 数据"""
    parser = OGMetaParser()
    try:
        parser.feed(html)
    except Exception:
        pass
    result = dict(parser.og_data)
    if parser.title:
        result["page_title"] = parser.title.strip()
    return result


# ─────────────────────────────────────────────
# 检测登录墙
# ─────────────────────────────────────────────

def is_login_wall(html: str) -> bool:
    """检测 Instagram 是否返回了登录墙"""
    login_indicators = [
        "loginAndSignupPage",
        '"requireLogin":true',
        "Log in to see",
        "log in to Instagram",
        "/accounts/login/",
    ]
    html_lower = html.lower()
    return any(indicator.lower() in html_lower for indicator in login_indicators)


# ─────────────────────────────────────────────
# 提取 hashtags
# ─────────────────────────────────────────────

def extract_hashtags(text: str) -> list[str]:
    """从文本中提取 hashtag"""
    if not text:
        return []
    return re.findall(r"#(\w+)", text)


# ─────────────────────────────────────────────
# 验证帖子 URL
# ─────────────────────────────────────────────

def verify_post(url: str, keywords: list[str] | None = None) -> dict:
    """
    通过 curl 验证 Instagram 帖子

    Returns:
        验证结果 dict
    """
    result = {
        "platform": "instagram",
        "url": url,
        "status": "unknown",
        "checks": {
            "accessible": False,
            "has_images": False,
            "image_count": 0,
            "has_title": False,
            "has_content": False,
            "keywords_matched": [],
            "keywords_missing": [],
            "has_tags": False,
            "tag_count": 0,
        },
        "details": {},
        "needs_browser": False,
        "summary": "",
    }

    # 请求页面
    try:
        resp = httpx.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            follow_redirects=True,
        )
    except httpx.TimeoutException:
        result["status"] = "error"
        result["summary"] = "FAIL - Request timed out"
        return result
    except Exception as e:
        result["status"] = "error"
        result["summary"] = f"FAIL - Request error: {e}"
        return result

    # HTTP 状态检查
    if resp.status_code != 200:
        result["status"] = "error"
        result["summary"] = f"FAIL - HTTP {resp.status_code}"
        if resp.status_code in (301, 302, 303, 307, 308):
            result["details"]["redirect_to"] = resp.headers.get("location", "")
        return result

    html = resp.text

    # 登录墙检测
    if is_login_wall(html):
        result["status"] = "login_wall"
        result["needs_browser"] = True
        result["summary"] = (
            "INCONCLUSIVE - Instagram login wall detected. "
            "Use CDP browser (Pydoll/Chrome port 9222) for full verification."
        )
        result["details"]["hint"] = (
            "Chrome CDP: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome "
            "--remote-debugging-port=9222 --user-data-dir=/tmp/chrome-ig-cdp"
        )
        return result

    # 解析 OG meta
    og = parse_og_meta(html)
    checks = result["checks"]

    # Check 1: 可访问
    checks["accessible"] = True

    # Check 2: 图片
    og_image = og.get("og:image", "")
    checks["has_images"] = bool(og_image)
    checks["image_count"] = 1 if og_image else 0  # OG meta 只能检测到 1 张
    if og_image:
        result["details"]["og_image"] = og_image

    # Check 3: 标题/描述
    og_title = og.get("og:title", "") or og.get("page_title", "")
    og_desc = og.get("og:description", "") or og.get("meta:description", "")
    checks["has_title"] = bool(og_title)
    checks["has_content"] = bool(og_desc)
    if og_title:
        result["details"]["og_title"] = og_title
    if og_desc:
        result["details"]["og_description"] = og_desc

    # Check 4: 关键词匹配
    if keywords:
        combined_text = f"{og_title} {og_desc}".lower()
        for kw in keywords:
            kw_lower = kw.strip().lower()
            if kw_lower and kw_lower in combined_text:
                checks["keywords_matched"].append(kw.strip())
            elif kw_lower:
                checks["keywords_missing"].append(kw.strip())

    # Check 5: Hashtags
    hashtags = extract_hashtags(og_desc)
    checks["tag_count"] = len(hashtags)
    checks["has_tags"] = len(hashtags) > 0
    if hashtags:
        result["details"]["hashtags"] = hashtags

    # OG type
    og_type = og.get("og:type", "")
    if og_type:
        result["details"]["og_type"] = og_type

    # 汇总
    passed = sum([
        checks["accessible"],
        checks["has_images"],
        checks["has_title"] or checks["has_content"],  # 标题或内容至少有一个
        len(checks.get("keywords_missing", [])) == 0 if keywords else True,
    ])
    total = 4 if keywords else 3

    if passed == total:
        result["status"] = "published"
        result["summary"] = f"PASS - {passed}/{total} checks passed (via curl/og:meta)"
    else:
        result["status"] = "partial"
        failures = []
        if not checks["accessible"]:
            failures.append("not_accessible")
        if not checks["has_images"]:
            failures.append("no_og_image")
        if not (checks["has_title"] or checks["has_content"]):
            failures.append("no_title_or_content")
        if keywords and checks.get("keywords_missing"):
            failures.append(f"missing_keywords:{','.join(checks['keywords_missing'])}")
        result["summary"] = (
            f"PARTIAL - {passed}/{total} checks passed, "
            f"failures: {', '.join(failures)}"
        )

    # 提醒 curl 的局限
    if not result.get("needs_browser"):
        result["details"]["note"] = (
            "curl-based verification has limited visibility. "
            "Image count may be undercounted (og:meta only shows 1). "
            "For full verification, use CDP browser."
        )

    return result


# ─────────────────────────────────────────────
# 验证用户主页
# ─────────────────────────────────────────────

def verify_profile(username: str, keywords: list[str] | None = None) -> dict:
    """
    验证 Instagram 用户主页可访问性

    Returns:
        验证结果 dict
    """
    url = f"https://www.instagram.com/{username}/"

    result = {
        "platform": "instagram",
        "url": url,
        "username": username,
        "status": "unknown",
        "checks": {
            "accessible": False,
            "has_images": False,
            "has_title": False,
            "has_content": False,
            "keywords_matched": [],
            "keywords_missing": [],
        },
        "details": {},
        "needs_browser": False,
        "summary": "",
    }

    try:
        resp = httpx.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            follow_redirects=True,
        )
    except Exception as e:
        result["status"] = "error"
        result["summary"] = f"FAIL - Request error: {e}"
        return result

    if resp.status_code != 200:
        result["status"] = "error"
        result["summary"] = f"FAIL - HTTP {resp.status_code}"
        return result

    html = resp.text

    if is_login_wall(html):
        result["status"] = "login_wall"
        result["needs_browser"] = True
        result["summary"] = (
            "INCONCLUSIVE - Login wall. Use CDP browser for verification."
        )
        return result

    og = parse_og_meta(html)
    checks = result["checks"]

    checks["accessible"] = True

    og_image = og.get("og:image", "")
    checks["has_images"] = bool(og_image)
    if og_image:
        result["details"]["avatar"] = og_image

    og_title = og.get("og:title", "") or og.get("page_title", "")
    og_desc = og.get("og:description", "") or og.get("meta:description", "")
    checks["has_title"] = bool(og_title)
    checks["has_content"] = bool(og_desc)

    if og_title:
        result["details"]["og_title"] = og_title
    if og_desc:
        result["details"]["og_description"] = og_desc

    # 从 description 解析 follower 等信息
    # 典型格式: "123 Followers, 456 Following, 789 Posts - See Instagram photos..."
    follower_match = re.search(r"([\d,.]+[KkMm]?)\s*Followers?", og_desc)
    if follower_match:
        result["details"]["followers"] = follower_match.group(1)

    post_match = re.search(r"([\d,.]+)\s*Posts?", og_desc)
    if post_match:
        result["details"]["posts"] = post_match.group(1)

    if keywords:
        combined_text = f"{og_title} {og_desc}".lower()
        for kw in keywords:
            kw_lower = kw.strip().lower()
            if kw_lower and kw_lower in combined_text:
                checks["keywords_matched"].append(kw.strip())
            elif kw_lower:
                checks["keywords_missing"].append(kw.strip())

    # 汇总
    passed = sum([
        checks["accessible"],
        checks["has_title"] or checks["has_content"],
    ])
    total = 2

    if passed == total:
        result["status"] = "published"
        result["summary"] = f"PASS - Profile accessible, {passed}/{total} checks passed"
    else:
        result["status"] = "partial"
        result["summary"] = f"PARTIAL - {passed}/{total} checks passed"

    return result


# ─────────────────────────────────────────────
# 人类可读输出
# ─────────────────────────────────────────────

def print_human_summary(result: dict) -> None:
    """打印人类可读的验证摘要"""
    status_map = {
        "published": "[OK]",
        "partial": "[WARN]",
        "login_wall": "[BLOCKED]",
        "error": "[ERROR]",
        "unknown": "[??]",
    }

    status = result.get("status", "unknown")
    icon = status_map.get(status, "[??]")

    print(f"\n{'='*60}")
    print(f"  {icon} {result.get('summary', 'No summary')}")
    print(f"{'='*60}")

    if result.get("url"):
        print(f"  URL:       {result['url']}")
    if result.get("username"):
        print(f"  Username:  {result['username']}")

    details = result.get("details", {})
    if details.get("og_title"):
        print(f"  Title:     {details['og_title'][:80]}")
    if details.get("og_description"):
        desc_preview = details["og_description"][:100]
        if len(details["og_description"]) > 100:
            desc_preview += "..."
        print(f"  Desc:      {desc_preview}")
    if details.get("followers"):
        print(f"  Followers: {details['followers']}")
    if details.get("posts"):
        print(f"  Posts:     {details['posts']}")
    if details.get("hashtags"):
        print(f"  Hashtags:  {', '.join('#' + h for h in details['hashtags'][:10])}")

    checks = result.get("checks", {})
    print(f"\n  Checks:")
    print(f"    Accessible:    {'YES' if checks.get('accessible') else 'NO'}")
    if "has_images" in checks:
        print(f"    Has image:     {'YES' if checks.get('has_images') else 'NO'} (count: {checks.get('image_count', '?')})")
    print(f"    Has title:     {'YES' if checks.get('has_title') else 'NO'}")
    print(f"    Has content:   {'YES' if checks.get('has_content') else 'NO'}")

    if checks.get("keywords_matched") or checks.get("keywords_missing"):
        matched = checks.get("keywords_matched", [])
        missing = checks.get("keywords_missing", [])
        print(f"    Keywords:      matched={matched}, missing={missing}")

    if "has_tags" in checks:
        print(f"    Has hashtags:  {'YES' if checks.get('has_tags') else 'NO'} (count: {checks.get('tag_count', 0)})")

    if result.get("needs_browser"):
        print(f"\n  ** Browser verification needed **")
        print(f"     Instagram returned a login wall.")
        print(f"     Start Chrome with CDP:")
        print(f"       /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\")
        print(f"         --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-ig-cdp")
        print(f"     Then use Pydoll or CDP-based verification.")

    if details.get("note"):
        print(f"\n  Note: {details['note']}")

    print()


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="验证 Instagram 帖子/主页发布状态",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  verify_ig.py https://www.instagram.com/p/ABC123/
  verify_ig.py https://www.instagram.com/p/ABC123/ --keywords "NA,26SS"
  verify_ig.py --username necessaryananke
  verify_ig.py --username necessaryananke --keywords "fashion"
        """,
    )
    parser.add_argument("url", nargs="?", help="Instagram 帖子 URL")
    parser.add_argument("--username", type=str, help="验证用户主页")
    parser.add_argument("--keywords", type=str, help="逗号分隔的关键词列表")
    parser.add_argument("--json", action="store_true", help="仅输出 JSON")

    args = parser.parse_args()

    # 解析关键词
    keywords = None
    if args.keywords:
        keywords = [kw.strip() for kw in args.keywords.split(",") if kw.strip()]

    if args.username:
        # 验证用户主页
        if not args.json:
            print(f"[verify-ig] Checking profile: @{args.username}")

        result = verify_profile(args.username, keywords)

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_human_summary(result)

        sys.exit(0 if result["status"] == "published" else 1)

    elif args.url:
        # 验证帖子
        url = args.url.strip()

        # 规范化 URL
        if not url.startswith("http"):
            url = f"https://www.instagram.com/p/{url}/"

        if not args.json:
            print(f"[verify-ig] Checking post: {url}")

        result = verify_post(url, keywords)

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_human_summary(result)

        sys.exit(0 if result["status"] == "published" else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
