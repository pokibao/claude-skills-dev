#!/usr/bin/env /opt/homebrew/bin/python3
"""
verify_batch.py — 批量流水线输出验证器

五层检查：文件计数 → 文件完整性 → 命名规范 → 抽样质检 → 差异报告

用法:
    python3 verify_batch.py /path/to/output
    python3 verify_batch.py /path/to/output --expected 75
    python3 verify_batch.py /path/to/output --expected 75 --pattern "Look_\\d{2}_.*\\.png"
    python3 verify_batch.py /path/to/output --min-size 50 --sample 5
"""

import argparse
import json
import os
import random
import re
import sys
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}


def find_images(directory: str, recursive: bool = True) -> list[Path]:
    """Find all image files in directory."""
    root = Path(directory)
    if not root.is_dir():
        print(f"ERROR: {directory} is not a valid directory", file=sys.stderr)
        sys.exit(1)

    images = []
    if recursive:
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                images.append(p)
    else:
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                images.append(p)

    return sorted(images)


def check_integrity(filepath: Path, min_size_kb: float) -> dict:
    """Layer 2: Check file integrity — size, PIL openable, not zero-byte."""
    result = {
        "file": str(filepath.name),
        "path": str(filepath),
        "size_kb": 0,
        "passed": False,
        "issues": [],
    }

    # Size check
    try:
        size_bytes = filepath.stat().st_size
        result["size_kb"] = round(size_bytes / 1024, 1)
    except OSError as e:
        result["issues"].append(f"cannot stat: {e}")
        return result

    if size_bytes == 0:
        result["issues"].append("zero-byte file")
        return result

    if result["size_kb"] < min_size_kb:
        result["issues"].append(f"too small: {result['size_kb']}KB < {min_size_kb}KB threshold")

    # PIL check
    try:
        from PIL import Image

        with Image.open(filepath) as img:
            img.verify()
        # Re-open after verify (verify can leave file in bad state)
        with Image.open(filepath) as img:
            result["resolution"] = f"{img.width}x{img.height}"
            result["mode"] = img.mode
    except ImportError:
        result["issues"].append("PIL not available, skipping image validation")
    except Exception as e:
        result["issues"].append(f"corrupt/unreadable: {e}")
        return result

    if not result["issues"]:
        result["passed"] = True

    return result


def check_naming(filepath: Path, pattern: str | None) -> dict:
    """Layer 3: Check naming convention."""
    result = {"file": filepath.name, "matches_pattern": None}
    if pattern:
        result["matches_pattern"] = bool(re.match(pattern, filepath.name))
    return result


def detect_sequence_gaps(filenames: list[str]) -> list[int]:
    """Detect gaps in numbered sequences.

    Tries common patterns:
    - Look_01, Look_02, ...
    - 001, 002, ...
    - item_1, item_2, ...
    """
    numbers = set()
    patterns_tried = [
        r"(?:Look|look|LOOK)[_-]?(\d+)",
        r"^(\d+)[_.\-]",
        r"[_-](\d+)[_.\-]",
        r"(\d+)",
    ]

    best_numbers = set()
    for pat in patterns_tried:
        nums = set()
        for name in filenames:
            m = re.search(pat, name)
            if m:
                nums.add(int(m.group(1)))
        if len(nums) > len(best_numbers):
            best_numbers = nums

    if not best_numbers or len(best_numbers) < 2:
        return []

    min_n = min(best_numbers)
    max_n = max(best_numbers)
    expected = set(range(min_n, max_n + 1))
    missing = sorted(expected - best_numbers)
    return missing


