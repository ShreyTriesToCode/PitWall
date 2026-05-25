"""FIA decision-document fetch helpers with deterministic 403 handling."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import requests

from pitwall.config import fia_document_settings


def fia_document_headers(source_url: str | None = None) -> dict[str, str]:
    settings = fia_document_settings()
    return {
        "User-Agent": settings["user_agent"],
        "Accept": "application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": settings["referer"],
    }


def fetch_fia_document_text(
    document: dict[str, Any],
    text_path: str | Path,
    parsed_path: str | Path,
    pdf_path: str | Path,
    *,
    extract_pdf_text: Callable[[bytes], str],
    strip_html: Callable[[str], str],
    keep_pdf: bool = False,
    timeout: int = 45,
    strict_downloads: bool | None = None,
) -> dict[str, Any]:
    text_path = Path(text_path)
    parsed_path = Path(parsed_path)
    pdf_path = Path(pdf_path)
    source_url = document.get("source_url")
    settings = fia_document_settings()
    if strict_downloads is None:
        strict_downloads = bool(settings["strict_downloads"])
    if not source_url:
        return {"text": None, "parse_status": "missing_url", "cache_status": "miss", "http_status": None, "error": "fia_document_source_url_missing"}

    response = requests.get(source_url, headers=fia_document_headers(source_url), timeout=timeout)
    status_code = response.status_code
    if status_code in {403, 404}:
        status_name = "forbidden" if status_code == 403 else "not_found"
        error = f"fia_document_{status_name}:{status_code}"
        if text_path.exists():
            return {
                "text": text_path.read_text(encoding="utf-8"),
                "parse_status": f"stale_cache_{status_name}",
                "cache_status": "stale",
                "http_status": status_code,
                "error": error,
                "local_parsed_json_path": str(parsed_path) if parsed_path.exists() else None,
            }
        if strict_downloads:
            raise RuntimeError(error)
        return {"text": None, "parse_status": status_name, "cache_status": "miss", "http_status": status_code, "error": error}

    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    is_pdf = "pdf" in content_type or str(source_url).lower().endswith(".pdf")
    if is_pdf:
        if keep_pdf:
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            pdf_path.write_bytes(response.content)
        text = extract_pdf_text(response.content)
    else:
        text = strip_html(response.text)
    return {"text": text, "parse_status": "downloaded", "cache_status": "miss", "http_status": status_code, "error": None}
