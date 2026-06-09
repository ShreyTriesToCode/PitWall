# Local AI

[Documentation index](docs/README.md)

PitWall includes free AI-style intelligence without paid inference. The default provider is deterministic and template-based.

## Deterministic Mode

Deterministic mode is always safe for CI and Vercel:

- reads existing contract/model/source fields
- explains trust, disagreement, missing data, and source state
- never changes numeric predictions or live timing labels
- writes compact fields such as `ai_explanation`, `race_intelligence_summary`, and `changed_since_last_run`

## Local RAG

Local RAG is optional keyword/BM25-style search over committed/local PitWall documents.

```bash
python scripts/build_local_rag_index.py
python scripts/query_local_rag.py "why is trust low"
```

If no index exists, queries return:

```text
Not enough data in local PitWall sources.
```

## Local Ollama

Ollama support is local-only and disabled by default:

```env
LOCAL_LLM_ENABLED=true
LOCAL_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

If Ollama is unavailable, PitWall falls back to deterministic explanations. Local LLM text is not used to alter rankings, probabilities, results, weather, FIA notes, or timing state.