def sample_deep_check(images: list[Path], sample_size: int) -> list[dict]:
    """Layer 4: Random sample for deeper quality checks."""
    if not images:
        return []

    sample = random.sample(images, min(sample_size, len(images)))
    results = []

    try:
        from PIL import Image
    except ImportError:
        return [{"file": str(p.name), "error": "PIL not available"} for p in sample]

    for filepath in sample:
        info = {
            "file": str(filepath.name),
            "path": str(filepath),
        }
        try:
            with Image.open(filepath) as img:
                info["resolution"] = f"{img.width}x{img.height}"
                info["size_kb"] = str(round(filepath.stat().st_size / 1024, 1))
                info["mode"] = img.mode
                info["format"] = img.format

                # Check if mostly white background (for product shots)
                if img.mode in ("RGB", "RGBA"):
                    # Sample corners for white bg detection
                    w, h = img.size
                    corners = [
                        img.getpixel((5, 5)),
                        img.getpixel((w - 6, 5)),
                        img.getpixel((5, h - 6)),
                        img.getpixel((w - 6, h - 6)),
                    ]
                    white_corners = 0
                    for c in corners:
                        if isinstance(c, int):
                            rgb = (c, c, c)
                        elif isinstance(c, (tuple, list)) and len(c) >= 3:
                            rgb = (c[0], c[1], c[2])
                        elif isinstance(c, (tuple, list)) and len(c) > 0:
                            rgb = (c[0], c[0], c[0])
                        else:
                            rgb = (0, 0, 0)
                        if all(v > 240 for v in rgb):
                            white_corners += 1
                    info["white_bg_corners"] = f"{white_corners}/4"
                    info["likely_white_bg"] = str(white_corners >= 3)

        except Exception as e:
            info["error"] = str(e)

        results.append(info)

    return results


def run_verification(
    directory: str,
    expected: int | None = None,
    pattern: str | None = None,
    min_size_kb: float = 10.0,
    sample_size: int = 3,
    recursive: bool = True,
) -> dict:
    """Run all 5 layers of verification."""

    # Layer 1: File count
    images = find_images(directory, recursive=recursive)
    total = len(images)

    report = {
        "directory": str(Path(directory).resolve()),
        "total": total,
        "expected": expected,
        "count_match": None,
        "passed": 0,
        "failed": 0,
        "corrupt": [],
        "too_small": [],
        "zero_byte": [],
        "naming_mismatches": [],
        "missing_sequence": [],
        "sample_results": [],
    }

    if expected is not None:
        report["count_match"] = total == expected
        report["count_diff"] = total - expected

    # Layer 2: File integrity
    for img_path in images:
        check = check_integrity(img_path, min_size_kb)
        if check["passed"]:
            report["passed"] += 1
        else:
            report["failed"] += 1
            for issue in check["issues"]:
                if "zero-byte" in issue:
                    report["zero_byte"].append(check["file"])
                elif "corrupt" in issue or "unreadable" in issue:
                    report["corrupt"].append(check["file"])
                elif "too small" in issue:
                    report["too_small"].append({"file": check["file"], "size_kb": check["size_kb"]})

    # Layer 3: Naming convention
    if pattern:
        for img_path in images:
            naming = check_naming(img_path, pattern)
            if naming["matches_pattern"] is False:
                report["naming_mismatches"].append(img_path.name)

    # Layer 3b: Sequence gap detection
    filenames = [p.name for p in images]
    report["missing_sequence"] = detect_sequence_gaps(filenames)

    # Layer 4: Sampling quality
    passed_images = [p for p in images if p.stat().st_size > min_size_kb * 1024]
    report["sample_results"] = sample_deep_check(
        passed_images if passed_images else images, sample_size
    )

    return report


