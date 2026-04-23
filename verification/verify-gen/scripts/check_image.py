#!/usr/bin/env /opt/homebrew/bin/python3
"""
check_image.py — 单张 AI 生图质量验证

用法:
    python3 check_image.py /path/to/image.png
    python3 check_image.py /path/to/image.png --json  (纯 JSON 输出)

检查项:
    1. 文件可读性 (PIL 能打开)
    2. 白底背景 (四角 + 边缘 RGB 均值 > 245)
    3. 分辨率 (宽高 >= 2048)
    4. 文件大小 (100KB ~ 50MB)
    5. 宽高比 (0.5 ~ 2.0)
    6. 色彩方差 (标准差 > 10, 排除纯色空白图)
"""

import json
import os
import sys
import statistics
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow", file=sys.stderr)
    sys.exit(1)


# ── 配置阈值 ──────────────────────────────────────────────

WHITE_THRESHOLD = 245       # RGB 均值高于此值视为白色
MIN_RESOLUTION = 2048       # 宽高最低像素
MIN_FILE_SIZE = 100 * 1024  # 100 KB
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MIN_ASPECT_RATIO = 0.5
MAX_ASPECT_RATIO = 2.0
MIN_COLOR_STDDEV = 10       # 色彩标准差低于此值视为空白图
EDGE_STRIP_PX = 20          # 边缘采样条宽度(像素)
CORNER_SIZE_PX = 50         # 角落采样区域大小(像素)


# ── 检查函数 ──────────────────────────────────────────────

def check_readable(path: str) -> dict:
    """检查文件是否可被 PIL 打开"""
    try:
        img = Image.open(path)
        img.verify()  # 验证文件完整性
        return {"check": "readable", "passed": True, "detail": "OK"}
    except Exception as e:
        return {"check": "readable", "passed": False, "detail": str(e)}


def check_file_size(path: str) -> dict:
    """检查文件大小在合理范围"""
    size = os.path.getsize(path)
    size_kb = size / 1024
    size_mb = size / (1024 * 1024)

    if size < MIN_FILE_SIZE:
        return {
            "check": "file_size",
            "passed": False,
            "detail": f"{size_kb:.1f}KB < 100KB minimum (可能是空白/损坏图)",
            "value": size,
        }
    if size > MAX_FILE_SIZE:
        return {
            "check": "file_size",
            "passed": False,
            "detail": f"{size_mb:.1f}MB > 50MB maximum",
            "value": size,
        }
    return {
        "check": "file_size",
        "passed": True,
        "detail": f"{size_mb:.2f}MB" if size_mb >= 1 else f"{size_kb:.1f}KB",
        "value": size,
    }


def check_resolution(img: Image.Image) -> dict:
    """检查分辨率 >= 2048 x 2048"""
    w, h = img.size
    passed = w >= MIN_RESOLUTION and h >= MIN_RESOLUTION
    detail = f"{w}x{h}"
    if not passed:
        fails = []
        if w < MIN_RESOLUTION:
            fails.append(f"width {w} < {MIN_RESOLUTION}")
        if h < MIN_RESOLUTION:
            fails.append(f"height {h} < {MIN_RESOLUTION}")
        detail += f" — {', '.join(fails)}"
    return {
        "check": "resolution",
        "passed": passed,
        "detail": detail,
        "value": {"width": w, "height": h},
    }


def check_aspect_ratio(img: Image.Image) -> dict:
    """检查宽高比在合理范围"""
    w, h = img.size
    ratio = w / h if h > 0 else 0
    passed = MIN_ASPECT_RATIO <= ratio <= MAX_ASPECT_RATIO
    detail = f"{ratio:.3f} (w/h)"
    if not passed:
        detail += f" — outside [{MIN_ASPECT_RATIO}, {MAX_ASPECT_RATIO}]"
    return {
        "check": "aspect_ratio",
        "passed": passed,
        "detail": detail,
        "value": ratio,
    }


