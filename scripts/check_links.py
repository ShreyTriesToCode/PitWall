#!/usr/bin/env python3
"""Lightweight PitWall link checker.

By default this performs offline checks only: malformed URLs and internal app
routes. Use `--check-external` for bounded HTTP checks.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SCAN_GLOBS = ["*.md", "docs/**/*.md", "frontend/app/**/*.jsx", "frontend/app/**/*.js", ".github/workflows/*.yml"]
SKIP_DIR_PARTS = {".git", ".next", ".venv", "node_modules", "test-results", "__pycache__"}
KNOWN_OPTIONAL_DOMAINS = {"api.openf1.org", "livetiming.formula1.com", "www.fia.com", "formula1.com", "www.formula1.com"}


@dataclass(frozen=True)
class LinkFinding:
    path: Path
    link: str
    status: str
    detail: str


MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
HTML_HREF_RE = re.compile(r"""(?:href|src)=["']([^"']+)["']""")
NEXT_HREF_RE = re.compile(r"""href=\{?`([^`]+)`\}?|href=\{?["']([^"']+)["']\}?""")


def should_scan(path: Path) -> bool:
    return not any(part in SKIP_DIR_PARTS for part in path.parts)


def iter_files(root: Path = ROOT) -> list[Path]:
    files: set[Path] = set()
    for pattern in SCAN_GLOBS:
        files.update(path for path in root.glob(pattern) if path.is_file() and should_scan(path))
    return sorted(files)


def extract_links(text: str) -> list[str]:
    links: list[str] = []
    links.extend(match.group(1).strip() for match in MARKDOWN_LINK_RE.finditer(text))
    links.extend(match.group(1).strip() for match in HTML_HREF_RE.finditer(text))
    for match in NEXT_HREF_RE.finditer(text):
        link = (match.group(1) or match.group(2) or "").strip()
        if link:
            links.append(link)
    return [link for link in links if link and not link.startswith("#") and not link.startswith("mailto:")]


def app_routes(root: Path = ROOT) -> set[str]:
    routes = {"/"}
    app = root / "frontend" / "app"
    for page in app.glob("**/page.jsx"):
        rel = page.relative_to(app).parent
        route = "/" + str(rel).replace("\\", "/")
        route = "/" if route == "/." else route
        if "[" not in route:
            routes.add(route.rstrip("/") or "/")
    for route in (root / "frontend" / "app" / "api").glob("**/route.js"):
        rel = route.relative_to(app).parent
        api_route = "/" + str(rel).replace("\\", "/")
        if "[" not in api_route:
            routes.add(api_route.rstrip("/") or "/")
    return routes


def normalize_internal_route(link: str) -> str | None:
    if not link.startswith("/") or link.startswith("//"):
        return None
    path = urlparse(link).path.rstrip("/") or "/"
    if path.startswith("/api/local-data"):
        return "/api/local-data"
    return path


def check_external(link: str, timeout: float) -> tuple[str, str]:
    parsed = urlparse(link)
    if parsed.hostname in KNOWN_OPTIONAL_DOMAINS:
        return "warn", "known optional/rate-limited source skipped"
    for method in ["HEAD", "GET"]:
        request = Request(link, method=method, headers={"User-Agent": "pitwall-link-check/1.0"})
        try:
            with urlopen(request, timeout=timeout) as response:
                if response.status < 400:
                    return "ok", f"HTTP {response.status}"
                return "error", f"HTTP {response.status}"
        except HTTPError as error:
            if method == "HEAD" and error.code in {403, 405}:
                continue
            return ("warn" if error.code in {401, 403, 429} else "error"), f"HTTP {error.code}"
        except (URLError, TimeoutError) as error:
            return "warn", str(error)
    return "warn", "external check inconclusive"


def check_links(*, root: Path = ROOT, check_external_links: bool = False, timeout: float = 5.0) -> list[LinkFinding]:
    findings: list[LinkFinding] = []
    routes = app_routes(root)
    for path in iter_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for link in extract_links(text):
            parsed = urlparse(link)
            if parsed.scheme in {"http", "https"}:
                if not parsed.netloc:
                    findings.append(LinkFinding(path, link, "error", "malformed URL"))
                elif check_external_links:
                    status, detail = check_external(link, timeout)
                    if status != "ok":
                        findings.append(LinkFinding(path, link, status, detail))
                continue
            route = normalize_internal_route(link)
            if route and route not in routes:
                findings.append(LinkFinding(path, link, "error", f"internal route {route} is missing"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-external", action="store_true", help="Run bounded HTTP checks for external links.")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    findings = check_links(check_external_links=args.check_external, timeout=args.timeout)
    errors = [finding for finding in findings if finding.status == "error"]
    for finding in findings:
        rel = finding.path.relative_to(ROOT)
        print(f"{finding.status.upper()}: {rel}: {finding.link} - {finding.detail}")
    if errors:
        print(f"Link check failed with {len(errors)} error(s).")
        return 1
    print(f"Link check passed with {len(findings)} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
