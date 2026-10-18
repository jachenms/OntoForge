# OntoForge GitHub 发布包设计

- 日期:2026-10-18
- 状态:已获用户批准(对话确认 "ok")
- 关联:[2026-10-17-ontoforge-design.md](2026-10-17-ontoforge-design.md)

## 目标

将 `~/palantir_re`(OntoForge 单文件原型,master e453617)整理为符合 GitHub 发布标准的完整代码包并公开发布。

## 已裁决事项(用户确认)

1. **代码形态**:保持单文件 `ontoforge.html` 发布,模块化重构仅写入 roadmap。
2. **内容取舍**:`research/` 与 `docs/superpowers/` 全部保留并整理进文档索引。
3. **语言**:README 与仓库元信息英文为主,附中文摘要。
4. **许可证**:MIT。
5. **仓库名**:`ontoforge`(本地目录名不变,仅远端命名;遵守"零 Palantir 字样"红线)。
6. **research/ 位置**:迁入 `docs/research/`,根目录保持干净。

## 目标结构

```
ontoforge/
├── README.md            # 英文为主,附中文摘要
├── LICENSE              # MIT
├── ontoforge.html       # 产品本体(单文件,开箱即用)
├── package.json         # 元信息 + npm scripts(test / test:e2e)
├── .gitignore
├── smoke.mjs            # 单元断言(39 项)
├── verify_ui.mjs        # Playwright E2E(21 项)
├── CHANGELOG.md         # v1.0.0,自 git log 整理
├── docs/
│   ├── README.md        # 文档索引
│   ├── research/        # 逆向分析笔记(自根目录 research/ 迁入)
│   └── superpowers/     # 设计规格与实施计划(原样保留)
└── .github/workflows/ci.yml
```

## 变更清单

### 新增

- **README.md**(英文):简介(Foundry / Ontology Manager 概念原型)、Quick Start(直接打开 HTML)、功能清单(Object Explorer / Object View / ActionType / 分支中心 / 设置 / onboarding / 全局搜索)、测试跑法、单文件 CORE/SEED/UI 架构说明、roadmap(模块化重构)、文档索引。
- **LICENSE**:MIT,版权年 2026。
- **package.json**:零运行时依赖;`npm test` → `node smoke.mjs`;`npm run test:e2e` → `node verify_ui.mjs`;devDependency 声明 playwright(供 CI / 其他机器)。
- **.gitignore**:node_modules、playwright 缓存、OS 杂项。
- **CHANGELOG.md**:v1.0.0,整理自 5 个既有 commit。
- **docs/README.md**:文档索引(research 逆向分析 + superpowers 规格/计划)。
- **.github/workflows/ci.yml**:ubuntu-latest + setup-node;步骤 `node smoke.mjs` → `npm i -D playwright@1.62.1 && npx playwright install chromium` → `node verify_ui.mjs` → 红线检查 `grep -ci palantir ontoforge.html` 须为 0。

### 修改

- **verify_ui.mjs**:加载 playwright 先尝试本地 `node_modules`,失败再回退 `$HOME/.hermes/hermes-agent/node_modules`。不改变现有 hermes 环境的可用性,同时让 CI 与他人机器可跑。
- **research/ → docs/research/**:`git mv`,README 与 docs 索引同步指向新路径。

## 质量门

1. 本地 `node smoke.mjs` 全绿(39 断言)。
2. 本地 hermes E2E 全绿(21 断言):`NODE_PATH=$HOME/.hermes/hermes-agent/node_modules node verify_ui.mjs`。
3. 红线:`grep -ci palantir ontoforge.html` = 0(CI 同步强制)。
4. 上述全绿后才提交;push 到 GitHub 由用户确认后执行。

## 不做的事(YAGNI)

- 不做模块化重构(仅 roadmap)。
- 不引入构建工具 / bundler。
- 不发布 npm 包(package.json 仅作元信息与脚本载体)。
- 不改 ontoforge.html 产品代码。