def print_summary(report: dict) -> None:
    """Print human-readable summary."""
    print("=" * 60)
    print("  VERIFY-PIPELINE  Batch Output Report")
    print("=" * 60)
    print(f"  Directory : {report['directory']}")
    print(f"  Total     : {report['total']} images found")

    if report["expected"] is not None:
        status = "PASS" if report["count_match"] else "FAIL"
        diff = report["count_diff"]
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        print(f"  Expected  : {report['expected']} ({status}, diff: {diff_str})")

    print()
    print(f"  Passed    : {report['passed']}")
    print(f"  Failed    : {report['failed']}")

    if report["zero_byte"]:
        print(f"\n  Zero-byte files ({len(report['zero_byte'])}):")
        for f in report["zero_byte"][:10]:
            print(f"    - {f}")
        if len(report["zero_byte"]) > 10:
            print(f"    ... and {len(report['zero_byte']) - 10} more")

    if report["corrupt"]:
        print(f"\n  Corrupt/unreadable ({len(report['corrupt'])}):")
        for f in report["corrupt"][:10]:
            print(f"    - {f}")
        if len(report["corrupt"]) > 10:
            print(f"    ... and {len(report['corrupt']) - 10} more")

    if report["too_small"]:
        print(f"\n  Too small ({len(report['too_small'])}):")
        for item in report["too_small"][:10]:
            print(f"    - {item['file']} ({item['size_kb']}KB)")
        if len(report["too_small"]) > 10:
            print(f"    ... and {len(report['too_small']) - 10} more")

    if report["naming_mismatches"]:
        print(f"\n  Naming mismatches ({len(report['naming_mismatches'])}):")
        for f in report["naming_mismatches"][:10]:
            print(f"    - {f}")
        if len(report["naming_mismatches"]) > 10:
            print(f"    ... and {len(report['naming_mismatches']) - 10} more")

    if report["missing_sequence"]:
        print(f"\n  Missing in sequence ({len(report['missing_sequence'])}):")
        # Group consecutive numbers for readability
        gaps = report["missing_sequence"]
        if len(gaps) <= 20:
            print(f"    {gaps}")
        else:
            print(f"    {gaps[:10]} ... ({len(gaps)} total)")

    if report["sample_results"]:
        print(f"\n  Sample quality check ({len(report['sample_results'])} images):")
        for s in report["sample_results"]:
            if "error" in s:
                print(f"    - {s['file']}: ERROR {s['error']}")
            else:
                wb = ""
                if "likely_white_bg" in s:
                    wb = f", white_bg={'yes' if s['likely_white_bg'] else 'no'}({s.get('white_bg_corners', '?')})"
                print(f"    - {s['file']}: {s.get('resolution', '?')} {s.get('mode', '?')} {s.get('size_kb', '?')}KB{wb}")

    # Overall verdict
    print()
    issues = (
        len(report["corrupt"])
        + len(report["too_small"])
        + len(report["zero_byte"])
    )
    if report["expected"] is not None and not report["count_match"]:
        issues += 1

    if issues == 0:
        print("  VERDICT: ALL PASSED")
    else:
        print(f"  VERDICT: {issues} ISSUE(S) FOUND — review above")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Verify batch pipeline output completeness and quality"
    )
    parser.add_argument("directory", help="Output directory to verify")
    parser.add_argument("--expected", type=int, default=None, help="Expected number of output files")
    parser.add_argument("--pattern", type=str, default=None, help="Filename regex pattern to match")
    parser.add_argument("--min-size", type=float, default=10.0, help="Minimum file size in KB (default: 10)")
    parser.add_argument("--sample", type=int, default=3, help="Number of images to sample for deep check (default: 3)")
    parser.add_argument("--no-recursive", action="store_true", help="Do not scan subdirectories")
    parser.add_argument("--json", action="store_true", help="Output only JSON (no summary)")

    args = parser.parse_args()

    report = run_verification(
        directory=args.directory,
        expected=args.expected,
        pattern=args.pattern,
        min_size_kb=args.min_size,
        sample_size=args.sample,
        recursive=not args.no_recursive,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_summary(report)
        # Also save JSON report next to the directory
        report_path = Path(args.directory).resolve().parent / f"verify_report_{Path(args.directory).name}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n  JSON report saved: {report_path}")


if __name__ == "__main__":
    main()
