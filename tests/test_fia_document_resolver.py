import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import f1_briefing as f1
from pitwall.data.fia_document_resolver import (
    CommunityDocumentIndexSource,
    F1LivePulseDocumentSource,
    FiaDocumentManifest,
    FiaDocumentResolver,
    FiaDocumentSource,
    FiaResolverConfig,
    OfficialFiaArchiveApiSource,
    OfficialFiaDocumentPageSource,
    OfficialFiaEventPageSource,
    RegulationMirrorSource,
    VerifiedCacheDocumentSource,
    verify_document_download,
)


def html_link(url="https://www.fia.com/system/files/decision-document/doc-01.pdf", title="Document 1 - Decision"):
    return f'<html><body><h2>Example Grand Prix</h2><a href="{url}">{title}</a></body></html>'


def config(priority):
    return FiaResolverConfig(source_priority=priority)


class EmptySource(FiaDocumentSource):
    source_key = "empty"

    def fetch(self, season, event_slug=None, document_kind="event"):
        return FiaDocumentManifest(season=season, event_slug=event_slug, errors=[f"{self.source_key}_empty"])


class RaisingResolver:
    def resolve(self, season, event_slug=None, document_kind="event"):
        raise RuntimeError("boom")


class FiaDocumentResolverTests(unittest.TestCase):
    def test_official_fia_document_page_success(self):
        source = OfficialFiaDocumentPageSource(
            source_key="official_fia",
            url="https://www.fia.com/documents",
            source_authority="official_fia",
            source_status="official_live",
            fetch_text=lambda _: html_link(),
            enabled=True,
        )
        manifest = FiaDocumentResolver([source], config(["official_fia"])).resolve(2026)
        self.assertEqual(manifest.source_authority, "official_fia")
        self.assertTrue(manifest.documents[0]["is_official"])

    def test_fia_documents_page_failure_event_page_success(self):
        primary = EmptySource()
        primary.source_key = "official_fia"
        event = OfficialFiaEventPageSource(
            source_key="official_fia_event_page",
            url="https://www.fia.com/events/example",
            source_authority="official_fia_event_page",
            source_status="official_secondary_live",
            fetch_text=lambda _: html_link(),
            enabled=True,
        )
        manifest = FiaDocumentResolver([primary, event], config(["official_fia", "official_fia_event_page"])).resolve(2026)
        self.assertEqual(manifest.source_authority, "official_fia_event_page")

    def test_official_sources_fail_archive_api_success(self):
        archive = OfficialFiaArchiveApiSource(
            source_key="official_fia_archive_api",
            url="https://api.fia.com/archive",
            source_authority="official_fia_archive_api",
            source_status="official_secondary_live",
            fetch_text=lambda _: html_link(),
            enabled=True,
        )
        manifest = FiaDocumentResolver([EmptySource(), archive], config(["empty", "official_fia_archive_api"])).resolve(2026)
        self.assertEqual(manifest.source_authority, "official_fia_archive_api")

    def test_f1livepulse_verifiable_official_document_link(self):
        source = F1LivePulseDocumentSource(
            source_key="f1livepulse",
            url="https://f1livepulse.example/docs",
            source_authority="third_party_official_doc_index",
            source_status="third_party_index_live",
            fetch_text=lambda _: html_link("https://www.fia.com/system/files/decision-document/doc-02.pdf"),
            enabled=True,
        )
        manifest = FiaDocumentResolver([source], config(["f1livepulse"])).resolve(2026)
        self.assertEqual(manifest.source_authority, "third_party_official_doc_index")
        self.assertFalse(manifest.documents[0]["is_official"])
        self.assertTrue(manifest.documents[0]["is_verified"])

    def test_f1livepulse_summary_only_is_context_not_official_document(self):
        source = F1LivePulseDocumentSource(
            source_key="f1livepulse",
            url="https://f1livepulse.example/article",
            source_authority="third_party_summary",
            source_status="third_party_summary_only",
            fetch_text=lambda _: "<article>Stewards summary only, no downloadable FIA document.</article>",
            enabled=True,
            summary_only=True,
        )
        manifest = FiaDocumentResolver([source], config(["f1livepulse"])).resolve(2026)
        self.assertEqual(manifest.status, "unavailable")
        self.assertEqual(manifest.documents, [])
        self.assertTrue(manifest.context_summaries)

    def test_community_index_disabled_by_default(self):
        self.assertFalse(FiaResolverConfig.from_env().community_index_enabled)

    def test_community_index_enabled_but_unstable_metadata_rejected(self):
        source = CommunityDocumentIndexSource(
            source_key="community_index",
            url="https://community.example/docs",
            source_authority="third_party_official_doc_index",
            source_status="third_party_index_live",
            fetch_text=lambda _: '<a href="https://community.example/doc.pdf"></a>',
            enabled=True,
        )
        manifest = FiaDocumentResolver([source], config(["community_index"])).resolve(2026)
        self.assertEqual(manifest.documents, [])
        self.assertIn("unavailable", manifest.status)

    def test_regulation_mirror_accepted_only_for_regulation_pdf(self):
        source = RegulationMirrorSource(
            source_key="regulation_mirror",
            url="https://statsf1.example/regulations",
            source_authority="regulation_pdf_mirror",
            source_status="regulation_mirror_live",
            fetch_text=lambda _: html_link("https://statsf1.example/f1-regulations.pdf", "2026 Sporting Regulations"),
            enabled=True,
        )
        manifest = FiaDocumentResolver([source], config(["regulation_mirror"])).resolve(2026, document_kind="regulation")
        self.assertEqual(manifest.source_authority, "regulation_pdf_mirror")

    def test_regulation_mirror_rejected_for_race_weekend_notice(self):
        source = RegulationMirrorSource(
            source_key="regulation_mirror",
            url="https://statsf1.example/regulations",
            source_authority="regulation_pdf_mirror",
            source_status="regulation_mirror_live",
            fetch_text=lambda _: html_link("https://statsf1.example/f1-regulations.pdf", "2026 Sporting Regulations"),
            enabled=True,
        )
        manifest = FiaDocumentResolver([source], config(["regulation_mirror"])).resolve(2026, document_kind="event")
        self.assertEqual(manifest.documents, [])
        self.assertIn("regulation_mirror_rejected_for_event_document", manifest.errors)

    def test_official_and_third_party_disagree_fia_wins_and_conflict_logged(self):
        official = OfficialFiaDocumentPageSource(
            source_key="official_fia",
            url="https://www.fia.com/documents",
            source_authority="official_fia",
            source_status="official_live",
            fetch_text=lambda _: html_link("https://www.fia.com/system/files/decision-document/doc-01.pdf", "Document 1 - Decision"),
            enabled=True,
        )
        third = F1LivePulseDocumentSource(
            source_key="f1livepulse",
            url="https://f1livepulse.example/docs",
            source_authority="third_party_official_doc_index",
            source_status="third_party_index_live",
            fetch_text=lambda _: html_link("https://mirror.example/doc-01.pdf", "Document 1 - Decision"),
            enabled=True,
        )
        manifest = FiaDocumentResolver([official, third], config(["official_fia", "f1livepulse"])).resolve(2026)
        self.assertEqual(manifest.documents[0]["source_authority"], "official_fia")
        self.assertTrue(manifest.conflicts)

    def test_official_and_third_party_match_dedupe_succeeds(self):
        url = "https://www.fia.com/system/files/decision-document/doc-01.pdf"
        official = OfficialFiaDocumentPageSource(
            source_key="official_fia",
            url="https://www.fia.com/documents",
            source_authority="official_fia",
            source_status="official_live",
            fetch_text=lambda _: html_link(url),
            enabled=True,
        )
        third = F1LivePulseDocumentSource(
            source_key="f1livepulse",
            url="https://f1livepulse.example/docs",
            source_authority="third_party_official_doc_index",
            source_status="third_party_index_live",
            fetch_text=lambda _: html_link(url),
            enabled=True,
        )
        manifest = FiaDocumentResolver([official, third], config(["official_fia", "f1livepulse"])).resolve(2026)
        self.assertEqual(len(manifest.documents), 1)

    def test_verified_cache_used_only_after_live_sources_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "season_index.json"
            path.write_text(json.dumps({"documents": [{"title": "Cached Decision", "source_url": "https://www.fia.com/doc.pdf"}]}), encoding="utf-8")
            cache = VerifiedCacheDocumentSource(path, max_age_days=14, enabled=True)
            manifest = FiaDocumentResolver([EmptySource(), cache], config(["empty", "verified_cache"])).resolve(2026)
            self.assertEqual(manifest.source_authority, "verified_cache")
            self.assertTrue(manifest.documents[0]["is_stale"])

    def test_stale_cache_beyond_max_age_gives_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "season_index.json"
            path.write_text(json.dumps({"documents": [{"title": "Cached Decision", "source_url": "https://www.fia.com/doc.pdf"}]}), encoding="utf-8")
            old = time.time() - 30 * 24 * 3600
            os.utime(path, (old, old))
            cache = VerifiedCacheDocumentSource(path, max_age_days=1, enabled=True)
            manifest = FiaDocumentResolver([cache], config(["verified_cache"])).resolve(2026)
            self.assertEqual(manifest.documents, [])
            self.assertIn("verified_cache_stale_beyond_limit", manifest.errors)

    def test_sha_mismatch_is_rejected(self):
        result = verify_document_download(url="https://www.fia.com/doc.pdf", content=b"%PDF-1.7 real", content_type="application/pdf", expected_sha256="bad")
        self.assertFalse(result["ok"])
        self.assertEqual(result["verification_status"], "rejected_sha_mismatch")

    def test_html_error_page_masquerading_as_pdf_is_rejected(self):
        result = verify_document_download(url="https://www.fia.com/doc.pdf", content=b"<html><title>404</title></html>", content_type="application/pdf")
        self.assertFalse(result["ok"])
        self.assertEqual(result["verification_status"], "rejected_html_error")

    def test_all_sources_fail_gives_unavailable_state(self):
        manifest = FiaDocumentResolver([EmptySource()], config(["empty"])).resolve(2026)
        self.assertEqual(manifest.status, "unavailable")
        self.assertEqual(manifest.source_authority, "unavailable")

    def test_refresh_fia_documents_handles_resolver_failure_without_crashing_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "fia-documents"
            registry = {"fia_season_document_url": "https://www.fia.com/documents/example-season"}
            with patch.object(f1, "FIA_DOCUMENT_CACHE_DIR", cache_dir), \
                 patch.object(f1, "build_fia_document_resolver", return_value=RaisingResolver()):
                payload = f1.fetch_fia_season_index(2026, registry=registry, refresh=True)

        self.assertEqual(payload["status"], "unavailable")
        self.assertIn("fia_document_resolver_failed", payload["errors"][0])


if __name__ == "__main__":
    unittest.main()
