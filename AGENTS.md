# PitWall Agent Rules

- Always run Ruff against `f1_briefing.py pitwall scripts tests`; do not lint only package folders.
- Route generated JSON artifacts through `pitwall.io.atomic.atomic_write_json` or a wrapper that delegates to it.
- Never present mocked, invented, placeholder, synthesized, or hardcoded F1/FIA data as real data.
- Never synthesize FIA PDFs or FIA documents. Summary/article text is context only, not an official document.
- FIA document fallback must preserve `source_authority`, `source_status`, official/verified/stale metadata, source URLs, and error states.
- Do not commit reproducible runtime caches such as `fastf1_cache/`, `data_cache/full_races/`, FIA PDF mirrors, or large temporary frontend/model artifacts.
- Keep Top 10 and Full Grid prediction outputs working together; Top 10 must derive from the ordered Full Grid.
- Use chronological race-group validation for model promotion and keep target/post-race leakage checks active.