def _sample_region_avg(img: Image.Image, box: tuple) -> tuple:
    """采样指定区域的 RGB 均值"""
    region = img.crop(box)
    pixels = list(region.getdata())
    if not pixels:
        return (0, 0, 0)
    # 处理不同模式
    if img.mode == "RGBA":
        r_avg = sum(p[0] for p in pixels) / len(pixels)
        g_avg = sum(p[1] for p in pixels) / len(pixels)
        b_avg = sum(p[2] for p in pixels) / len(pixels)
    elif img.mode == "RGB":
        r_avg = sum(p[0] for p in pixels) / len(pixels)
        g_avg = sum(p[1] for p in pixels) / len(pixels)
        b_avg = sum(p[2] for p in pixels) / len(pixels)
    elif img.mode == "L":
        avg = sum(p for p in pixels) / len(pixels)
        return (avg, avg, avg)
    else:
        # 转 RGB 再处理
        rgb_region = region.convert("RGB")
        pixels = list(rgb_region.getdata())
        r_avg = sum(p[0] for p in pixels) / len(pixels)
        g_avg = sum(p[1] for p in pixels) / len(pixels)
        b_avg = sum(p[2] for p in pixels) / len(pixels)
    return (r_avg, g_avg, b_avg)


def check_white_background(img: Image.Image) -> dict:
    """
    检查白底背景:
    - 四个角落 (CORNER_SIZE_PX x CORNER_SIZE_PX)
    - 四条边缘 (EDGE_STRIP_PX 宽的条带)
    所有采样区域 RGB 均值 > WHITE_THRESHOLD
    """
    w, h = img.size
    cs = min(CORNER_SIZE_PX, w // 4, h // 4)
    es = min(EDGE_STRIP_PX, w // 4, h // 4)

    # 四角: 左上, 右上, 左下, 右下
    corners = {
        "top_left": (0, 0, cs, cs),
        "top_right": (w - cs, 0, w, cs),
        "bottom_left": (0, h - cs, cs, h),
        "bottom_right": (w - cs, h - cs, w, h),
    }

    # 四边缘条带 (去掉角落重叠区域)
    edges = {
        "top_edge": (cs, 0, w - cs, es),
        "bottom_edge": (cs, h - es, w - cs, h),
        "left_edge": (0, cs, es, h - cs),
        "right_edge": (w - es, cs, w, h - cs),
    }

    failed_regions = []
    region_details = {}

    for name, box in {**corners, **edges}.items():
        # 确保 box 有效
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        avg_rgb = _sample_region_avg(img, box)
        avg_val = sum(avg_rgb) / 3
        region_details[name] = {
            "rgb": [round(c, 1) for c in avg_rgb],
            "mean": round(avg_val, 1),
        }
        if avg_val < WHITE_THRESHOLD:
            failed_regions.append(name)

    passed = len(failed_regions) == 0
    if passed:
        detail = "所有角落和边缘均为白色"
    else:
        detail = f"非白色区域: {', '.join(failed_regions)}"
        for fr in failed_regions:
            info = region_details[fr]
            detail += f" [{fr}: RGB({info['rgb'][0]},{info['rgb'][1]},{info['rgb'][2]}) mean={info['mean']}]"

    return {
        "check": "white_background",
        "passed": passed,
        "detail": detail,
        "regions": region_details,
        "failed_regions": failed_regions,
    }


def check_color_variance(img: Image.Image) -> dict:
    """
    检查色彩方差，排除纯色空白图。
    对图片降采样后计算 RGB 各通道标准差的均值。
    """
    # 降采样到 256x256 提升速度
    thumb = img.copy()
    thumb.thumbnail((256, 256))
    if thumb.mode not in ("RGB", "RGBA"):
        thumb = thumb.convert("RGB")

    pixels = list(thumb.getdata())
    if len(pixels) < 10:
        return {
            "check": "color_variance",
            "passed": False,
            "detail": "图片像素不足",
            "value": 0,
        }

    r_vals = [p[0] for p in pixels]
    g_vals = [p[1] for p in pixels]
    b_vals = [p[2] for p in pixels]

    r_std = statistics.pstdev(r_vals)
    g_std = statistics.pstdev(g_vals)
    b_std = statistics.pstdev(b_vals)
    avg_std = (r_std + g_std + b_std) / 3

    passed = avg_std > MIN_COLOR_STDDEV
    detail = f"RGB stddev: R={r_std:.1f} G={g_std:.1f} B={b_std:.1f}, avg={avg_std:.1f}"
    if not passed:
        detail += f" — < {MIN_COLOR_STDDEV} (可能是纯色空白图)"

    return {
        "check": "color_variance",
        "passed": passed,
        "detail": detail,
        "value": round(avg_std, 2),
    }


# ── 主函数 ────────────────────────────────────────────────

def verify_image(path: str) -> dict:
    """运行所有检查，返回综合结果"""
    path = str(Path(path).resolve())
    result = {
        "file": path,
        "filename": os.path.basename(path),
        "checks": [],
        "passed": False,
        "failed_checks": [],
    }

    # 1. 文件可读性
    readable = check_readable(path)
    result["checks"].append(readable)
    if not readable["passed"]:
        result["failed_checks"].append("readable")
        return result

    # 2. 文件大小
    size_check = check_file_size(path)
    result["checks"].append(size_check)
    if not size_check["passed"]:
        result["failed_checks"].append("file_size")

    # 打开图片进行后续检查
    try:
        img = Image.open(path)
        # 处理 EXIF 旋转
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # 转 RGB 用于分析 (保留原始模式信息)
        original_mode = img.mode
        if img.mode == "P":
            img = img.convert("RGBA" if "transparency" in img.info else "RGB")
        elif img.mode not in ("RGB", "RGBA", "L"):
            img = img.convert("RGB")

        # 3. 分辨率
        res_check = check_resolution(img)
        result["checks"].append(res_check)
        if not res_check["passed"]:
            result["failed_checks"].append("resolution")

        # 4. 宽高比
        ar_check = check_aspect_ratio(img)
        result["checks"].append(ar_check)
        if not ar_check["passed"]:
            result["failed_checks"].append("aspect_ratio")

        # 5. 白底背景
        wb_check = check_white_background(img)
        result["checks"].append(wb_check)
        if not wb_check["passed"]:
            result["failed_checks"].append("white_background")

        # 6. 色彩方差
        cv_check = check_color_variance(img)
        result["checks"].append(cv_check)
        if not cv_check["passed"]:
            result["failed_checks"].append("color_variance")

    except Exception as e:
        result["checks"].append({
            "check": "image_open",
            "passed": False,
            "detail": f"无法打开图片: {e}",
        })
        result["failed_checks"].append("image_open")

    # 综合判定
    result["passed"] = len(result["failed_checks"]) == 0
    result["total_checks"] = len(result["checks"])
    result["passed_checks"] = result["total_checks"] - len(result["failed_checks"])

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="AI 生图质量验证 (单张)")
    parser.add_argument("image", help="图片文件路径")
    parser.add_argument("--json", action="store_true", help="纯 JSON 输出")
    args = parser.parse_args()

    if not os.path.isfile(args.image):
        print(f"ERROR: 文件不存在: {args.image}", file=sys.stderr)
        sys.exit(1)

    result = verify_image(args.image)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 人类可读输出
        verdict = "PASS" if result["passed"] else "FAIL"
        print(f"\n{'='*60}")
        print(f"  {verdict}  {result['filename']}")
        print(f"  {result['passed_checks']}/{result['total_checks']} checks passed")
        print(f"{'='*60}")

        for c in result["checks"]:
            icon = "[OK]" if c["passed"] else "[!!]"
            print(f"  {icon} {c['check']}: {c['detail']}")

        if result["failed_checks"]:
            print(f"\n  Failed: {', '.join(result['failed_checks'])}")
        print()

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
