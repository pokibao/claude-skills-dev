---
name: verify-pipeline
description: 验证批量流水线输出。Use when a batch pipeline finishes, after craft-pipeline/look-split/batch generation runs, when checking batch output completeness and quality, or when user says "验证流水线/检查批量/pipeline验证".
allowed-tools: Bash(python3 *), Bash(ls *), Bash(wc *), Bash(find *), Read, Glob, Grep
---

# verify-pipeline

验证批量流水线输出的完整性和质量。适用于 craft-pipeline / look-split / auto-gen-factory 等所有批量生产流水线。

## 用法

```
/verify-pipeline <输出目录>
/verify-pipeline <输出目录> --expected 75
/verify-pipeline <输出目录> --input <输入目录>
```

`$ARGUMENTS` = 流水线输出目录路径

## 五层检查框架

```
Layer 1: 文件计数        实际数量 vs 预期数量（用户提供或从输入推断）
Layer 2: 文件完整性      大小 > 10KB, PIL 可打开, 非零字节
Layer 3: 命名规范        匹配预期模式（如 Look_01_款式图.png）
Layer 4: 抽样质检        随机抽取 3-5 张图片深度检查（分辨率、白底等）
Layer 5: 差异报告        缺什么、坏什么、过了什么
```

## 命令

### 基础验证（仅检查输出目录）

```bash
/opt/homebrew/bin/python3 ~/.claude/skills/verify-pipeline/scripts/verify_batch.py \
  /path/to/output \
  --expected 75 \
  --pattern "Look_\d{2}_.*\.png"
```

参数：
- 第一个参数：输出目录路径（必填）
- `--expected N`：预期文件数量（可选，不填则仅报告实际数量）
- `--pattern REGEX`：文件名正则匹配模式（可选）
- `--min-size KB`：最小文件大小阈值，默认 10KB
- `--sample N`：抽样检查数量，默认 3

### 输入输出对比（craft-pipeline 等需要 1:N 映射的场景）

```bash
/opt/homebrew/bin/python3 ~/.claude/skills/verify-pipeline/scripts/compare_io.py \
  /path/to/input \
  /path/to/output \
  --suffix "_cleaned" \
  --variants 3
```

参数：
- 第一个参数：输入目录路径（必填）
- 第二个参数：输出目录路径（必填）
- `--suffix SUFFIX`：输出文件名后缀变换（如 `_cleaned`）
- `--variants N`：每个输入预期产出数量（如扩色 3 个变体）
- `--prefix PREFIX`：输出文件名前缀变换
- `--output-ext EXT`：输出文件扩展名（如 `.png`），默认与输入相同

## 典型流水线验证场景

### craft-pipeline 验证

```bash
# Phase 1 清洗后验证：每个输入应有 1 个清洗输出
/opt/homebrew/bin/python3 ~/.claude/skills/verify-pipeline/scripts/compare_io.py \
  /path/to/originals /path/to/cleaned --suffix "_cleaned"

# Phase 3 扩色后验证：每个输入应有 3-5 个色彩变体
/opt/homebrew/bin/python3 ~/.claude/skills/verify-pipeline/scripts/compare_io.py \
  /path/to/cleaned /path/to/variants --variants 5
```

### look-split 验证

```bash
# 75 Look 拆分验证
/opt/homebrew/bin/python3 ~/.claude/skills/verify-pipeline/scripts/verify_batch.py \
  /path/to/split_output \
  --expected 75 \
  --pattern "Look_\d{2}_.*\.png"
```

### auto-gen-factory 验证

```bash
# 批量生图验证
/opt/homebrew/bin/python3 ~/.claude/skills/verify-pipeline/scripts/verify_batch.py \
  /path/to/generated \
  --expected 150 \
  --min-size 50
```

## 输出格式

JSON 报告 + 人类可读摘要：

```json
{
  "total": 75,
  "passed": 72,
  "failed": 3,
  "missing_sequence": [14, 38],
  "corrupt": ["Look_07_款式图.png"],
  "too_small": ["Look_52_模特图.png"],
  "sample_results": [
    {"file": "Look_01_款式图.png", "resolution": "2048x2048", "size_kb": 1240, "mode": "RGB"}
  ]
}
```

## 常见陷阱

- **零字节文件**：API 超时/网络中断会产生空文件，Layer 2 检测
- **重复文件名**：不同子目录下同名文件，递归扫描时注意去重
- **格式错误**：.jpg 实际是 .png 或反过来，PIL 打开验证
- **序号断裂**：Look_01 到 Look_75 中间缺号，Layer 3 序号连续性检测
- **尺寸异常**：正常生图 > 100KB，< 10KB 大概率是错误输出
