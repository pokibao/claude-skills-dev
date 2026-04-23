#!/usr/bin/env /opt/homebrew/bin/python3
"""
port_scanner.py - Scan common dev ports and detect running web services.

Usage:
    python3 port_scanner.py                    # Scan default ports
    python3 port_scanner.py 3000 8000 8080     # Scan specific ports
    python3 port_scanner.py --all              # Scan extended port range

Output: JSON with detected services, framework, and page title.
"""

import json
import socket
import sys
import time

import httpx

# Default ports commonly used in web development
DEFAULT_PORTS = [
    3000,   # React CRA, Express, Next.js
    3001,   # React CRA (secondary), Vite preview
    3002,   # Misc dev server
    3100,   # Paperclip
    4200,   # Angular CLI
    5000,   # Flask, generic Python
    5173,   # Vite dev server
    5180,   # auto-gen-factory frontend
    8000,   # FastAPI, Django, generic Python
    8080,   # Generic HTTP, Spring Boot
    8888,   # Jupyter, misc
    9000,   # PHP-FPM, SonarQube, misc
]

# Extended ports for --all mode
EXTENDED_PORTS = DEFAULT_PORTS + [
    1234,   # Parcel
    3333,   # AdonisJS
    4000,   # Phoenix (Elixir)
    4173,   # Vite preview
    5001,   # Flask secondary
    5500,   # Live Server (VS Code)
    5555,   # Prisma Studio
    6006,   # Storybook
    6379,   # Redis (not HTTP but good to know)
    7860,   # Gradio
    8001,   # Secondary backend
    8081,   # Generic
    8443,   # HTTPS alt
    8899,   # Heartbeat web
    9090,   # Prometheus
    18060,  # xiaohongshu-mcp
    54329,  # PGlite
]

# Framework detection patterns in HTML body
BODY_PATTERNS = {
    "__vite_plugin_react": "Vite+React",
    "__vite": "Vite",
    '<div id="root"': "React",
    '<div id="app"': "Vue",
    '<div id="__next"': "Next.js",
    '<div id="__nuxt"': "Nuxt.js",
    "ng-version": "Angular",
    "_next/static": "Next.js",
    "/_nuxt/": "Nuxt.js",
    "Swagger UI": "FastAPI (Swagger)",
    '"openapi"': "FastAPI/OpenAPI",
    "Gradio": "Gradio",
    "Streamlit": "Streamlit",
    "Jupyter": "Jupyter",
}

# Framework detection from response headers
HEADER_PATTERNS = {
    "x-powered-by": {
        "express": "Express",
        "next.js": "Next.js",
        "nuxt": "Nuxt.js",
        "php": "PHP",
    },
    "server": {
        "uvicorn": "FastAPI/Uvicorn",
        "hypercorn": "FastAPI/Hypercorn",
        "gunicorn": "Gunicorn",
        "nginx": "Nginx",
        "apache": "Apache",
        "next.js": "Next.js",
        "werkzeug": "Flask/Werkzeug",
        "tornado": "Tornado",
    },
}


def is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Quick TCP connect check."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


def detect_framework_from_headers(headers: httpx.Headers) -> str | None:
    """Detect framework from HTTP response headers."""
    for header_name, patterns in HEADER_PATTERNS.items():
        value = headers.get(header_name, "").lower()
        if value:
            for pattern, framework in patterns.items():
                if pattern in value:
                    return framework
    return None


def detect_framework_from_body(body: str) -> str | None:
    """Detect framework from HTML body content."""
    for pattern, framework in BODY_PATTERNS.items():
        if pattern in body:
            return framework
    return None


def extract_title(body: str) -> str | None:
    """Extract <title> from HTML."""
    lower = body.lower()
    start = lower.find("<title>")
    if start == -1:
        return None
    start += len("<title>")
    end = lower.find("</title>", start)
    if end == -1:
        return None
    title = body[start:end].strip()
    return title if title else None


def probe_service(client: httpx.Client, port: int, host: str = "localhost") -> dict | None:
    """Probe a port with HTTP GET and gather info."""
    url = f"http://{host}:{port}/"
    result = {
        "port": port,
        "status": "open",
        "framework": None,
        "title": None,
        "status_code": None,
        "response_time_ms": None,
        "content_type": None,
        "server_header": None,
        "error": None,
    }

    try:
        start = time.monotonic()
        resp = client.get(url, follow_redirects=True, timeout=5.0)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)

        result["status_code"] = resp.status_code
        result["response_time_ms"] = elapsed_ms
        result["content_type"] = resp.headers.get("content-type", "")
        result["server_header"] = resp.headers.get("server")

        body = resp.text[:5000]  # Only need first 5KB for detection

        # Detect framework
        fw = detect_framework_from_headers(resp.headers)
        if not fw:
            fw = detect_framework_from_body(body)
        result["framework"] = fw

        # Extract title
        result["title"] = extract_title(body)

        # If it's a JSON response (likely API), try to get some info
        if "application/json" in result["content_type"]:
            try:
                data = resp.json()
                if isinstance(data, dict):
                    # Use a meaningful field as title if no HTML title
                    for key in ("name", "title", "service", "app", "message"):
                        if key in data:
                            result["title"] = str(data[key])
                            break
            except Exception:
                pass

    except httpx.ConnectError:
        # Port is open (TCP) but HTTP failed - might be non-HTTP service
        result["status"] = "open_non_http"
        result["error"] = "connection_refused_http"
    except httpx.TimeoutException:
        result["status"] = "open_slow"
        result["error"] = "http_timeout"
    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    # Parse arguments
    use_extended = "--all" in sys.argv
    custom_ports = []
    for arg in sys.argv[1:]:
        if arg == "--all":
            continue
        try:
            custom_ports.append(int(arg))
        except ValueError:
            print(f"Warning: ignoring invalid port '{arg}'", file=sys.stderr)

    if custom_ports:
        ports = sorted(set(custom_ports))
    elif use_extended:
        ports = sorted(set(EXTENDED_PORTS))
    else:
        ports = DEFAULT_PORTS

    # Phase 1: Quick TCP scan to find open ports
    open_ports = []
    for port in ports:
        if is_port_open("localhost", port):
            open_ports.append(port)

    if not open_ports:
        output = {
            "services": [],
            "summary": {
                "ports_scanned": len(ports),
                "services_found": 0,
                "message": "No services detected on scanned ports.",
            },
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    # Phase 2: HTTP probe open ports
    services = []
    with httpx.Client() as client:
        for port in open_ports:
            result = probe_service(client, port)
            if result:
                services.append(result)

    # Build output
    output = {
        "services": services,
        "summary": {
            "ports_scanned": len(ports),
            "services_found": len(services),
            "http_ok": sum(1 for s in services if s.get("status_code") and 200 <= s["status_code"] < 400),
            "frameworks_detected": [
                s["framework"] for s in services if s.get("framework")
            ],
        },
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
