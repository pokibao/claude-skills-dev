#!/usr/bin/env /opt/homebrew/bin/python3
"""
health_check.py - Web application health check with endpoint testing.

Usage:
    python3 health_check.py <base_url> [additional_paths...]

Examples:
    python3 health_check.py http://localhost:5180
    python3 health_check.py http://localhost:8000 /api/v1/models /api/v1/status

Output: JSON with endpoint results and overall health status.
"""

import json
import sys
import time
from urllib.parse import urljoin

import httpx

# Default paths to check for every service
DEFAULT_PATHS = [
    "/",
    "/health",
    "/api/health",
]

# Additional paths to probe (checked only if they return non-404)
PROBE_PATHS = [
    "/docs",              # FastAPI Swagger
    "/openapi.json",      # FastAPI OpenAPI spec
    "/api/v1/status",     # Common API status
    "/api/models",        # auto-gen-factory specific
    "/favicon.ico",       # Static asset sanity
]

# Markers that indicate a page loaded correctly
HTML_MARKERS = [
    '<div id="root"',     # React (CRA / Vite)
    '<div id="app"',      # Vue
    '<div id="__next"',   # Next.js
    "<main",              # Semantic HTML
    "<body",              # Any HTML page
    "<!doctype html",     # HTML doctype (case-insensitive checked separately)
    "<!DOCTYPE html",
]

# Markers for known frameworks in response headers or body
FRAMEWORK_HINTS = {
    "x-powered-by: express": "Express",
    "server: uvicorn": "FastAPI/Uvicorn",
    "server: hypercorn": "FastAPI/Hypercorn",
    "server: next.js": "Next.js",
    '"openapi"': "FastAPI",
    "vite": "Vite",
    "__vite_plugin_react": "Vite+React",
    "__next": "Next.js",
    "nuxt": "Nuxt.js",
}


def check_endpoint(client: httpx.Client, base_url: str, path: str) -> dict:
    """Check a single endpoint. Returns result dict."""
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    result = {
        "path": path,
        "url": url,
        "status_code": None,
        "response_time_ms": None,
        "body_preview": None,
        "content_type": None,
        "body_length": None,
        "has_content": False,
        "error": None,
    }

    try:
        start = time.monotonic()
        resp = client.get(url, follow_redirects=True, timeout=10.0)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)

        result["status_code"] = resp.status_code
        result["response_time_ms"] = elapsed_ms
        result["content_type"] = resp.headers.get("content-type", "")

        body = resp.text
        result["body_length"] = len(body)
        result["has_content"] = len(body.strip()) > 0

        # Body preview: first 300 chars, cleaned up
        preview = body[:300].replace("\n", " ").replace("\r", "").strip()
        if len(body) > 300:
            preview += "..."
        result["body_preview"] = preview

    except httpx.ConnectError:
        result["error"] = "connection_refused"
    except httpx.TimeoutException:
        result["error"] = "timeout"
    except Exception as e:
        result["error"] = str(e)

    return result


def detect_framework(results: list[dict]) -> str | None:
    """Try to detect the framework from response content."""
    for r in results:
        if r.get("body_preview") is None:
            continue
        combined = (r.get("body_preview", "") + " " + r.get("content_type", "")).lower()
        for hint, framework in FRAMEWORK_HINTS.items():
            if hint.lower() in combined:
                return framework
    return None


def check_html_structure(body_preview: str) -> list[str]:
    """Check which HTML markers are present in the body."""
    if not body_preview:
        return []
    found = []
    lower = body_preview.lower()
    for marker in HTML_MARKERS:
        if marker.lower() in lower:
            found.append(marker)
    return found


def compute_overall(results: list[dict]) -> str:
    """Determine overall health: healthy / degraded / down.

    Logic:
    - If ALL endpoints have connection errors -> down
    - If any endpoint returns 5xx -> degraded
    - For API backends (FastAPI etc), root / returning 404 is normal;
      check /health, /api/health, /docs instead
    - If at least one meaningful endpoint returns 200 -> healthy or degraded
    """
    if not results:
        return "down"

    # Check if anything is reachable at all
    connection_errors = sum(1 for r in results if r.get("error") in ("connection_refused", "timeout", "connect_timeout"))
    if connection_errors == len(results):
        return "down"

    # Count by category across ALL results (not just defaults)
    all_status: list[int] = [r["status_code"] for r in results if r.get("status_code") is not None]
    success_count = sum(1 for s in all_status if 200 <= s < 400)
    server_error_count = sum(1 for s in all_status if s >= 500)
    not_found_count = sum(1 for s in all_status if s == 404)
    error_count = sum(1 for r in results if r.get("error"))

    # If there are 5xx errors, at best degraded
    if server_error_count > 0:
        if success_count > 0:
            return "degraded"
        return "down"

    # If we have successful endpoints, service is up
    if success_count > 0 and error_count == 0:
        return "healthy"

    if success_count > 0:
        return "degraded"

    # Everything is 404 or 4xx but server responds (e.g., API with no root route)
    # If the server is responding with structured errors, it's running but misconfigured
    if not_found_count > 0 and error_count == 0:
        return "degraded"

    return "down"


def main():
    if len(sys.argv) < 2:
        print("Usage: health_check.py <base_url> [additional_paths...]", file=sys.stderr)
        print("Example: health_check.py http://localhost:5180", file=sys.stderr)
        sys.exit(1)

    base_url = sys.argv[1]
    extra_paths = sys.argv[2:] if len(sys.argv) > 2 else []

    # Ensure base_url has a scheme
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = "http://" + base_url

    # Build path list: defaults + probes + user-specified extras
    paths_to_check = list(DEFAULT_PATHS)
    paths_to_check.extend(PROBE_PATHS)
    for p in extra_paths:
        if not p.startswith("/"):
            p = "/" + p
        if p not in paths_to_check:
            paths_to_check.append(p)

    results = []
    with httpx.Client() as client:
        for path in paths_to_check:
            result = check_endpoint(client, base_url, path)
            results.append(result)

    # Separate default results (always shown) from probe results (only shown if useful)
    default_set = set(DEFAULT_PATHS) | set(extra_paths)
    default_results = [r for r in results if r["path"] in default_set or (
        r.get("status_code") is not None and r["status_code"] != 404
    )]

    # Filter out 404 probe results (they just add noise)
    filtered = [
        r for r in results
        if r["path"] in default_set
        or r.get("error") is not None
        or (r.get("status_code") is not None and r["status_code"] != 404)
    ]

    overall = compute_overall(results)
    framework = detect_framework(results)

    # HTML structure check on root
    root_result = next((r for r in results if r["path"] == "/"), None)
    html_markers = []
    if root_result and root_result.get("body_preview"):
        html_markers = check_html_structure(root_result["body_preview"])

    output = {
        "url": base_url,
        "status": overall,
        "framework": framework,
        "html_markers": html_markers,
        "endpoints": filtered,
        "summary": {
            "total_checked": len(results),
            "total_shown": len(filtered),
            "success": sum(1 for r in filtered if r.get("status_code") and 200 <= r["status_code"] < 400),
            "errors": sum(1 for r in filtered if r.get("error")),
            "not_found": sum(1 for r in results if r.get("status_code") == 404),
        },
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
