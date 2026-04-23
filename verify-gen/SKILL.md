---
name: verify-gen
description: 验证 AI 生图输出质量。Use when images are generated, after auto-gen-factory runs, when checking white background product shots or model photos quality, or when user says "验证图片/检查输出/图片质量".
allowed-tools: Bash(python3 *), Read, Glob, Grep
---

# verify-gen: AI 生图质量验证

## 用途

验证 auto-gen-factory 输出的 AI 时尚图片是否达到生产标准。
适用于白底产品图、模特穿搭图等 Gemini Pro Image 生成的图片。

## 检查项

| 检查 | 标准 | 常见问题 |
|------|------|----------|
| 白底背景 | 四角+边缘 RGB 均值 > 245 | 灰色背景、渐变污染 |
| 分辨率 | 宽高均 >= 2048px | Gemini 降级输出 |
| 文件大小 | 100KB ~ 50MB | 空白图太小、损坏图 |
| 宽高比 | 0.5 ~ 2.0 | 异常裁切 |
| 色彩方差 | 标准差 > 10 | 纯色空白图 |

## 工作流

```
1. 定位输出目录（默认: ~/projects/「auto生图工厂」/3_outputs/）
2. 扫描 .png / .jpg / .webp 文件
3. 逐张运行 check_image.py → JSON 结果
4. batch_verify.py 汇总 → verify_report_{timestamp}.json
5. 输出摘要：通过/失败数量 + 失败原因分布
```

## 快速使用

单张验证：
```bash
/opt/homebrew/bin/python3 ~/.claude/skills/verify-gen/scripts/check_image.py /path/to/image.png
```

批量验证：
```bash
/opt/homebrew/bin/python3 ~/.claude/skills/verify-gen/scripts/batch_verify.py /path/to/output_dir/
```

指定输出报告位置：
```bash
/opt/homebrew/bin/python3 ~/.claude/skills/verify-gen/scripts/batch_verify.py /path/to/dir/ --output /path/to/report.json
```

## 最近输出文件

!"ls -lt ~/projects/「auto生图工厂」/3_outputs/ 2>/dev/null | head -5"

## Gotchas（常见失败模式）

1. **灰色背景** — Gemini 有时生成 RGB(240,240,240) 而非纯白，阈值 245 可捕获
2. **肢体裁切** — 模特图脚/手被切掉，目前靠分辨率+宽高比间接检测
3. **分辨率降级** — API 偶尔返回 1024px 而非请求的 2048+，直接 fail
4. **纯色空白图** — 生成失败返回纯白/纯黑图，色彩方差检测可捕获
5. **文件损坏** — PIL 无法打开 = 直接 fail
6. **EXIF 旋转** — 部分图片实际像素与显示不一致，脚本已处理

## 脚本详情

- `scripts/check_image.py` — 单张图片完整质检，输出 JSON
- `scripts/batch_verify.py` — 批量扫描 + 汇总报告
