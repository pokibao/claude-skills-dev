#!/usr/bin/env /opt/homebrew/bin/python3
"""
compare_io.py — 流水线输入/输出对比验证器

比较输入目录和输出目录，检测：
- 哪些输入没有对应输出（丢失）
- 哪些输出是孤儿（无对应输入）
- 每个输入是否产出了预期数量的变体

用法:
    # 基础对比（1:1 映射）
    python3 compare_io.py /path/to/input /path/to/output

    # 带后缀变换（input: A.png → output: A_cleaned.png）
    python3 compare_io.py /path/to/input /path/to/output --suffix "_cleaned"

    # 扩色场景（1:N 映射，每个输入应产出 3 个变体）
    python3 compare_io.py /path/to/input /path/to/output --variants 3

    # 带前缀变换（input: A.png → output: NA_A.png）
    python3 compare_io.py /path/to/input /path/to/output --prefix "NA_"
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}


def find_images(directory: str) -> list[Path]:
    """Find all image files in directory (recursive)."""
    root = Path(directory)
    if not root.is_dir():
        print(f"ERROR: {directory} is not a valid directory", file=sys.stderr)
        sys.exit(1)

    images = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(p)
    return sorted(images)


def get_stem(filepath: Path) -> str:
    """Get filename stem (without extension)."""
    return filepath.stem


def build_expected_name(
    input_stem: str,
    input_ext: str,
    suffix: str = "",
    prefix: str = "",
    output_ext: str | None = None,
) -> str:
    """Build expected output filename from input name + transforms."""
    ext = output_ext if output_ext else input_ext
    if not ext.startswith("."):
        ext = "." + ext
    return f"{prefix}{input_stem}{suffix}{ext}"


def compare_directories(
    input_dir: str,
    output_dir: str,
    suffix: str = "",
    prefix: str = "",
    output_ext: str | None = None,
    variants: int = 1,
) -> dict:
    """Compare input and output directories.

    For variants > 1, expects output files matching pattern:
        {prefix}{input_stem}{suffix}_{variant_index}{ext}
    or any file containing the input stem.
    """
    input_images = find_images(input_dir)
    output_images = find_images(output_dir)

    # Build lookup: output stem → output paths
    output_by_name = {}
    for p in output_images:
        output_by_name[p.name.lower()] = p

    # Also build a lookup by stem for fuzzy matching
    output_by_stem = {}
    for p in output_images:
        stem = p.stem.lower()
        if stem not in output_by_stem:
            output_by_stem[stem] = []
        output_by_stem[stem].append(p)

    report = {
        "input_dir": str(Path(input_dir).resolve()),
        "output_dir": str(Path(output_dir).resolve()),
        "input_count": len(input_images),
        "output_count": len(output_images),
        "expected_variants": variants,
        "matched": [],
        "missing_output": [],
        "incomplete_variants": [],
        "orphaned_output": [],
    }

    matched_outputs = set()

    for inp in input_images:
        inp_stem = inp.stem
        inp_ext = inp.suffix

        if variants == 1:
            # 1:1 mapping — look for exact transformed name
            expected_name = build_expected_name(inp_stem, inp_ext, suffix, prefix, output_ext)
            found = output_by_name.get(expected_name.lower())

            if not found:
                # Fuzzy: look for any output containing the input stem
                expected_stem = f"{prefix}{inp_stem}{suffix}".lower()
                found_list = output_by_stem.get(expected_stem, [])
                if found_list:
                    found = found_list[0]

            if found:
                report["matched"].append({
                    "input": inp.name,
                    "output": found.name,
                })
                matched_outputs.add(str(found))
            else:
                report["missing_output"].append({
                    "input": inp.name,
                    "expected_output": expected_name,
                })
        else:
            # 1:N mapping — look for multiple variants
            found_variants = []
            inp_stem_lower = inp_stem.lower()

            for out_p in output_images:
                out_stem_lower = out_p.stem.lower()
                # Match if output name contains input stem
                # Common patterns:
                #   A_color1.png, A_color2.png
                #   A_v1.png, A_v2.png
                #   A_01.png, A_02.png
                if inp_stem_lower in out_stem_lower:
                    # Exclude exact match if suffix/prefix differ
                    found_variants.append(out_p)
                    matched_outputs.add(str(out_p))

            if not found_variants:
                report["missing_output"].append({
                    "input": inp.name,
                    "expected_variants": variants,
                    "found_variants": 0,
                })
            elif len(found_variants) < variants:
                report["incomplete_variants"].append({
                    "input": inp.name,
                    "expected_variants": variants,
                    "found_variants": len(found_variants),
                    "found_files": [p.name for p in found_variants],
                })
            else:
                report["matched"].append({
                    "input": inp.name,
                    "output_count": len(found_variants),
                    "outputs": [p.name for p in found_variants[:5]],  # cap display
                })

    # Find orphaned outputs (no corresponding input)
    for out_p in output_images:
        if str(out_p) not in matched_outputs:
            report["orphaned_output"].append(out_p.name)

    # Summary stats
    report["summary"] = {
        "matched": len(report["matched"]),
        "missing": len(report["missing_output"]),
        "incomplete": len(report["incomplete_variants"]),
        "orphaned": len(report["orphaned_output"]),
        "match_rate": f"{len(report['matched']) / len(input_images) * 100:.1f}%" if input_images else "N/A",
    }

    return report


def print_summary(report: dict) -> None:
    """Print human-readable comparison summary."""
    print("=" * 60)
    print("  COMPARE-IO  Input vs Output Report")
    print("=" * 60)
    print(f"  Input dir  : {report['input_dir']}")
    print(f"  Output dir : {report['output_dir']}")
    print(f"  Input files  : {report['input_count']}")
    print(f"  Output files : {report['output_count']}")
    if report["expected_variants"] > 1:
        print(f"  Expected variants per input: {report['expected_variants']}")

    s = report["summary"]
    print()
    print(f"  Matched      : {s['matched']} ({s['match_rate']})")
    print(f"  Missing      : {s['missing']}")
    if report["expected_variants"] > 1:
        print(f"  Incomplete   : {s['incomplete']}")
    print(f"  Orphaned     : {s['orphaned']}")

    if report["missing_output"]:
        print(f"\n  Missing outputs ({len(report['missing_output'])}):")
        for item in report["missing_output"][:15]:
            if "expected_variants" in item:
                print(f"    - {item['input']} (expected {item['expected_variants']} variants, found {item['found_variants']})")
            else:
                print(f"    - {item['input']} → expected: {item['expected_output']}")
        if len(report["missing_output"]) > 15:
            print(f"    ... and {len(report['missing_output']) - 15} more")

    if report["incomplete_variants"]:
        print(f"\n  Incomplete variants ({len(report['incomplete_variants'])}):")
        for item in report["incomplete_variants"][:10]:
            print(f"    - {item['input']}: {item['found_variants']}/{item['expected_variants']} variants")
            for f in item["found_files"][:3]:
                print(f"      found: {f}")
        if len(report["incomplete_variants"]) > 10:
            print(f"    ... and {len(report['incomplete_variants']) - 10} more")

    if report["orphaned_output"]:
        print(f"\n  Orphaned outputs ({len(report['orphaned_output'])}):")
        for f in report["orphaned_output"][:10]:
            print(f"    - {f}")
        if len(report["orphaned_output"]) > 10:
            print(f"    ... and {len(report['orphaned_output']) - 10} more")

    # Verdict
    print()
    issues = s["missing"] + s["incomplete"] + s["orphaned"]
    if issues == 0:
        print("  VERDICT: ALL INPUTS HAVE MATCHING OUTPUTS")
    else:
        print(f"  VERDICT: {issues} ISSUE(S) FOUND — review above")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Compare pipeline input vs output directories"
    )
    parser.add_argument("input_dir", help="Input directory (pipeline source)")
    parser.add_argument("output_dir", help="Output directory (pipeline result)")
    parser.add_argument("--suffix", type=str, default="", help="Output filename suffix transform (e.g. '_cleaned')")
    parser.add_argument("--prefix", type=str, default="", help="Output filename prefix transform (e.g. 'NA_')")
    parser.add_argument("--output-ext", type=str, default=None, help="Output file extension (default: same as input)")
    parser.add_argument("--variants", type=int, default=1, help="Expected output variants per input (default: 1)")
    parser.add_argument("--json", action="store_true", help="Output only JSON (no summary)")

    args = parser.parse_args()

    report = compare_directories(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        suffix=args.suffix,
        prefix=args.prefix,
        output_ext=args.output_ext,
        variants=args.variants,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_summary(report)
        # Save JSON report
        report_path = Path(args.output_dir).resolve().parent / f"compare_report_{Path(args.output_dir).name}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n  JSON report saved: {report_path}")


if __name__ == "__main__":
    main()
