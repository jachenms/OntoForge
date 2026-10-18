# Palantir Foundry / Ontology 逆向分析(公开资料证据驱动)

日期:2026-10-17 · 方法:REA skill 流程(证据优先:观测 / 推断 / 未知三类分离)

## 0. 证据边界(诚信声明)

| 类型 | 内容 |
|---|---|
| **观测(Observed)** | palantir.com/platforms/foundry 营销页(Next.js SSR JSON 提取);palantir.com/docs/foundry 官方文档 4 页正文 + 完整文档导航树(404 行,存 `research/docs-sidebar-tree.txt`) |
| **推断(Inferred)** | 由文档术语与导航结构推导的架构分层、UX 模式;搜索快照中的第三方描述 |
| **未知(Unknown)** | 实际产品的运行时行为、真实 UI 像素细节、性能/规模指标、闭源实现 —— 无 shipped artifact,无测试实例,未做运行时观测 |

命名澄清:Palantir 官方**没有叫 "Ontology Builder" 的独立应用**。本体建模应用叫 **Ontology Manager(OMA)**,文档大章节叫 "Ontology building"。用户所说 "Ontology Builder" 即指这一能力域。

## 1. 平台层:Foundry 能力地图(观测:docs 顶部导航)

官方文档把平台能力分为 11 个域:

1. **AI Platform (AIP)** — LLM 接入、AIP Logic、Agent Studio 等
2. **Data connectivity & integration** — 源连接、同步、Pipeline Builder、流批一体
3. **Model connectivity & development** — 模型注册、训练、评估、托管
4. **Ontology building** — 本体定义(本项目重点)
5. **Developer toolchain** — OSDK(本体 SDK)、API、代码仓库
6. **Use case development** — Workshop(应用搭建)、Slate、Quiver、Contour、Map 等
7. **Observability** — 监控、告警、健康度
8. **Analytics** — 报表、探索分析
9. **Product delivery** — Marketplace(产品打包分发)
10. **Security & governance** — 角色、权限、审计
11. **Management & enablement** — 平台管理、用量

营销页定位语(观测):**"The Ontology-Powered Operating System for the Modern Enterprise"**、**"Run your business as code"**;Ontology 是 Foundry 的心脏,"integrates the **semantic**, **kinetic**, and **dynamic** elements of your business"。

## 2. Ontology 概念模型(观测:官方文档 core-concepts 页)

### 2.1 定义

> The Ontology is an **operational layer** for the organization. It sits on top of the digital assets(datasets, virtual tables, models)and connects them to their real-world counterparts … In many settings, the Ontology serves as a **digital twin** of the organization.

### 2.2 三要素:语义 / 动力 / 接口

| 层 | 要素 | 定义(官方原文压缩) |
|---|---|---|
| **语义 Semantic** | object type | 真实世界实体或事件的 schema 定义;object = 一个实例;object set = 实例集合 |
| | property | object type 的特征;property value = 某实例上的值 |
| | shared property | 可挂到多个 object type 上的共享属性,统一元数据管理 |
| | link type | 两个 object type 之间关系的 schema;link = 一个关系实例 |
| **动力 Kinetic** | action type | 一组对 objects/properties/links 的**事务性修改** + 提交时的副作用行为的定义 |
| | function | 代码逻辑(TypeScript/Python),输入参数→输出;原生接受 objects/object sets,可跨 action types 与应用复用 |
| **多态** | interface | 描述 object type 的"形状与能力",提供 object type 多态 |

### 2.3 数据集 ↔ 本体类比(官方文档原文表格)

| 数据集世界 | 本体世界 |
|---|---|
| Dataset | Object type |
| Row | Object |
| Column | Property |
| Field | Property value |
| Join | Link type |

### 2.4 属性系统的完整度(观测:文档导航树)

属性子系统远超普通 catalog:**value formatting、conditional formatting、edit-only、required、mandatory control、base types、property reducers、derived properties、structs(嵌套结构)、shared properties、value types(带版本/权限/约束)、type classes、render hints**。

### 2.5 Action types:本体的"写"侧(观测:action-types 文档)

- **Action = 单笔事务**,按用户定义逻辑同时改一个或多个 object 的属性/链接
- 组成:**parameters(标准化表单输入)→ rules/validation → submission criteria → logic → side effects**
- 副作用:**notification(通知旧/新经理)、webhook、写回源系统(write-back)**
- 治理:权限校验(如仅 HR 可执行)、**审计轨迹**、跨所有应用一致的编辑语义
- 官方例:`Assign Employee` action 改 Employee.role,自动建 Employee→Manager link,通知相关人
- 关键哲学(原文):决策与洞察以 edits 形式沉淀回数据资产,"the data asset grows in richness and value as user decisions are captured" —— **闭环运营(closed-loop operations)**

### 2.6 分支治理(观测:导航树)

Ontology 支持 **branching(分支)→ proposals(提案)→ review(评审)→ merge**,另有 shared ontologies、migrating between ontologies —— 即**对本体的 Git 式协作治理**。

### 2.7 动态层(观测:导航树)

