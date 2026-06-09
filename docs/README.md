# PitWall Documentation Index

This index keeps the repo's markdown files connected. Generated briefing files stay in `briefings/` because the dashboard archive reads them from there.

## Start Here

- [README](../README.md): project overview, local commands, and deployment flow.
- [Setup](../SETUP.md): install dependencies and configure optional environment variables.
- [Runbook](../RUNBOOK.md): validation, retraining, cache refresh, and operator commands.
- [Free Deployment](../FREE_DEPLOYMENT.md): no-paid-service deployment model.
- [Frontend README](../frontend/README.md): Next.js routes and frontend data policy.

## Model And Data

- [Methodology](../METHODOLOGY.md): prediction philosophy, data sources, and uncertainty handling.
- [Model Design](../MODEL_DESIGN.md): model architecture and feature families.
- [Model Report](../MODEL_REPORT.md): current model outputs, metrics, contracts, and known limitations.
- [Model Experiments](../MODEL_EXPERIMENTS.md): experiment records and promotion guardrails.
- [Model Status](../MODEL_STATUS.md): latest generated model status.
- [Run Report](../RUN_REPORT.md): latest generated contract validation summary.
- [Data Sources](../DATA_SOURCES.md): official, optional, fallback, and cache-backed sources.
- [Artifact Policy](../ARTIFACT_POLICY.md): what is allowed in Git and what should remain cache-only.

## Project Tracking

- [Audit](../AUDIT.md): completed hardening/audit notes and remaining risks.
- [Roadmap](../ROADMAP.md): planned improvements.
- [Changelog](../CHANGELOG.md): user-facing change history.
- [Verification Report](verification-report.md): validation history and source documentation checks.

## Generated Briefings

- [Latest run status](../briefings/latest-run-status.md)
- [Barcelona Grand Prix briefing](../briefings/2026-06-14-f1-weekend-briefing-barcelona-grand-prix.md)
- [Monaco Grand Prix race briefing](../briefings/2026-06-07-f1-briefing-f1-monaco-gp-race.md)
- [Monaco Grand Prix weekend briefing](../briefings/2026-06-07-f1-weekend-briefing-monaco-grand-prix.md)
- [Canadian Grand Prix race briefing](../briefings/2026-05-25-f1-briefing-f1-canadian-gp-race.md)
- [Canadian Grand Prix weekend briefing](../briefings/2026-05-25-f1-weekend-briefing-canadian-grand-prix.md)
- [Canadian Grand Prix sprint race briefing](../briefings/2026-05-23-f1-briefing-f1-canadian-gp-sprint-race.md)
- [Canadian Grand Prix sprint weekend briefing](../briefings/2026-05-23-f1-weekend-briefing-canadian-grand-prix-sprint-race.md)

## Cleanup Policy

- Keep generated briefing markdown only when it is referenced by `briefings/index.json` or useful for the archive.
- Keep generated status markdown when it reflects the latest checked-in contract.
- Do not commit local handoff notes, terminal logs, Playwright reports, `.env`, `.venv`, `node_modules`, or `.next`.
- Prefer adding a link here instead of creating another standalone root markdown file.
