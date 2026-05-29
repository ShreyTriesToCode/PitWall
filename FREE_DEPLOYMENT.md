# Free Deployment

PitWall is designed to run without paid AI, paid databases, paid Redis, or paid model hosting.

## Architecture

- GitHub Actions performs the heavy Python/model generation work.
- Generated JSON artifacts are committed to `main` only after validation passes.
- Vercel Hobby serves the Next.js frontend and lightweight API routes.
- The frontend reads committed JSON locally in development and can fall back to GitHub raw files in deployment.
- Deterministic AI-style features summarize existing structured fields only.

## No Paid API Requirement

The default flags are:

```env
FREE_MODE=true
AI_FEATURES_ENABLED=false
DETERMINISTIC_EXPLANATIONS_ENABLED=true
LOCAL_LLM_ENABLED=false
LOCAL_RAG_ENABLED=false
HUGGINGFACE_SPACE_AI_ENABLED=false
GITHUB_RAW_DATA_FALLBACK=true
USE_LAST_VALID_CONTRACT_ON_ERROR=true
```

AI-style text cannot alter rankings, probabilities, model scores, race results, weather values, FIA notes, penalties, or live timing state.

## Optional Local AI

Local Ollama and local RAG are development-only helpers. They are disabled by default and are not required by GitHub Actions or Vercel.

- Build local keyword index: `python scripts/build_local_rag_index.py`
- Query local index: `python scripts/query_local_rag.py "source warnings"`
- Optional Ollama: set `LOCAL_LLM_ENABLED=true`, `OLLAMA_MODEL=<local model>`.

Do not commit downloaded model files or embedding model caches.

## GitHub Contribution Graph

GitHub contributions are based on commits whose author email is linked to the GitHub account and that land on the default branch. The PitWall generation workflow configures:

- author name: `Shreyansh Singhal`
- author email: `111811929+ShreyTriesToCode@users.noreply.github.com`

Generated commits use this author through `git commit --author=...`. Contributions can take up to 24 hours to appear. Commits authored only by `github-actions[bot]` may not show on the personal contribution graph.