- **Ontology scenarios**:临时场景(temporary scenarios)、scenario 元数据存为 objects、merge scenarios、OSDK 集成 —— what-if 沙盘
- **Semantic search / Ontology Augmented Generation (OAG)**:embedding 模型选择、文档处理、语义搜索工作流(注意:用户的 OAG 评估工作台正是评估这一类东西的成熟度)
- **Derived properties**:计算属性

## 3. Ontology Manager(OMA)UX 结构(观测:om-overview 文档)

### 3.1 入口

Workspace 侧边栏 Apps 区图标 / Data Lineage 右键 "Configure object type" / `/workspace/ontology` 直链。

### 3.2 界面骨架

```
┌──────────────── Top bar:搜索资源 · 新建资源 · 分支切换/新建 ────────────────┐
├── Sidebar(资源导航)──┬────────────── 主视图区 ──────────────────────────────┤
│                     │                                                      │
```

### 3.3 五种视图

1. **Discover view**:落地页。默认 = 收藏 object types + 最近查看 + 收藏分组;新用户 = 最近修改 + 重点 object types;栏目可自定义
2. **Object type view**:左侧页签 + 右侧页面。Overview 页 7 个 section:**① 元数据 ② Properties ③ Action types ④ Link type graph(关系图)⑤ Dependents ⑥ Data(预览底层数据)⑦ Usage(用量)**
3. **Property editor view**:从 Properties 区点入单属性编辑
4. **Link type view**:Overview + Datasources 两页(外键映射)
5. **Action type view**:**Overview / Logic / Observability** 三页 —— Observability 显示近 30 天近实时调用量与监控规则

另有 **Function type view**。

### 3.4 安全模型

**Roles 是本体中心权限模型**,可授在 Ontology 级或单资源级;另有 object security policies、restricted-view-backed object types、Multi-datasource object types(MDOs)。

## 4. Ontology 驱动的应用生态(观测:导航树 Applications 节)

| 应用 | 作用 |
|---|---|
| **Object Explorer** | 搜索/探索对象、SQL 分析、图表、链接跳转探索、对象集对比、Apply Actions、保存探索 |
| **Object Views** | 单个对象的"中央枢纽"页:关键信息+链接对象+指标+关联仪表盘/应用;有 Standard/Full/Panel 三级形态,可配置 tabs/侧栏/可视化/布局 |
| **Object Monitors** | [已 Sunset] 条件监控+通知 |
| **Map** | 地理可视化:图层、选区、直方图过滤、时间轴、tracks、Action 触发,可嵌 Workshop |
| **Vulcan** | (时序/图表,可嵌 Workshop) |
| **Dynamic Scheduling** | 排产甘特图,直接操作本体原语,拖拽即 Action |
| **Workshop** | 低代码应用搭建(导航树另有完整章节) |
| **Foundry Rules** | 规则引擎 |

架构底座(观测:导航树 Ontology architecture 节):**Object Storage v2(OSv2)**、indexing(funnel batch/streaming pipelines、direct datasources)、**user edits 应用机制 + materializations(物化)**、edit history、object databases(旧版 Phonograph 弃用中)。

## 5. 逆向结论:可模仿的设计模式 vs 不可触碰

### 5.1 值得概念级模仿的 7 个模式

1. **语义+动力双层模型**:不止建图谱(schema),还要建 Action(受治理的写路径)—— 这是 Foundry 与普通知识图谱产品的分水岭
2. **数据集↔本体直白类比**:用 "dataset/row/column/join" 解释 object/object/property/link,用户零门槛
3. **本体即数字孪生 + 闭环**:决策以 edit 形式回流,数据资产随使用增值
4. **OMA 的对象类型 7-section Overview**(元数据/属性/动作/关系图/依赖/数据/用量)—— 信息架构可直接借鉴
5. **Action type 的参数→校验→提交条件→副作用流水线** —— 表单化、可治理、跨应用一致
6. **本体分支/提案/评审**:schema 治理 Git 化
7. **Object View 作为对象级"中央枢纽"**:一切应用围绕对象聚合

### 5.2 不可做(法律红线)

- 不使用 Palantir 商标/Logo/截图/品牌视觉;不复制其文案原文做商业发布(内部学习分析 OK)
- 不声称"Palantir 官方/兼容/认证";命名自创
- 模仿的是**概念与交互模式**(不受版权保护),不是代码与美术资产

### 5.3 与既有资产的衔接(推断)

- 用户已有:OAG 本体评估工作台(10维×40指标)、爱化身本体图谱 v1.8、gd 交通本体测试集
- 一个 Foundry 式 OMA 演示可直接加载 gd_traffic_tbox_v4.owl 做示例本体,评估工作台可当 "Ontology 健康度" 面板的数据源

## 证据文件

- `research/docs-sidebar-tree.txt` — Ontology building 完整文档导航树(404 节点)
- `research/onto_overview.txt` / `onto_core.txt` / `om_overview.txt` / `action_overview.txt` — 四页正文抽取
- 来源:palantir.com/platforms/foundry · palantir.com/docs/foundry/ontology/{overview,core-concepts} · /ontology-manager/overview · /action-types/overview
