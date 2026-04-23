---
name: verify-site
description: 网站 E2E 验证。Use before deploying web apps, when testing if a site works correctly, when checking pages load and interactive elements function, or when user says "验证网站/测试站点/E2E测试/网站能跑吗".
allowed-tools: Bash(curl *), Bash(python3 *), Bash(npx *), Read, Glob, Grep
---

# verify-site - 网站 E2E 验证 Skill

## Purpose

End-to-end verification of web applications before deployment. Checks health, page content, API endpoints, responsive rendering, performance, and console errors.

## Usage

```
/verify-site                          # Auto-detect running services
/verify-site http://localhost:5180    # Test specific URL
/verify-site http://localhost:5180 http://localhost:8000  # Test multiple
```

`$ARGUMENTS` = URL(s) to test. If empty, auto-detect running services.

## Auto-Detection

Scan for running dev services on common ports:

```bash
lsof -i -P | grep LISTEN | grep -E '(node|python|next|vite)' | head -10
```

Port scanner script for detailed detection:

```bash
python3 ~/.claude/skills/verify-site/scripts/port_scanner.py
```

Common dev ports checked: 3000, 3001, 3002, 4200, 5000, 5173, 5180, 8000, 8080, 8888, 9000.

## Verification Layers

Execute these layers **in order**. Stop early if Layer 1 fails (service down).

### Layer 1: Health Check (curl)

Check each endpoint returns HTTP 200.

```bash
python3 ~/.claude/skills/verify-site/scripts/health_check.py <base_url>
```

The script tests:
- `GET /` - main page loads
- `GET /health` - health endpoint (if exists)
- `GET /api/health` - API health (if exists)
- Measures response time for each
- Outputs JSON with overall status: `healthy` / `degraded` / `down`

Manual fallback:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5180/
```

### Layer 2: Page Load Verification

Verify HTML contains expected structural elements:

```bash
curl -s http://localhost:5180/ | grep -c '<div id="root"\|<div id="app"\|<main\|<body'
```

For React apps, check the JS bundle loads:
```bash
curl -s http://localhost:5180/ | grep -c 'src=.*\.js'
```

For API backends (FastAPI/Express):
```bash
curl -s http://localhost:8000/docs  # FastAPI Swagger
curl -s http://localhost:8000/openapi.json | python3 -m json.tool | head -20
```

### Layer 3: API Endpoint Testing

Test key API routes. Adapt based on project:

```bash
# FastAPI health
curl -s http://localhost:8000/health | python3 -m json.tool

# Common API patterns
curl -s http://localhost:8000/api/v1/status
curl -s -X POST http://localhost:8000/api/v1/generate -H "Content-Type: application/json" -d '{"test": true}'
```

For the auto-gen-factory project specifically:
```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/models
```

### Layer 4: Responsive Check (Playwright MCP)

If `mcp__MCP_DOCKER__browser_*` tools are available, use them for viewport testing:

1. Navigate to the URL:
   - Use `mcp__MCP_DOCKER__browser_navigate` with the target URL
2. Take desktop screenshot (1920x1080):
   - Use `mcp__MCP_DOCKER__browser_resize` to set viewport
   - Use `mcp__MCP_DOCKER__browser_take_screenshot`
3. Take mobile screenshot (375x667 iPhone SE):
   - Use `mcp__MCP_DOCKER__browser_resize` to 375x667
   - Use `mcp__MCP_DOCKER__browser_take_screenshot`
4. Check for layout overflow or broken elements via snapshot:
   - Use `mcp__MCP_DOCKER__browser_snapshot`

If Playwright MCP is not available, fall back to curl with User-Agent:
```bash
curl -s -A "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)" http://localhost:5180/ | head -50
```

### Layer 5: Performance (TTFB)

Measure Time to First Byte using curl timing:

```bash
curl -s -o /dev/null -w "TTFB: %{time_starttransfer}s\nTotal: %{time_total}s\nHTTP: %{http_code}\nSize: %{size_download} bytes\n" http://localhost:5180/
```

**Thresholds**:
| Metric | Good | Acceptable | Bad |
|--------|------|------------|-----|
| TTFB | < 200ms | < 500ms | > 500ms |
| Total | < 1s | < 3s | > 3s |

### Layer 6: Console Errors (Playwright MCP)

If Playwright MCP is available:

1. Navigate to the page
2. Use `mcp__MCP_DOCKER__browser_console_messages` to capture JS console output
3. Filter for `error` and `warning` level messages
4. Report any JS errors that indicate broken functionality

If Playwright MCP is not available, skip this layer and note it in the report.

## Output Format

After all layers complete, produce a summary table:

```
=== E2E Verification Report ===
Target: http://localhost:5180 (React/Vite frontend)
        http://localhost:8000 (FastAPI backend)

| Layer | Check | Status | Details |
|-------|-------|--------|---------|
| 1 | Health: :5180 | PASS | 200 OK, 45ms |
| 1 | Health: :8000 | PASS | 200 OK, 12ms |
| 2 | Page load | PASS | HTML has #root, 2 JS bundles |
| 3 | API /health | PASS | {"status":"ok"} |
| 3 | API /docs | PASS | Swagger UI loads |
| 4 | Desktop 1920x1080 | PASS | No overflow |
| 4 | Mobile 375x667 | WARN | Horizontal scroll detected |
| 5 | TTFB :5180 | PASS | 89ms |
| 5 | TTFB :8000 | PASS | 8ms |
| 6 | Console errors | PASS | 0 errors, 2 warnings |

Overall: PASS (1 warning)
```

## Gotchas

- **Services not started**: Run auto-detection first. If nothing found, remind user to start services (`./start_services.sh` for auto-gen-factory).
- **Wrong port**: Vite dev server defaults to 5173 but auto-gen-factory uses 5180. Always check actual config.
- **CORS issues**: API calls from browser may fail due to CORS even if curl works. Note this in the report.
- **Dev vs Prod differences**: Dev mode has HMR, source maps, no minification. Prod build (`npm run build && npm run preview`) may behave differently.
- **Playwright MCP not running**: Fall back gracefully to curl-only checks. Note reduced coverage in report.
- **macOS firewall**: May block port scanning. Use `lsof` instead of raw socket scanning for reliability.

## Integration with Projects

### auto-gen-factory (React :5180 + FastAPI :8000)

```bash
# Start services first
cd ~/projects/your-project && ./start_services.sh

# Then verify
/verify-site http://localhost:5180 http://localhost:8000
```

Expected endpoints:
- Frontend: `/` (React app with #root)
- Backend: `/health`, `/docs`, `/api/models`, `/api/v1/generate`

### General React + API pattern

```bash
/verify-site http://localhost:3000 http://localhost:8000
```
