#!/usr/bin/env /opt/homebrew/bin/python3
"""
batch_verify.py — 批量验证 AI 生图输出质量

用法:
    python3 batch_verify.py /path/to/output_dir/
    python3 batch_verify.py /path/to/output_dir/ --output /path/to/report.json
    python3 batch_verify.py /path/to/output_dir/ --recursive
    python3 batch_verify.py /path/to/output_dir/ --fail-only

默认输出目录: 与扫描目录同级，文件名 verify_report_{timestamp}.json
"""

import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

# 导入同目录下的 check_image
sys.path.insert(0, str(Path(__file__).parent))
from check_image import verify_image

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def find_images(directory: str, recursive: bool = False) -> list:
    """查找目录下所有图片文件"""
    directory = Path(directory)
    images = []

    if recursive:
        for ext in IMAGE_EXTENSIONS:
            images.extend(directory.rglob(f"*{ext}"))
            images.extend(directory.rglob(f"*{ext.upper()}"))
    else:
        for ext in IMAGE_EXTENSIONS:
            images.extend(directory.glob(f"*{ext}"))
            images.extend(directory.glob(f"*{ext.upper()}"))

    # 去重 + 排序
    seen = set()
    unique = []
    for p in sorted(images):
        resolved = p.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)

    return unique


def batch_verify(directory: str, recursive: bool = False, fail_only: bool = False) -> dict:
    """批量验证目录下所有图片"""
    start_time = time.time()
    images = find_images(directory, recursive)

    if not images:
        return {
            "directory": str(Path(directory).resolve()),
            "timestamp": datetime.now().isoformat(),
            "total": 0,
            "passed": 0,
            "failed": 0,
            "pass_rate": "N/A",
            "results": [],
            "failure_breakdown": {},
            "duration_seconds": 0,
            "message": "未找到图片文件",
        }

    results = []
    passed_count = 0
    failed_count = 0
    failure_reasons = Counter()

    total = len(images)
    for i, img_path in enumerate(images, 1):
        # 进度输出
        pct = i * 100 // total
        print(f"\r  [{pct:3d}%] {i}/{total} — {img_path.name}", end="", flush=True)

        result = verify_image(str(img_path))

        if result["passed"]:
            passed_count += 1
        else:
            failed_count += 1
            for fc in result["failed_checks"]:
                failure_reasons[fc] += 1

        # fail_only 模式下只保留失败结果
        if not fail_only or not result["passed"]:
            results.append(result)

    print()  # 换行

    duration = time.time() - start_time
    pass_rate = f"{passed_count * 100 / total:.1f}%" if total > 0 else "N/A"

    report = {
        "directory": str(Path(directory).resolve()),
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "passed": passed_count,
        "failed": failed_count,
        "pass_rate": pass_rate,
        "failure_breakdown": dict(failure_reasons.most_common()),
        "duration_seconds": round(duration, 2),
        "results": results,
    }

    return report


def print_summary(report: dict):
    """打印人类可读的摘要"""
    print(f"\n{'='*60}")
    print(f"  AI 生图质量验证报告")
    print(f"{'='*60}")
    print(f"  目录: {report['directory']}")
    print(f"  时间: {report['timestamp']}")
    print(f"  耗时: {report['duration_seconds']}s")
    print(f"{'─'*60}")
    print(f"  总计: {report['total']} 张")
    print(f"  通过: {report['passed']} 张")
    print(f"  失败: {report['failed']} 张")
    print(f"  通过率: {report['pass_rate']}")

    if report["failure_breakdown"]:
        print(f"{'─'*60}")
        print(f"  失败原因分布:")
        for reason, count in report["failure_breakdown"].items():
            bar = "#" * min(count, 40)
            print(f"    {reason:20s} : {count:3d} {bar}")

    if report["failed"] > 0:
        print(f"{'─'*60}")
        print(f"  失败文件:")
        for r in report["results"]:
            if not r["passed"]:
                reasons = ", ".join(r["failed_checks"])
                print(f"    [FAIL] {r['filename']} — {reasons}")

    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="AI 生图批量质量验证")
    parser.add_argument("directory", help="图片目录路径")
    parser.add_argument("--output", "-o", help="报告输出路径 (默认: 目录内 verify_report_{timestamp}.json)")
    parser.add_argument("--recursive", "-r", action="store_true", help="递归扫描子目录")
    parser.add_argument("--fail-only", action="store_true", help="报告中仅包含失败结果")
    parser.add_argument("--json", action="store_true", help="仅输出 JSON (不输出摘要)")
    args = parser.parse_args()

    directory = args.directory
    if not os.path.isdir(directory):
        print(f"ERROR: 目录不存在: {directory}", file=sys.stderr)
        sys.exit(1)

    print(f"\n  扫描目录: {directory}")
    print(f"  递归: {'是' if args.recursive else '否'}")
    print()

    report = batch_verify(directory, recursive=args.recursive, fail_only=args.fail_only)

    # 确定输出路径
    if args.output:
        output_path = args.output
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(directory, f"verify_report_{ts}.json")

    # 保存 JSON 报告
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if args.json:
        # 纯 JSON 模式: 输出到 stdout
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        # 人类可读摘要
        print_summary(report)
        print(f"  报告已保存: {output_path}\n")

    # 退出码: 有失败则非零
    sys.exit(1 if report["failed"] > 0 else 0)


if __name__ == "__main__":
    main()
