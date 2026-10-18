# Changelog

All notable changes to OntoForge are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

### Testing

- `smoke.mjs`: 39 Node assertions against the CORE section
- `verify_ui.mjs`: 21 Playwright E2E assertions over the core interaction paths, plus final delivery check
