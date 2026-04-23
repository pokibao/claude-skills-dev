# claude-skills-dev

Development pipeline skills for [Claude Code](https://claude.ai/code). Covers the full dev cycle: plan → build → verify.

## Structure

```
claude-skills-dev/
├── pipeline/      Build pipelines & architecture
└── verification/  Output verification
```

---

## pipeline

### [`build`](./pipeline/build/)
**Build 2** — Gated, role-based delivery pipeline. Three topologies (LIGHT / STANDARD / FULL), Harness gates, Hermes single source of truth, Memory Anchor recall and checkpoint resume. The flagship dev skill.

```
/build
```

### [`build-frontend`](./pipeline/build-frontend/)
**Frontend parallel pipeline** — Frontend PM + component architect + dev + visual QA running in parallel, sharing an API contract layer with `/build`. Embeds `/fix-frontend` repair loop.

```
/build-frontend
```

### [`fix-frontend`](./pipeline/fix-frontend/)
**Frontend bug fix loop** — Screenshot baseline → root cause → atomic fix → visual diff → regression check → experience write-back. Solves "fix A breaks B."

```
/fix-frontend
修前端
```

### [`code-contract`](./pipeline/code-contract/)
**Architecture contract generator** — Scans the project, generates module contracts (input / output / consumers / invariants), detects integration issues before they happen.

```
/code-contract
契约
```

---

## verification

### [`verify-site`](./verification/verify-site/)
**E2E site verification** — Port scan, HTTP health check, content validation, interactive element testing. Run before deploy or after a bug fix.

```
/verify-site http://localhost:3000
```

### [`verify-pipeline`](./verification/verify-pipeline/)
**Batch pipeline output verification** — Checks completeness, quality, and failure rate after a batch job finishes.

```
/verify-pipeline
```

### [`verify-gen`](./verification/verify-gen/)
**AI image quality verification** — White background compliance, product shot standards, batch pass/fail report.

```
/verify-gen
```

### [`verify-publish`](./verification/verify-publish/)
**Social publish verification** — Confirms post went live, content matches, no platform errors.

```
/verify-publish
```

---

## Installation

```bash
# Clone and copy the skills you need
git clone https://github.com/pokibao/claude-skills-dev
cp -r claude-skills-dev/pipeline/build ~/.claude/skills/
cp -r claude-skills-dev/verification/verify-site ~/.claude/skills/
```

## Related Repos

- [claude-skills-ai-quality](https://github.com/pokibao/claude-skills-ai-quality) — pua, ahvs, semantic-master, model-route, memory-audit, ai-brainstorm, ai-debate
- [claude-skills-ops](https://github.com/pokibao/claude-skills-ops) — chain, drift-check, pulse, cold-eye, daily-digest

## Dependencies

- [Claude Code](https://claude.ai/code)
- [Memory Anchor](https://github.com/pokibao/memory-anchor) — required for `build` full functionality

## License

MIT
