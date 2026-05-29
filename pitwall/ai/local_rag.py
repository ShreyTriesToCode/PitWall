"""Optional local keyword/BM25-style search over PitWall documents."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_INDEX_PATH = Path("data_cache/rag_index/index.json")
DEFAULT_SOURCE_GLOBS = [
    "briefings/*.md",
    "MODEL_STATUS.md",
    "MODEL_REPORT.md",
    "MODEL_DESIGN.md",
    "METHODOLOGY.md",
    "DATA_SOURCES.md",
    "data_cache/model-status.json",
    "data_cache/latest-model-debug.json",
    "data_cache/model_corrections.json",
    "data_cache/backtest-history.json",
    "data_cache/source_registry/**/*.json",
    "data_cache/fia-documents/**/text/*.txt",
]


def tokenize(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9]{3,}", text.lower()) if word not in {"the", "and", "for", "with", "that"}]


def build_keyword_index(base_dir: Path | str = ".", output_path: Path | str = DEFAULT_INDEX_PATH) -> dict[str, Any]:
    base = Path(base_dir)
    docs = []
    for pattern in DEFAULT_SOURCE_GLOBS:
        for path in base.glob(pattern):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            tokens = tokenize(text)
            if not tokens:
                continue
            rel = str(path.relative_to(base))
            docs.append({"path": rel, "title": path.name, "tokens": dict(Counter(tokens)), "preview": text[:800]})
    payload = {
        "schema_version": "pitwall-local-rag-v1",
        "generated_by": "keyword_bm25",
        "document_count": len(docs),
        "documents": docs,
    }
    output = base / output_path
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def query_keyword_index(query: str, base_dir: Path | str = ".", index_path: Path | str = DEFAULT_INDEX_PATH, limit: int = 5) -> dict[str, Any]:
    base = Path(base_dir)
    path = base / index_path
    if not path.exists() or not str(query or "").strip():
        return _no_data()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _no_data()
    query_terms = tokenize(query)
    if not query_terms:
        return _no_data()
    docs = payload.get("documents") or []
    doc_count = max(1, len(docs))
    df = Counter()
    for doc in docs:
        for term in set((doc.get("tokens") or {}).keys()):
            df[term] += 1
    rows = []
    for doc in docs:
        tokens = doc.get("tokens") or {}
        score = 0.0
        for term in query_terms:
            tf = float(tokens.get(term) or 0)
            if tf <= 0:
                continue
            idf = math.log((doc_count + 1) / (df[term] + 0.5)) + 1
            score += (tf / (tf + 1.2)) * idf
        if score > 0:
            rows.append({"path": doc.get("path"), "title": doc.get("title"), "score": round(score, 4), "preview": doc.get("preview", "")[:360]})
    rows.sort(key=lambda row: row["score"], reverse=True)
    if not rows:
        return _no_data()
    return {"ok": True, "answer": "Local PitWall sources contain matching snippets.", "results": rows[:limit], "generated_by": "keyword_bm25"}


def _no_data() -> dict[str, Any]:
    return {"ok": False, "answer": "Not enough data in local PitWall sources.", "results": [], "generated_by": "keyword_bm25"}
