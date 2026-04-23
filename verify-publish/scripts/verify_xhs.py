#!/usr/bin/env /opt/homebrew/bin/python3
"""
小红书发布验证脚本

验证方式（按优先级）：
1. /api/v1/user/me — 获取我的笔记列表，按 note_id 匹配
2. /api/v1/feeds/detail — 获取笔记详情（需 xsec_token，从 user/me 获取）
3. /api/v1/feeds/search — 按关键词搜索匹配

用法：
  verify_xhs.py <note_id_or_url>                        # 验证单条笔记
  verify_xhs.py <note_id> --keywords "极简,法式"         # 带关键词匹配
  verify_xhs.py --recent                                 # 验证最近发布
  verify_xhs.py --recent --count 5                       # 验证最近 5 条
"""

import argparse
import json
import re
import sys
import time
from urllib.parse import urlparse

import httpx

_config = {"mcp_base_url": "http://localhost:18060"}
TIMEOUT = 30  # 秒


def _mcp_url() -> str:
    return _config["mcp_base_url"]


# ─────────────────────────────────────────────
# Helper: MCP health + login check
# ─────────────────────────────────────────────

def check_mcp_health() -> dict:
    """检查 MCP 服务健康状态和登录状态"""
    result = {"mcp_running": False, "logged_in": False, "account": None}
    try:
        resp = httpx.get(f"{_mcp_url()}/health", timeout=5, follow_redirects=True)
        if resp.status_code == 200:
            data = resp.json()
            result["mcp_running"] = data.get("success", False)
            result["account"] = data.get("data", {}).get("account", "unknown")
    except Exception:
        return result

    try:
        resp = httpx.get(
            f"{_mcp_url()}/api/v1/login/status",
            timeout=5,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            data = resp.json()
            result["logged_in"] = data.get("success", False)
    except Exception:
        pass

    return result


# ─────────────────────────────────────────────
# Extract note_id from URL or raw ID
# ─────────────────────────────────────────────

def extract_note_id(input_str: str) -> str:
    """从 URL 或原始字符串中提取 note_id"""
    input_str = input_str.strip()

    # URL 格式: https://www.xiaohongshu.com/explore/6801a2b3c4d5e6f7
    # 或: https://www.xiaohongshu.com/discovery/item/6801a2b3c4d5e6f7
    url_patterns = [
        r"xiaohongshu\.com/explore/([a-f0-9]+)",
        r"xiaohongshu\.com/discovery/item/([a-f0-9]+)",
        r"xhslink\.com/\w+",  # 短链接，无法直接提取 ID
    ]
    for pattern in url_patterns:
        match = re.search(pattern, input_str)
        if match and match.group(1):
            return match.group(1)

    # 纯 hex ID（小红书笔记 ID 通常是 24 位 hex）
    if re.match(r"^[a-f0-9]{16,32}$", input_str):
        return input_str

    return input_str  # 原样返回，让后续逻辑处理


# ─────────────────────────────────────────────
# 获取我的笔记列表（核心验证路径）
# ─────────────────────────────────────────────

def get_my_notes() -> tuple[dict | None, list[dict]]:
    """
    调用 /api/v1/user/me 获取我的笔记列表

    Returns:
        (user_profile_dict, list_of_note_dicts)
    """
    try:
        resp = httpx.get(
            f"{_mcp_url()}/api/v1/user/me",
            timeout=TIMEOUT,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return None, []

        data = resp.json()
        if not data.get("success"):
            return None, []

        user_data = data.get("data", {}).get("data", {})
        basic_info = user_data.get("userBasicInfo", {})

        user_profile = {
            "nickname": basic_info.get("nickname", "unknown"),
            "red_id": basic_info.get("redId", ""),
        }

        feeds = user_data.get("feeds", [])
        notes = []
        for feed in feeds:
            note_card = feed.get("noteCard", {})
            interact_info = note_card.get("interactInfo", {})
            cover = note_card.get("cover", {})
            image_list = note_card.get("imageList", [])

            notes.append({
                "id": feed.get("id", ""),
                "title": note_card.get("displayTitle", ""),
                "cover_url": cover.get("urlDefault", "") or cover.get("urlPre", ""),
                "xsec_token": feed.get("xsecToken", ""),
                "note_type": note_card.get("type", "normal"),
                "liked_count": interact_info.get("likedCount", "0"),
                "collected_count": interact_info.get("collectedCount", "0"),
                "comment_count": interact_info.get("commentCount", "0"),
                "image_count": len(image_list) if image_list else (1 if cover else 0),
                "desc": note_card.get("desc", ""),
                "tag_list": note_card.get("tagList", []),
            })

        return user_profile, notes

    except Exception as e:
        print(f"[ERROR] 获取笔记列表失败: {e}", file=sys.stderr)
        return None, []


# ─────────────────────────────────────────────
# 获取笔记详情（需要 xsec_token）
# ─────────────────────────────────────────────

def get_note_detail(feed_id: str, xsec_token: str) -> dict | None:
    """
    调用 /api/v1/feeds/detail 获取笔记详情

    注意：此 API 标记为"待验证"，可能不稳定
    """
    try:
        resp = httpx.post(
            f"{_mcp_url()}/api/v1/feeds/detail",
            json={"feed_id": feed_id, "xsec_token": xsec_token},
            timeout=TIMEOUT,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        if not data.get("success"):
            return None

        return data.get("data", {})

    except Exception:
        return None


# ─────────────────────────────────────────────
# 验证单条笔记
# ─────────────────────────────────────────────

def verify_note(note_id: str, keywords: list[str] | None = None) -> dict:
    """
    验证单条小红书笔记

    Returns:
        验证结果 dict
    """
    result = {
        "platform": "xiaohongshu",
        "note_id": note_id,
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
        "details": {
            "title": "",
            "url": f"https://www.xiaohongshu.com/explore/{note_id}",
        },
        "summary": "",
    }

    # Step 1: 获取我的笔记列表
    user_profile, notes = get_my_notes()

    if not notes:
        result["status"] = "error"
        result["summary"] = "FAIL - 无法获取笔记列表（MCP 未运行或未登录）"
        return result

    # Step 2: 查找目标笔记
    target_note = None
    for note in notes:
        if note["id"] == note_id:
            target_note = note
            break

    if target_note is None:
        # 尝试模糊匹配（ID 前缀）
        for note in notes:
            if note["id"].startswith(note_id) or note_id.startswith(note["id"]):
                target_note = note
                break

    if target_note is None:
        result["status"] = "not_found"
        result["summary"] = (
            f"FAIL - 笔记 {note_id} 未在最近发布列表中找到"
            f"（共 {len(notes)} 条笔记）"
        )
        return result

    # Step 3: 运行检查
    checks = result["checks"]

    # Check 1: 可访问
    checks["accessible"] = True

    # Check 2: 图片
    checks["image_count"] = target_note.get("image_count", 0)
    checks["has_images"] = checks["image_count"] > 0

    # Check 3: 标题
    title = target_note.get("title", "").strip()
    checks["has_title"] = bool(title)
    result["details"]["title"] = title

    # Check 4: 内容
    desc = target_note.get("desc", "").strip()
    checks["has_content"] = bool(desc)

    # Check 5: 关键词匹配
    if keywords:
        combined_text = f"{title} {desc}".lower()
        for kw in keywords:
            kw_lower = kw.strip().lower()
            if kw_lower and kw_lower in combined_text:
                checks["keywords_matched"].append(kw.strip())
            elif kw_lower:
                checks["keywords_missing"].append(kw.strip())

    # Check 6: 标签
    tag_list = target_note.get("tag_list", [])
    checks["tag_count"] = len(tag_list)
    checks["has_tags"] = len(tag_list) > 0

    # Step 4: 尝试获取详情（补充信息）
    xsec_token = target_note.get("xsec_token", "")
    if xsec_token:
        detail = get_note_detail(note_id, xsec_token)
        if detail:
            # 更新更详细的信息
            note_detail = detail.get("noteDetail", detail)
            if isinstance(note_detail, dict):
                detail_images = note_detail.get("imageList", [])
                if detail_images:
                    checks["image_count"] = len(detail_images)
                    checks["has_images"] = True

                detail_desc = note_detail.get("desc", "")
                if detail_desc and not desc:
                    checks["has_content"] = bool(detail_desc.strip())

                detail_tags = note_detail.get("tagList", [])
                if detail_tags:
                    checks["tag_count"] = len(detail_tags)
                    checks["has_tags"] = True

    # Step 5: 补充互动数据
    result["details"]["liked_count"] = target_note.get("liked_count", "0")
    result["details"]["collected_count"] = target_note.get("collected_count", "0")
    result["details"]["comment_count"] = target_note.get("comment_count", "0")
    result["details"]["note_type"] = target_note.get("note_type", "normal")

    if user_profile:
        result["details"]["account"] = user_profile.get("nickname", "unknown")

    # Step 6: 汇总
    passed = sum([
        checks["accessible"],
        checks["has_images"],
        checks["has_title"],
        checks["has_content"],
        len(checks.get("keywords_missing", [])) == 0 if keywords else True,
    ])
    total = 5 if keywords else 4  # 无关键词时跳过关键词检查

    if passed == total:
        result["status"] = "published"
        result["summary"] = f"PASS - {passed}/{total} checks passed"
    else:
        result["status"] = "partial"
        failures = []
        if not checks["accessible"]:
            failures.append("not_accessible")
        if not checks["has_images"]:
            failures.append("no_images")
        if not checks["has_title"]:
            failures.append("no_title")
        if not checks["has_content"]:
            failures.append("no_content")
        if keywords and checks.get("keywords_missing"):
            failures.append(f"missing_keywords:{','.join(checks['keywords_missing'])}")
        result["summary"] = f"PARTIAL - {passed}/{total} checks passed, failures: {', '.join(failures)}"

    return result


# ─────────────────────────────────────────────
# 验证最近发布的笔记
# ─────────────────────────────────────────────

def verify_recent(count: int = 3, keywords: list[str] | None = None) -> list[dict]:
    """验证最近发布的 N 条笔记"""
    user_profile, notes = get_my_notes()

    if not notes:
        return [{
            "platform": "xiaohongshu",
            "status": "error",
            "summary": "FAIL - 无法获取笔记列表",
        }]

    results = []
    check_notes = notes[:count]

    for note in check_notes:
        result = verify_note(note["id"], keywords)
        results.append(result)
        # 间隔避免频率限制
        if len(check_notes) > 1:
            time.sleep(0.5)

    return results


# ─────────────────────────────────────────────
# 人类可读输出
# ─────────────────────────────────────────────

def print_human_summary(result: dict) -> None:
    """打印人类可读的验证摘要"""
    status_emoji = {
        "published": "[OK]",
        "partial": "[WARN]",
        "not_found": "[FAIL]",
        "error": "[ERROR]",
        "unknown": "[??]",
    }

    status = result.get("status", "unknown")
    icon = status_emoji.get(status, "[??]")

    print(f"\n{'='*60}")
    print(f"  {icon} {result.get('summary', 'No summary')}")
    print(f"{'='*60}")

    details = result.get("details", {})
    if details.get("title"):
        print(f"  Title:   {details['title']}")
    if details.get("url"):
        print(f"  URL:     {details['url']}")
    if details.get("account"):
        print(f"  Account: {details['account']}")

    checks = result.get("checks", {})
    print(f"\n  Checks:")
    print(f"    Accessible:    {'YES' if checks.get('accessible') else 'NO'}")
    print(f"    Has images:    {'YES' if checks.get('has_images') else 'NO'} (count: {checks.get('image_count', 0)})")
    print(f"    Has title:     {'YES' if checks.get('has_title') else 'NO'}")
    print(f"    Has content:   {'YES' if checks.get('has_content') else 'NO'}")

    if checks.get("keywords_matched") or checks.get("keywords_missing"):
        matched = checks.get("keywords_matched", [])
        missing = checks.get("keywords_missing", [])
        print(f"    Keywords:      matched={matched}, missing={missing}")

    print(f"    Has tags:      {'YES' if checks.get('has_tags') else 'NO'} (count: {checks.get('tag_count', 0)})")

    if details.get("liked_count"):
        print(f"\n  Engagement:")
        print(f"    Likes:     {details.get('liked_count', '0')}")
        print(f"    Collects:  {details.get('collected_count', '0')}")
        print(f"    Comments:  {details.get('comment_count', '0')}")

    print()


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="验证小红书笔记发布状态",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  verify_xhs.py 6801a2b3c4d5e6f7
  verify_xhs.py https://www.xiaohongshu.com/explore/6801a2b3c4d5e6f7
  verify_xhs.py 6801a2b3c4d5e6f7 --keywords "极简,法式"
  verify_xhs.py --recent
  verify_xhs.py --recent --count 5
        """,
    )
    parser.add_argument("input", nargs="?", help="笔记 ID 或 URL")
    parser.add_argument("--keywords", type=str, help="逗号分隔的关键词列表")
    parser.add_argument("--recent", action="store_true", help="验证最近发布的笔记")
    parser.add_argument("--count", type=int, default=3, help="验证最近 N 条（默认 3）")
    parser.add_argument("--json", action="store_true", help="仅输出 JSON")
    default_url = _config["mcp_base_url"]
    parser.add_argument("--mcp-url", type=str, default=default_url,
                        help=f"MCP 服务地址（默认 {default_url}）")

    args = parser.parse_args()

    # 更新 MCP URL
    _config["mcp_base_url"] = args.mcp_url

    # 解析关键词
    keywords = None
    if args.keywords:
        keywords = [kw.strip() for kw in args.keywords.split(",") if kw.strip()]

    # 前置检查：MCP 健康
    if not args.json:
        print("[verify-xhs] Checking MCP status...")

    health = check_mcp_health()

    if not health["mcp_running"]:
        error_result = {
            "platform": "xiaohongshu",
            "status": "error",
            "summary": "FAIL - xiaohongshu-mcp not running (http://localhost:18060)",
            "hint": "Start MCP: cd ~/projects/小红书自动发布 && ./bin/xiaohongshu-mcp -port :18060",
        }
        if args.json:
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
        else:
            print(f"\n[ERROR] MCP 服务未运行")
            print(f"  启动命令: cd ~/projects/小红书自动发布 && ./bin/xiaohongshu-mcp -port :18060")
        sys.exit(1)

    if not health["logged_in"]:
        error_result = {
            "platform": "xiaohongshu",
            "status": "error",
            "summary": "FAIL - Not logged in to xiaohongshu-mcp",
            "hint": "Login: curl http://localhost:18060/api/v1/login/qrcode",
        }
        if args.json:
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
        else:
            print(f"\n[ERROR] 未登录小红书")
            print(f"  登录: curl http://localhost:18060/api/v1/login/qrcode")
        sys.exit(1)

    if not args.json:
        print(f"[verify-xhs] MCP OK, account: {health.get('account', 'unknown')}")

    # 执行验证
    if args.recent:
        results = verify_recent(count=args.count, keywords=keywords)

        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(f"\n[verify-xhs] Verifying {len(results)} recent notes...")
            for r in results:
                print_human_summary(r)

            # 汇总
            passed = sum(1 for r in results if r["status"] == "published")
            total = len(results)
            print(f"{'='*60}")
            print(f"  Total: {passed}/{total} notes verified OK")
            print(f"{'='*60}")

    elif args.input:
        note_id = extract_note_id(args.input)

        if not args.json:
            print(f"[verify-xhs] Verifying note: {note_id}")

        result = verify_note(note_id, keywords)

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_human_summary(result)

        # 退出码：published=0, 其他=1
        sys.exit(0 if result["status"] == "published" else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
