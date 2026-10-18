# OntoForge

A single-file **ontology workbench prototype** — a concept study inspired by Foundry-style ontology managers. Zero build, zero runtime dependencies: open `ontoforge.html` in a browser and it runs.

> 中文摘要:OntoForge 是一个本体工坊概念原型(单文件、零构建、零依赖)。直接用浏览器打开 `ontoforge.html` 即可使用;`npm test` 跑冒烟断言,`npm run test:e2e` 跑 Playwright 端到端测试。详见下文。

## Features

- **Object Explorer / Object View** — browse object types, inspect objects, manage links, view history, run actions in place
- **ActionType views** — three-tab detail view with a run modal and confirmation flow for guarded actions
- **Branch center** — create branches, isolate schema changes per branch, review proposals with diffs, merge back
- **Global search** — jump to any object type or object
- **Notification center** — action toasts and audit trail
- **Settings** — full state export / import as JSON, reset, onboarding with seed datasets (e.g. a traffic-emergency sample)
- **Persistence** — all state lives in `localStorage`; refresh-safe, fully offline

## Quick start

```bash
# Option 1: just open it
open ontoforge.html          # or double-click the file; file:// works fine

# Option 2: serve it
npx serve .
```

No install, no build step. Everything (logic, seed data, UI) ships in one HTML file.

## Architecture

`ontoforge.html` is organized into three script sections:

| Section | Contents | Constraint |
|---------|----------|------------|
| `CORE`  | Pure domain logic (schema, objects, links, actions, branches, proposals) | No DOM, no UI — extracted and unit-tested in Node |
| `SEED`  | Seed datasets | Data only |
| UI      | Rendering, modals (stacked), views | UI code only |

## Testing

```bash
npm test            # smoke: 39 assertions against the CORE section, pure Node
npm run test:e2e    # E2E: 21 Playwright assertions over the core interaction paths
```

For E2E you need Playwright with a Chromium build:

```bash
npm install                        # installs playwright (devDependency)
npx playwright install chromium
npm run test:e2e
```

### Python package

The CORE + SEED domain engine is also available as a typed, zero-dependency Python package under [`python/`](python/) — same state contract, same error messages, importable from your own backend or notebook:

```bash
cd python
pip install -e ".[dev]"
pytest                 # 29 tests mirroring smoke.mjs S0–S7
```

CI (`.github/workflows/ci.yml`) runs all three suites plus a trademark red-line check on every push.

## Project layout

```
ontoforge.html       the entire application
smoke.mjs            CORE smoke tests (39 assertions)
verify_ui.mjs        Playwright E2E (21 assertions)
python/              Python port of the CORE+SEED domain engine (src layout, pytest)
docs/
  research/          reverse-engineering notes on Foundry's ontology model
  superpowers/       design specs and implementation plans
```

## Roadmap

- [ ] Split the single file into ES modules (`src/core`, `src/seed`, `src/ui`) with a bundler-less dev flow
- [ ] Broader E2E coverage (settings edge cases, proposal conflicts)
- [ ] i18n scaffolding (UI copy is currently Chinese-first)

## License

[MIT](LICENSE) © 2026 OntoForge contributors
