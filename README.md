# Claude Code Skills

Battle-tested skills for [Claude Code](https://claude.ai/code). Built around three principles: gated pipelines, self-evolving memory, and AI quality control.

## Structure

```
claude-code-skills/
├── pipeline/          # Development pipelines
├── quality-control/   # AI behavior control
├── verification/      # Output verification
├── system-ops/        # Session & workflow management
└── intelligence/      # Decision & analysis tools
```

## Installation

Copy a skill to your skills directory:

```bash
cp -r pipeline/build ~/.claude/skills/
```

Then invoke it in Claude Code:

```
/build
```

---

## pipeline — Development Pipelines

### [`build`](./pipeline/build/)
**Build 2** — Gated, role-based delivery pipeline. Harness (gates + evidence + degradation chain) × Hermes (single source of truth + skill orchestration) × Memory Anchor (recall + checkpoint resume). Three topologies: LIGHT / STANDARD / FULL.

### [`build-frontend`](./pipeline/build-frontend/)
**Frontend parallel pipeline** — Frontend PM + component architect + dev + visual QA, sharing an API contract layer with `/build`. Embeds `/fix-frontend` repair loop.

### [`fix-frontend`](./pipeline/fix-frontend/)
**Frontend bug fix loop** — Screenshot baseline → root cause diagnosis → atomic fix → visual diff → regression check → experience write-back. Solves "fix A breaks B."

### [`code-contract`](./pipeline/code-contract/)
**Architecture contract generator** — Scans the project, generates module contracts, detects integration issues before they happen. Answers: what does each module expect, what does it return, who calls it.

---

## quality-control — AI Behavior Control

### [`pua`](./quality-control/pua/)
**Anti-AI-laziness detector** — 7 mental models distilled from 8000+ words of Claude Code issue reports and arxiv papers. Detects: read-discipline collapse, ask-instead-of-think, simplest-path bias, skip-hard-parts, fabricated verification, premature stop, fluent nonsense. Self-activating.

### [`ahvs`](./quality-control/ahvs/)
**Anti-Hallucination Verification System v2.1** — Static fact check (v1) + temporal causal reasoning (v2) + perspective shift (v2.1). Answers: is it right, why, what would invalidate it, what to watch.

### [`semantic-master`](./quality-control/semantic-master/)
**Semantic understanding system** — Adaptive depth parsing on first call, reflective enhancement mode on re-call. For "do you understand?" moments before high-stakes actions.

### [`model-route`](./quality-control/model-route/)
**Model routing guide** — When to use Opus vs Sonnet vs Haiku. Decision tree by task type: exploration, implementation, production incident, analysis.

---

## verification — Output Verification

### [`verify-site`](./verification/verify-site/)
**E2E site verification** — Port scan, HTTP health check, content validation, interactive element testing. Runs before deploy or after a bug fix.

### [`verify-pipeline`](./verification/verify-pipeline/)
**Batch pipeline output verification** — Checks completeness, quality, and failure rate after a batch job finishes. Works with image generation, data processing, or any bulk operation.

### [`verify-gen`](./verification/verify-gen/)
**AI image quality verification** — White background compliance, product shot standards, batch pass/fail report.

### [`verify-publish`](./verification/verify-publish/)
**Social publish verification** — Confirms post went live on Xiaohongshu or Instagram, content matches, no platform errors.

---

## system-ops — Session & Workflow Management

### [`chain`](./system-ops/chain/)
**Multi-step workflow tracker** — Create, advance, block, resume, and complete chains across sessions. Persists state so long workflows survive context resets.

### [`drift-check`](./system-ops/drift-check/)
**Drift detector** — Checks whether current work is still aligned with the north-star goal. Run when deep in execution and unsure if the work still matters.

### [`pulse`](./system-ops/pulse/)
**Daily ops dashboard** — Aggregates session data, detects stalls, produces weekly summaries. Answers: what got done, what's stuck, where did time go.

### [`memory-audit`](./system-ops/memory-audit/)
**Memory audit and evolution** — Detects contradictions, prunes stale knowledge, surfaces forgotten context. Inspired by OpenAEON Dreaming Mode.

---

## intelligence — Decision & Analysis

### [`cold-eye`](./intelligence/cold-eye/)
**Brutally realistic viability judgment** — Applies a fixed market-reality harness instead of encouragement. For evaluating projects, plans, or ideas without bias. No cheerleading.

### [`daily-digest`](./intelligence/daily-digest/)
**Information digestion engine** — Fetches articles, extracts comments, cross-references against memory, performs competitive teardown, writes back learnings. Multi-platform.

---

## Dependencies

- [Claude Code](https://claude.ai/code)
- [Memory Anchor](https://github.com/pokibao/memory-anchor) — required for `build`, `chain`, `pulse`, `memory-audit` full functionality

## License

MIT
