"""Trust-aware FIA document source resolver.

The resolver indexes real document links only. Summary text can be retained as
context, but it is never promoted into an official FIA document.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin, urlparse


OFFICIAL_AUTHORITIES = {"official_fia", "official_fia_event_page", "official_fia_archive_api"}
THIRD_PARTY_INDEX = "third_party_official_doc_index"
SUMMARY_ONLY = "third_party_summary"
REGULATION_MIRROR = "regulation_pdf_mirror"
VERIFIED_CACHE = "verified_cache"
UNAVAILABLE = "unavailable"


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_slug(value: str | None) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower())
    return text.strip("-") or "season"


def is_fia_url(url: str | None) -> bool:
    host = urlparse(str(url or "")).netloc.lower()
    return host == "fia.com" or host.endswith(".fia.com")


def is_pdf_like(url: str | None, content_type: str | None = None) -> bool:
    return "pdf" in str(content_type or "").lower() or str(url or "").lower().split("?", 1)[0].endswith(".pdf")


def looks_like_html_error(content: bytes, content_type: str | None = None) -> bool:
    prefix = (content or b"")[:512].lstrip().lower()
    if "html" in str(content_type or "").lower():
        return True
    return prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html") or b"<title>404" in prefix or b"access denied" in prefix


def verify_document_download(
    *,
    url: str,
    content: bytes,
    content_type: str | None = None,
    expected_sha256: str | None = None,
    require_sha256: bool = False,
) -> dict[str, Any]:
    byte_count = len(content or b"")
    digest = sha256(content or b"").hexdigest()
    if byte_count <= 0:
        return {"ok": False, "verification_status": "rejected_empty", "sha256": digest, "bytes": byte_count}
    if looks_like_html_error(content, content_type):
        return {"ok": False, "verification_status": "rejected_html_error", "sha256": digest, "bytes": byte_count}
    if not is_pdf_like(url, content_type):
        return {"ok": False, "verification_status": "rejected_non_pdf", "sha256": digest, "bytes": byte_count}
    if expected_sha256 and expected_sha256 != digest:
        return {"ok": False, "verification_status": "rejected_sha_mismatch", "sha256": digest, "bytes": byte_count}
    if require_sha256 and not expected_sha256:
        return {"ok": False, "verification_status": "rejected_missing_expected_sha", "sha256": digest, "bytes": byte_count}
    return {"ok": True, "verification_status": "verified", "sha256": digest, "bytes": byte_count}


@dataclass
class FiaDocumentCandidate:
    season: int
    event_slug: str
    title: str
    source_url: str
    source_authority: str
    source_status: str
    document_id: str | None = None
    document_number: int | None = None
    published_at: str | None = None
    download_url: str | None = None
    content_type: str | None = None
    fetched_at: str = field(default_factory=utc_now)
    sha256: str | None = None
    bytes: int | None = None
    verification_status: str = "indexed"
    error_summary: str | None = None
    context_summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["document_id"] = payload["document_id"] or sha256(
            f"{self.season}:{self.event_slug}:{self.source_url}:{self.title}".encode("utf-8")
        ).hexdigest()[:16]
        payload["download_url"] = payload["download_url"] or self.source_url
        payload["is_official"] = self.source_authority in OFFICIAL_AUTHORITIES
        payload["is_verified"] = self.verification_status in {"indexed", "verified"} and self.source_authority != SUMMARY_ONLY
        payload["is_stale"] = self.source_status == "stale_cache"
        payload["context_summary_available"] = bool(self.context_summary)
        return payload


@dataclass
class FiaDocumentManifest:
    season: int
    event_slug: str | None = None
    status: str = UNAVAILABLE
    source_authority: str = UNAVAILABLE
    source_status: str = UNAVAILABLE
    documents: list[dict[str, Any]] = field(default_factory=list)
    context_summaries: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    checked_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["context_summary_available"] = bool(self.context_summaries)
        return payload


@dataclass
class FiaResolverConfig:
    enabled: bool = True
    source_priority: list[str] = field(default_factory=lambda: [
        "official_fia",
        "official_fia_event_page",
        "official_fia_archive_api",
        "f1livepulse",
        "community_index",
        "regulation_mirror",
        "verified_cache",
    ])
    fia_primary_enabled: bool = True
    fia_event_page_enabled: bool = True
    fia_archive_api_enabled: bool = True
    f1livepulse_enabled: bool = True
    community_index_enabled: bool = False
    regulation_mirror_enabled: bool = True
    cache_enabled: bool = True
    stale_cache_max_days: int = 14
    require_sha256: bool = False
    allow_summary_context: bool = True

    @classmethod
    def from_env(cls) -> "FiaResolverConfig":
        priority = [
            item.strip()
            for item in os.getenv(
                "FIA_DOCUMENT_SOURCE_PRIORITY",
                "official_fia,official_fia_event_page,official_fia_archive_api,f1livepulse,community_index,regulation_mirror,verified_cache",
            ).split(",")
            if item.strip()
        ]
        return cls(
            enabled=env_bool("FIA_DOCUMENTS_ENABLED", True),
            source_priority=priority,
            fia_primary_enabled=env_bool("FIA_DOCUMENT_FIA_PRIMARY_ENABLED", True),
            fia_event_page_enabled=env_bool("FIA_DOCUMENT_FIA_EVENT_PAGE_ENABLED", True),
            fia_archive_api_enabled=env_bool("FIA_DOCUMENT_FIA_ARCHIVE_API_ENABLED", True),
            f1livepulse_enabled=env_bool("FIA_DOCUMENT_F1LIVEPULSE_ENABLED", True),
            community_index_enabled=env_bool("FIA_DOCUMENT_COMMUNITY_INDEX_ENABLED", False),
            regulation_mirror_enabled=env_bool("FIA_DOCUMENT_REGULATION_MIRROR_ENABLED", True),
            cache_enabled=env_bool("FIA_DOCUMENT_CACHE_ENABLED", True),
            stale_cache_max_days=int(os.getenv("FIA_DOCUMENT_STALE_CACHE_MAX_DAYS", "14")),
            require_sha256=env_bool("FIA_DOCUMENT_REQUIRE_SHA256", False),
            allow_summary_context=env_bool("FIA_DOCUMENT_ALLOW_SUMMARY_CONTEXT", True),
        )


class FiaDocumentSource:
    source_key = "source"

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    def fetch(self, season: int, event_slug: str | None = None, document_kind: str = "event") -> FiaDocumentManifest:
        raise NotImplementedError


class HtmlDocumentIndexSource(FiaDocumentSource):
    def __init__(
        self,
        *,
        source_key: str,
        url: str | None,
        source_authority: str,
        source_status: str,
        fetch_text: Callable[[str], str | None],
        parse_index: Callable[[str, int, str], list[dict[str, Any]]] | None = None,
        enabled: bool = True,
        summary_only: bool = False,
    ) -> None:
        super().__init__(enabled=enabled and bool(url))
        self.source_key = source_key
        self.url = url
        self.source_authority = source_authority
        self.source_status = source_status
        self.fetch_text = fetch_text
        self.parse_index = parse_index
        self.summary_only = summary_only

    def fetch(self, season: int, event_slug: str | None = None, document_kind: str = "event") -> FiaDocumentManifest:
        if not self.enabled or not self.url:
            return FiaDocumentManifest(season=season, event_slug=event_slug, errors=[f"{self.source_key}_disabled_or_unconfigured"])
        try:
            html = self.fetch_text(self.url) or ""
        except Exception as error:
            return FiaDocumentManifest(season=season, event_slug=event_slug, errors=[f"{self.source_key}_failed:{error}"])
        if self.summary_only:
            summary = strip_html(html)[:1200]
            return FiaDocumentManifest(
                season=season,
                event_slug=event_slug,
                status=SUMMARY_ONLY,
                source_authority=SUMMARY_ONLY,
                source_status="third_party_summary_only",
                context_summaries=[{"source_url": self.url, "context_summary": summary, "fetched_at": utc_now()}] if summary else [],
                errors=[] if summary else [f"{self.source_key}_summary_empty"],
            )

        raw_docs = self.parse_index(html, season, self.url) if self.parse_index else parse_document_links(html, season, self.url)
        candidates = [
            candidate_from_raw_doc(doc, self.source_authority, self.source_status)
            for doc in raw_docs
        ]
        docs, errors = verify_candidates(candidates, document_kind=document_kind)
        return FiaDocumentManifest(
            season=season,
            event_slug=event_slug,
            status="available" if docs else UNAVAILABLE,
            source_authority=self.source_authority if docs else UNAVAILABLE,
            source_status=self.source_status if docs else UNAVAILABLE,
            documents=docs,
            errors=errors,
        )


class OfficialFiaDocumentPageSource(HtmlDocumentIndexSource):
    pass


class OfficialFiaEventPageSource(HtmlDocumentIndexSource):
    pass


class OfficialFiaArchiveApiSource(HtmlDocumentIndexSource):
    pass


class F1LivePulseDocumentSource(HtmlDocumentIndexSource):
    pass


class CommunityDocumentIndexSource(HtmlDocumentIndexSource):
    pass


class RegulationMirrorSource(HtmlDocumentIndexSource):
    def fetch(self, season: int, event_slug: str | None = None, document_kind: str = "event") -> FiaDocumentManifest:
        if document_kind != "regulation":
            return FiaDocumentManifest(season=season, event_slug=event_slug, errors=["regulation_mirror_rejected_for_event_document"])
        return super().fetch(season, event_slug=event_slug, document_kind=document_kind)


class VerifiedCacheDocumentSource(FiaDocumentSource):
    source_key = "verified_cache"

    def __init__(self, cache_path: Path | None, *, max_age_days: int = 14, enabled: bool = True) -> None:
        super().__init__(enabled=enabled and cache_path is not None)
        self.cache_path = Path(cache_path) if cache_path is not None else None
        self.max_age_days = max_age_days

    def fetch(self, season: int, event_slug: str | None = None, document_kind: str = "event") -> FiaDocumentManifest:
        if not self.enabled or self.cache_path is None or not self.cache_path.exists():
            return FiaDocumentManifest(season=season, event_slug=event_slug, errors=["verified_cache_missing"])
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception as error:
            return FiaDocumentManifest(season=season, event_slug=event_slug, errors=[f"verified_cache_invalid:{error}"])
        age_limit = datetime.now(timezone.utc) - timedelta(days=self.max_age_days)
        mtime = datetime.fromtimestamp(self.cache_path.stat().st_mtime, tz=timezone.utc)
        if mtime < age_limit:
            return FiaDocumentManifest(season=season, event_slug=event_slug, errors=["verified_cache_stale_beyond_limit"])
        docs = []
        for doc in payload.get("documents") or []:
            item = dict(doc)
            item.update({
                "source_authority": VERIFIED_CACHE,
                "source_status": "stale_cache",
                "is_official": False,
                "is_verified": bool(item.get("source_url") and item.get("title")),
                "is_stale": True,
                "context_summary_available": False,
            })
            docs.append(item)
        return FiaDocumentManifest(
            season=season,
            event_slug=event_slug,
            status="available" if docs else UNAVAILABLE,
            source_authority=VERIFIED_CACHE if docs else UNAVAILABLE,
            source_status="stale_cache" if docs else UNAVAILABLE,
            documents=docs,
            errors=[] if docs else ["verified_cache_empty"],
        )


class FiaDocumentResolver:
    def __init__(self, sources: list[FiaDocumentSource], config: FiaResolverConfig | None = None) -> None:
        self.config = config or FiaResolverConfig.from_env()
        by_key = {source.source_key: source for source in sources}
        self.sources = [by_key[key] for key in self.config.source_priority if key in by_key]
        self.sources.extend(source for source in sources if source not in self.sources)

    def resolve(self, season: int, event_slug: str | None = None, document_kind: str = "event") -> FiaDocumentManifest:
        if not self.config.enabled:
            return FiaDocumentManifest(season=season, event_slug=event_slug, errors=["fia_documents_disabled"])
        errors: list[str] = []
        summaries: list[dict[str, Any]] = []
        seen: dict[tuple[str, str | None, str], dict[str, Any]] = {}
        conflicts: list[str] = []
        for source in self.sources:
            manifest = source.fetch(season, event_slug=event_slug, document_kind=document_kind)
            errors.extend(manifest.errors)
            summaries.extend(manifest.context_summaries)
            if not manifest.documents:
                continue
            for doc in manifest.documents:
                key = (normalize_slug(doc.get("title")), str(doc.get("document_number") or ""), doc.get("sha256") or "")
                existing = seen.get(key)
                if existing and existing.get("source_url") != doc.get("source_url"):
                    if doc.get("is_official") and not existing.get("is_official"):
                        conflicts.append(f"official_copy_preferred:{doc.get('title')}")
                        seen[key] = doc
                    elif existing.get("is_official") and not doc.get("is_official"):
                        conflicts.append(f"third_party_copy_ignored:{doc.get('title')}")
                    else:
                        conflicts.append(f"duplicate_source:{doc.get('title')}")
                else:
                    seen[key] = doc
        docs = list(seen.values())
        if docs:
            first = docs[0]
            return FiaDocumentManifest(
                season=season,
                event_slug=event_slug,
                status="available",
                source_authority=first.get("source_authority") or UNAVAILABLE,
                source_status=first.get("source_status") or UNAVAILABLE,
                documents=docs,
                context_summaries=summaries,
                errors=errors,
                conflicts=conflicts,
            )
        return FiaDocumentManifest(
            season=season,
            event_slug=event_slug,
            status=UNAVAILABLE,
            source_authority=UNAVAILABLE,
            source_status=UNAVAILABLE,
            context_summaries=summaries,
            errors=errors or ["fia_documents_unavailable"],
            conflicts=conflicts,
        )


def strip_html(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def parse_document_links(html: str, season: int, base_url: str) -> list[dict[str, Any]]:
    docs = []
    for match in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html or "", flags=re.I | re.S):
        href, label = match.group(1), strip_html(match.group(2))
        if not label:
            continue
        url = urljoin(base_url, href)
        if not (is_pdf_like(url) or "decision-document" in url.lower() or "/system/files/" in url.lower() or "/file/" in url.lower()):
            continue
        docs.append({
            "season": season,
            "event_slug": "season",
            "title": label,
            "source_url": url,
            "download_url": url,
            "content_type": "application/pdf" if is_pdf_like(url) else None,
        })
    return docs


def candidate_from_raw_doc(raw: dict[str, Any], source_authority: str, source_status: str) -> FiaDocumentCandidate:
    return FiaDocumentCandidate(
        season=int(raw.get("season") or 0),
        event_slug=raw.get("event_slug") or "season",
        title=str(raw.get("title") or "").strip(),
        document_id=raw.get("document_id"),
        document_number=raw.get("document_number"),
        published_at=raw.get("published_at") or raw.get("published_at_utc"),
        source_url=raw.get("source_url") or raw.get("download_url") or "",
        download_url=raw.get("download_url") or raw.get("source_url"),
        content_type=raw.get("content_type"),
        source_authority=source_authority,
        source_status=source_status,
        sha256=raw.get("sha256"),
        bytes=raw.get("bytes"),
        verification_status=raw.get("verification_status") or "indexed",
        error_summary=raw.get("error_summary"),
        context_summary=raw.get("context_summary"),
    )


def verify_candidates(candidates: list[FiaDocumentCandidate], *, document_kind: str = "event") -> tuple[list[dict[str, Any]], list[str]]:
    docs: list[dict[str, Any]] = []
    errors: list[str] = []
    for candidate in candidates:
        if not candidate.title:
            errors.append("candidate_rejected_missing_title")
            continue
        if candidate.source_authority == SUMMARY_ONLY:
            errors.append("summary_context_not_official_document")
            continue
        if candidate.source_authority == REGULATION_MIRROR and document_kind != "regulation":
            errors.append(f"regulation_mirror_rejected_for_{document_kind}")
            continue
        if candidate.source_authority == THIRD_PARTY_INDEX:
            if not candidate.download_url:
                errors.append(f"third_party_index_rejected_missing_download:{candidate.title}")
                continue
            if not (is_fia_url(candidate.download_url) or is_pdf_like(candidate.download_url, candidate.content_type)):
                errors.append(f"third_party_index_rejected_unverifiable_url:{candidate.title}")
                continue
        payload = candidate.to_dict()
        docs.append(payload)
    return docs, errors


def manifest_to_legacy_index(manifest: FiaDocumentManifest, season_url: str | None = None) -> dict[str, Any]:
    payload = manifest.to_dict()
    payload["season_url"] = season_url
    payload["documents"] = [
        {
            **doc,
            "published_date": (doc.get("published_at") or "")[:10] or doc.get("published_date"),
            "published_time": (doc.get("published_at") or "")[11:16] or doc.get("published_time"),
            "parse_status": doc.get("parse_status") or "indexed",
            "parse_error": doc.get("parse_error"),
            "source_confidence": 1.0 if doc.get("is_official") else 0.72,
            "cache_status": doc.get("cache_status") or ("stale" if doc.get("is_stale") else "miss"),
            "season_url": season_url,
        }
        for doc in manifest.documents
    ]
    return payload
