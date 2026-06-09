# PitWall Documentation

This is the canonical documentation index. Keep new long-form docs connected here; avoid adding standalone root Markdown files unless they are generated outputs or truly canonical.

## Reading Path

1. [Project overview](../README.md)
2. [Operator runbook](../RUNBOOK.md)
3. [Model report](../MODEL_REPORT.md)
4. [Data sources](../DATA_SOURCES.md)
5. [Artifact policy](../ARTIFACT_POLICY.md)
6. [Audit notes](../AUDIT.md)
7. [Frontend notes](../frontend/README.md)
8. [Verification history](verification-report.md)

Generated status files:

- [Model status](../MODEL_STATUS.md)
- [Run report](../RUN_REPORT.md)

Generated briefing archive:

- [Latest run status](../briefings/latest-run-status.md)
- [Barcelona Grand Prix briefing](../briefings/2026-06-14-f1-weekend-briefing-barcelona-grand-prix.md)
- [Monaco Grand Prix race briefing](../briefings/2026-06-07-f1-briefing-f1-monaco-gp-race.md)
- [Monaco Grand Prix weekend briefing](../briefings/2026-06-07-f1-weekend-briefing-monaco-grand-prix.md)
- [Canadian Grand Prix race briefing](../briefings/2026-05-25-f1-briefing-f1-canadian-gp-race.md)
- [Canadian Grand Prix weekend briefing](../briefings/2026-05-25-f1-weekend-briefing-canadian-grand-prix.md)
- [Canadian Grand Prix sprint race briefing](../briefings/2026-05-23-f1-briefing-f1-canadian-gp-sprint-race.md)
- [Canadian Grand Prix sprint weekend briefing](../briefings/2026-05-23-f1-weekend-briefing-canadian-grand-prix-sprint-race.md)

## Cleanup Policy

- Keep only canonical root docs plus generated status docs.
- Fold setup, deployment, local AI, methodology, roadmap, and experiment notes into `RUNBOOK.md` or `MODEL_REPORT.md`.
- Keep generated briefing Markdown only when it is referenced by `briefings/index.json` or useful for the archive.
- Do not commit local handoff notes, terminal logs, Playwright reports, `.env`, `.venv`, `node_modules`, `.next`, or model-input snapshots.
- Prefer linking an existing canonical doc over creating another standalone Markdown file.
