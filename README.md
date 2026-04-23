# Claude Code Skills — Dev & System Execution

A collection of battle-tested Claude Code skills for software development workflows, AI quality control, and system operations.

These skills are designed for [Claude Code](https://claude.ai/code) — Anthropic's official CLI.

## Installation

```bash
# Install a skill
claude skill add <skill-name> --path ./skill-name

# Or copy directly to your skills directory
cp -r <skill-name> ~/.claude/skills/
```

## Skills

### Core Build Pipeline

| Skill | Description |
|-------|-------------|
| [`build`](./build/) | Build 2 — gated role-based delivery pipeline with Memory Anchor recall, Harness + Hermes integration |
| [`build-frontend`](./build-frontend/) | Frontend parallel pipeline — PM + architect + dev + visual QA, shares API contract layer with `/build` |
| [`fix-frontend`](./fix-frontend/) | Frontend bug fix loop — screenshot baseline → root cause → atomic fix → visual diff → regression check |
| [`code-contract`](./code-contract/) | Architecture contracts — scan project, generate module contracts, detect integration issues before they happen |

### AI Quality Control

| Skill | Description |
|-------|-------------|
| [`pua`](./pua/) | Anti-AI-laziness detector — 7 mental models (read-discipline collapse, premature stop, fabricated verification, etc.) with self-activation |
| [`ahvs`](./ahvs/) | Anti-Hallucination Verification System v2.1 — temporal causal reasoning + perspective shift |
| [`semantic-master`](./semantic-master/) | Semantic understanding system — adaptive depth parsing, iterative refinement mode |
| [`model-route`](./model-route/) | Model routing decision guide — Opus vs Sonnet vs Haiku by task type |

### Verification Family

| Skill | Description |
|-------|-------------|
| [`verify-site`](./verify-site/) | E2E site verification — port scan, health check, content validation, interactive element testing |
| [`verify-pipeline`](./verify-pipeline/) | Batch pipeline output verification — completeness, quality, failure detection |
| [`verify-gen`](./verify-gen/) | AI-generated image quality verification — white background, product shot standards |
| [`verify-publish`](./verify-publish/) | Social media publish verification — post went live, content matches, no errors |

### System Operations

| Skill | Description |
|-------|-------------|
| [`chain`](./chain/) | Multi-step workflow tracker — create, advance, block, resume across sessions |
| [`drift-check`](./drift-check/) | Drift detection — checks if current work is aligned with north star goal |
| [`pulse`](./pulse/) | Daily ops dashboard — session aggregation, stall detection, weekly summary |
| [`memory-audit`](./memory-audit/) | Memory audit and evolution — detect contradictions, prune stale knowledge |

### Intelligence Tools

| Skill | Description |
|-------|-------------|
| [`cold-eye`](./cold-eye/) | Brutally realistic viability judgment — market reality harness, no encouragement bias |
| [`daily-digest`](./daily-digest/) | Information digestion engine — multi-platform article fetch + competitive analysis + self-evolution |

## Design Philosophy

These skills follow three principles:

1. **Harness over hope** — every skill has gates, fallbacks, and explicit failure modes
2. **Hermes self-evolution** — skills learn from usage and write back to evolution files
3. **Memory Anchor integration** — decisions and outcomes flow into persistent memory

## Skill Format

Each skill is a markdown file with YAML frontmatter:

```yaml
---
name: skill-name
description: When to use this skill
triggers:
  - /skill-name
  - keyword trigger
---
```

## Requirements

- [Claude Code](https://claude.ai/code) CLI
- [Memory Anchor](https://github.com/pokibao/memory-anchor) MCP (for full functionality)

## License

MIT
