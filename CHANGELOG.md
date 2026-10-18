# Changelog

All notable changes to OntoForge are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.1.0] - 2026-10-18

Repositioned as an open-source enterprise ontology layer (builder + pipeline), and shipped the pipeline engine.

### Added

- Pipeline engine (`ontoforge.pipeline`): dataset registration (CSV / JSON / rows), declarative column→property/link mapping with built-in transforms, two-phase atomic execution (validate everything, then materialize), primary-key upsert with stable object ids, link materialization with cardinality checks, and batch-level lineage in `state["pipelineRuns"]`; `dry_run` preview mode
- AI skeleton (`ontoforge.ai`): Logic Function registry (`register_logic` / `invoke_logic` / `list_logic`) as the protocol for a future agent/orchestration layer — no LLM calls
- `examples/traffic_pipeline.py` + sample CSV data: end-to-end pipeline walkthrough
- Docs: repositioned README with concept map, `docs/architecture.md`, `docs/pipeline.md`, `docs/guides/finance-risk.md`, `docs/roadmap.md`
- 14 pipeline + 3 AI pytest cases (suite now 46)

## [1.0.0] - 2026-10-17

Initial delivery of the single-file ontology workbench prototype.

### Added

- Object Explorer and Object View: link management, in-place action entry points, object history
- ActionType three-tab detail view with run modal and confirmation flow
- Notification center with stacked modal support (persistent modals for onboarding)
- Global search across object types and objects
- Branch center: branch creation, per-branch schema isolation, proposal diff review and merge
- Settings page: full-state JSON export/import, reset, seed-dataset onboarding
- LinkType save no longer submits read-only from/to endpoints (CORE constraint)
- Python package (`python/`): typed, zero-dependency port of the CORE+SEED domain engine — state/serialization, schema CRUD, links, the `run_action` engine, queries, branches/proposals, and the traffic-emergency seed; 29 pytest cases mirroring smoke.mjs S0–S7

### Testing

- `smoke.mjs`: 39 Node assertions against the CORE section
- `verify_ui.mjs`: 21 Playwright E2E assertions over the core interaction paths, plus final delivery check
- `python/tests`: 29 pytest assertions mirroring S0–S7
