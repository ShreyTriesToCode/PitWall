# Data sources and integrity

| Source | Active use | Freshness and limitations | Failure behavior |
|---|---|---|---|
| [Jolpica F1](https://github.com/jolpica/jolpica-f1) | Calendar, qualifying, race classification | Community provider; may lag or revise official records. Active cache TTL five minutes; request timeouts and pagination/schema checks. | No stale calendar selects a current event. Missing qualifying means no prediction. Saved results remain explicitly historical. |
| [Formula 1 timing](https://livetiming.formula1.com/static/Index.json) | Session index, timing packets, lap/tyre observations, weather, race control, audio links | Undocumented endpoints without an availability SLA. Automatic selection cache at most 15 seconds; explicit archived selection up to six hours. Live requires an active scheduled window and source UTC packet no older than 60 seconds. | Unknown timestamp is stale/unavailable. An unmatched historical selection never loads another race. Partial fields remain absent. |
| [FIA documents](https://www.fia.com/documents) | Official document metadata/archive via existing resolver | Original authority, source status, official/verified/stale flags, URLs and errors are preserved. UI labels saved metadata as historical and distinguishes indexing from current verification. | Resolver preserves cache/fallback provenance and errors. No PDF or document is fabricated. Numerical ranking does not infer car performance from document text. |
| Original Jolpica HTTP JSON in repository | Reconstructed 2018–2025 historical experiment | Original response URLs/hashes retained. Historical publication timestamps are unavailable; later corrections are possible. | Incomplete qualifying, duplicate positions, mismatched fields and missing history are excluded with reasons. |
| Immutable local forecast/evaluation ledger | Genuine new prediction history and evaluated dataset | Actual capture/retrieval/evaluation timestamps. Keep persistent backups. | Corruption or conflicting overwrite fails publication. No historical capture timestamps are invented. |

OpenF1, FastF1, Open-Meteo, F1DB, RelBench, Ollama and ICS helpers remain in the
legacy research tree. They are not production numerical fallbacks. A configured
provider is not counted as available merely because its URL or credentials exist.

## Status meanings

- **UPCOMING**: confirmed scheduled future race; does not imply a forecast exists.
- **UPDATING**: scheduled start passed recently; this is not proof of live activity.
- **LIVE**: timing source packet freshness and active session window both verified.
- **STALE**: prior evidence exists but freshness is not established.
- **UNAVAILABLE**: no reliable current data or valid input for that feature.
- **HISTORICAL**: a past classification, saved archive, or ended session snapshot.

Retrieval time is never presented as the time a timing packet was produced.
An empty successful qualifying response establishes endpoint accessibility, not
that a qualifying result exists. Missing numbers never become zero.

## Timing field semantics

Wind speed is supplied in m/s. Tyre age is an observed lap count, not an estimated
percentage of life remaining. A zero observation is distinct from missing data.
Provider `Utc` message fields are normalized with an explicit UTC suffix; generic
dates without an offset and relative audio times do not become absolute timestamps.
Unknown car channels are not assigned speculative labels. Archived car readings
are the latest retained feed values, not race averages.

## Usage and attribution

[Jolpica documentation](https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md)
describes its Ergast-compatible API. Cache and limit requests; do not assume an
unlimited service or guaranteed update time. Provider content is subject to its
terms. Formula 1 and FIA content, names, images, audio and PDFs retain their owners'
rights. The repository's MIT code license does not license third-party data.
No legally required notices have been removed. The application makes no affiliation
claim and requires no paid OpenF1 or AI account for current functionality.

During the audit, the current Jolpica selection was cross-checked against the
[official 2026 F1 calendar](https://www.formula1.com/en/racing/2026), which listed
Azerbaijan as the next event. That verification is audit evidence, not a hardcoded
runtime choice. The application requests the current UTC year's calendar and,
after season end, the next published year's calendar.
