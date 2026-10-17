# OntoForge 本体工坊 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 单文件 vanilla HTML 的 Palantir Foundry/Ontology Manager 概念模仿原型:浏览器内真建 object/link/action type、真跑 action 写回数据、schema 分支治理,localStorage 持久化。

**Architecture:** 单 `ontoforge.html` 三段式:`<script id="core">` 纯逻辑(零 DOM,Node 可测)、`<script id="seed">` 种子构建(调用 CORE)、`<script id="appjs">` UI(STORE/路由/视图)。`smoke.mjs` 按 oag_eval 模式提取 core+seed 在 Node 断言;`verify_ui.mjs` 用 playwright 做 headless E2E。

**Tech Stack:** vanilla JS/HTML/CSS;Node.js(smoke);playwright via `NODE_PATH=$HOME/agentrix-arch-3d-tooling/node_modules`(浏览器在 `~/.cache/ms-playwright`)。

## Global Constraints

- UI 全部中文;产品名 **OntoForge 本体工坊**;**文件中禁止出现 "Palantir" 字样**(smoke 断言,不区分大小写)
- 零外部依赖;`file://` 直开可用;不引入任何 CDN/npm 包到交付 HTML
- 三段 script 的 id 固定为 `core` / `seed` / `appjs`(smoke 依赖)
- `state.v = 1`;localStorage 键 `ontoforge.v1`,备份键 `ontoforge.v1.bak`
- CORE 纯函数:不碰 DOM、不碰 localStorage、不碰 Date 以外的副作用(uid 允许);所有 CORE 函数通过 `globalThis.CORE` 导出
- `BASE_TYPES = ['string','number','boolean','date','enum']`;`RULE_OPS = ['eq','neq','in','notIn','gt','lt','ge','le','contains']`
- 分支只隔离 schema(`state.schemas[branchName]`),实例数据全局共享(spec §5)
- 每个任务结束:`node smoke.mjs` 全绿 + git commit
- 工作目录 `~/palantir_re`,已 git init

---

### Task 1: 骨架 + CORE 基础 + smoke 骨架

**Files:**
- Create: `ontoforge.html`
- Create: `smoke.mjs`

**Interfaces:**
- Produces(后续全部任务依赖):
  - `CORE.uid(prefix) → string`
  - `CORE.clone(o) → deep copy`
  - `CORE.createEmptyState() → state`(结构见 spec §3,含 `schemas:{main:…}`、`notices:[]`)
  - `CORE.schemaOf(state) → state.schemas[state.branch.current]`
  - `CORE.serialize(state) → string`;`CORE.deserialize(text) → {ok,state?|error?}`
  - `CORE.validateState(s) → string[]`
  - `CORE.BASE_TYPES`, `CORE.RULE_OPS`
  - smoke 工具:`T(name,fn)`、`ok(cond,msg)`、`eq(a,b,msg)`、`section(id)`

- [ ] **Step 1: 写 smoke.mjs 骨架(含失败断言)**

```js
// smoke.mjs — OntoForge 冒烟测试(oag_eval 同款模式)
import {readFileSync} from 'fs';
const html = readFileSync(new URL('./ontoforge.html', import.meta.url), 'utf8');
function section(id){
  const m = html.match(new RegExp('<script id="'+id+'">([\\s\\S]*?)</script>'));
  if(!m) throw new Error('缺少 <script id="'+id+'">');
  return m[1];
}
let pass=0, fail=0;
const T=(name,fn)=>{ try{ fn(); pass++; console.log('ok  -',name); }catch(e){ fail++; console.log('FAIL-',name,'::',e.message); } };
const ok=(c,m)=>{ if(!c) throw new Error(m||'assert failed'); };
const eq=(a,b,m)=>{ if(JSON.stringify(a)!==JSON.stringify(b)) throw new Error((m||'eq')+': '+JSON.stringify(a)+' !== '+JSON.stringify(b)); };

eval(section('core'));   // 导出 globalThis.CORE
eval(section('seed'));   // 导出 globalThis.SEED(Task 8 前允许为空注释)

// ── S8 静态检查 ──
T('S8.1 三个 script 段存在', ()=>{ ['core','seed','appjs'].forEach(i=>section(i)); });
T('S8.2 无商标字样', ()=>{ ok(!/palantir/i.test(html), '文件中出现 Palantir 字样'); });
// ── S0 序列化 ──
T('S0.1 空状态序列化往返', ()=>{
  const s=CORE.createEmptyState();
  const r=CORE.deserialize(CORE.serialize(s));
  ok(r.ok, r.error);
  eq(r.state.meta.ontologyName, s.meta.ontologyName, 'ontologyName 往返');
  ok(r.state.schemas.main, 'schemas.main 存在');
});
T('S0.2 非法输入拒绝', ()=>{
  ok(!CORE.deserialize('not json').ok, '坏 JSON 应拒绝');
  ok(!CORE.deserialize('{"app":"other"}').ok, '非本应用文件应拒绝');
});

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
```

- [ ] **Step 2: 运行确认失败**

Run: `cd ~/palantir_re && node smoke.mjs`
Expected: FAIL(ontoforge.html 不存在,readFileSync 抛错)

- [ ] **Step 3: 写 ontoforge.html 骨架与 CORE 基础**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>OntoForge 本体工坊</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
/* Task 9 填充全部样式 */
</style>
</head>
<body>
<div id="app"></div>
<script id="core">
const CORE=(()=>{
let _seq=0;
const uid=(p)=>p+'_'+Date.now().toString(36)+'_'+(_seq++).toString(36)+Math.random().toString(36).slice(2,6);
const clone=(o)=>JSON.parse(JSON.stringify(o));
const BASE_TYPES=['string','number','boolean','date','enum'];
const RULE_OPS=['eq','neq','in','notIn','gt','lt','ge','le','contains'];

function createEmptyState(){
  return {
    v:1,
    meta:{ ontologyName:'未命名本体', createdAt:new Date().toISOString(), rev:0 },
    branch:{ current:'main', list:[{name:'main', baseRev:0, status:'active', createdAt:new Date().toISOString()}] },
    schemas:{ main:{ objectTypes:[], linkTypes:[], actionTypes:[], sharedProps:[] } },
    proposals:[],
    data:{ objects:[], links:[] },
    audit:[],
    notices:[],
    ui:{ view:'discover', sel:null, favorites:[], recent:[] }
  };
}
function schemaOf(state){ return state.schemas[state.branch.current]; }

function serialize(state){ return JSON.stringify({app:'ontoforge', v:1, state}, null, 2); }
function validateState(s){
  const errs=[];
  if(!s || typeof s!=='object') return ['state 不是对象'];
  if(s.v!==1) errs.push('state.v 必须为 1');
  if(!s.meta||typeof s.meta.ontologyName!=='string') errs.push('缺 meta.ontologyName');
  if(!s.branch||!s.branch.current||!Array.isArray(s.branch.list)) errs.push('缺 branch 结构');
  if(!s.schemas||typeof s.schemas!=='object') errs.push('缺 schemas');
  else if(s.branch && !s.schemas[s.branch.current]) errs.push('当前分支无 schema: '+s.branch.current);
  for(const k of ['objectTypes','linkTypes','actionTypes','sharedProps']){
    if(s.schemas && s.schemas[s.branch.current] && !Array.isArray(s.schemas[s.branch.current][k])) errs.push('schema.'+k+' 非数组');
  }
  if(!s.data||!Array.isArray(s.data.objects)||!Array.isArray(s.data.links)) errs.push('缺 data.objects/links');
  if(!Array.isArray(s.audit)) errs.push('audit 非数组');
  if(!Array.isArray(s.proposals)) errs.push('proposals 非数组');
  if(!Array.isArray(s.notices)) errs.push('notices 非数组');
  return errs;
}
function deserialize(text){
  let o; try{ o=JSON.parse(text); }catch(e){ return {ok:false,error:'JSON 解析失败: '+e.message}; }
  if(!o||o.app!=='ontoforge') return {ok:false,error:'不是 OntoForge 导出文件'};
  const errs=validateState(o.state);
  if(errs.length) return {ok:false,error:errs[0],errors:errs};
  return {ok:true,state:o.state};
}

return { uid, clone, BASE_TYPES, RULE_OPS, createEmptyState, schemaOf, serialize, validateState, deserialize };
})();
if(typeof globalThis!=='undefined') globalThis.CORE=CORE;
</script>
<script id="seed">
/* Task 8 填充:SEED 构建(交通应急 / 空白) */
</script>
<script id="appjs">
/* Task 9 起填充:STORE / 路由 / 视图 / 启动 */
</script>
</body>
</html>
```

- [ ] **Step 4: 运行确认通过**

Run: `node smoke.mjs`
Expected: `4 passed, 0 failed`

- [ ] **Step 5: Commit**

```bash
cd ~/palantir_re
git add ontoforge.html smoke.mjs
git commit -m "feat: 骨架 + CORE 基础(状态/序列化/校验) + smoke 骨架"
```

---

### Task 2: CORE 对象类型 / 属性 / 共享属性 CRUD

**Files:**
- Modify: `ontoforge.html`(`<script id="core">` 段,return 前追加函数并加入导出表)
- Modify: `smoke.mjs`(追加 S1 节)

**Interfaces:**
- Consumes: Task 1 的 `schemaOf`、`uid`、`BASE_TYPES`
- Produces:
  - `CORE.addObjectType(state,{name,label?,icon?,color?,primaryKey?}) → {ok,id?|error}` — name 必须 `^[a-z][a-z0-9_]*$` 且不重复
  - `CORE.updateObjectType(state,id,patch) → {ok|error}` — 只允许 label/icon/color/primaryKey;primaryKey 须为已有属性 name
  - `CORE.deleteObjectType(state,id) → {ok|error}` — 有实例/被 linkType 引用/被 actionType 引用时拒绝(错误信息点名)
  - `CORE.addProperty(state,typeId,{name,label?,baseType,enumValues?,required?}) → {ok|error}`
  - `CORE.updateProperty(state,typeId,propName,patch) → {ok|error}` — 不允许改 name
  - `CORE.deleteProperty(state,typeId,propName) → {ok|error}` — 是 primaryKey 时拒绝
  - `CORE.addSharedProp(state,{name,label?,baseType,enumValues?}) → {ok,id?|error}`
  - `CORE.attachSharedProp(state,typeId,spId) → {ok|error}`;`CORE.detachSharedProp(state,typeId,spId) → {ok|error}`(注意:sharedPropRefs 存的是共享属性 **id**,UI 一律按 id 比较)
  - `CORE.deleteSharedProp(state,spId) → {ok|error}` — 有对象类型挂载时拒绝
  - 每次成功修改 `state.meta.rev++`(全部写操作统一,后续任务同)

- [ ] **Step 1: smoke 追加 S1(先运行确认 FAIL: addObjectType 未定义)**

```js
// ── S1 对象类型/属性/共享属性 ──
T('S1.1 建对象类型+name 校验', ()=>{
  const s=CORE.createEmptyState();
  ok(!CORE.addObjectType(s,{name:'Bad Name'}).ok,'大写空格名应拒绝');
  ok(CORE.addObjectType(s,{name:'road_segment',label:'路段',primaryKey:''}).ok,'合法名应通过');
  ok(!CORE.addObjectType(s,{name:'road_segment'}).ok,'重名应拒绝');
});
T('S1.2 属性 CRUD 与主键保护', ()=>{
  const s=CORE.createEmptyState();
  const t=CORE.addObjectType(s,{name:'incident',label:'事件'}); const tid=t.id;
  ok(CORE.addProperty(s,tid,{name:'inc_id',baseType:'string',required:true}).ok,'加属性');
  ok(!CORE.addProperty(s,tid,{name:'inc_id',baseType:'string'}).ok,'属性重名应拒绝');
  ok(!CORE.addProperty(s,tid,{name:'x',baseType:'enum'}).ok,'enum 缺 enumValues 应拒绝');
  ok(CORE.addProperty(s,tid,{name:'status',baseType:'enum',enumValues:['待处置','已关闭']}).ok,'enum 带值通过');
  ok(CORE.updateObjectType(s,tid,{primaryKey:'inc_id'}).ok,'设主键');
  ok(!CORE.deleteProperty(s,tid,'inc_id').ok,'删主键属性应拒绝');
  ok(!CORE.updateProperty(s,tid,'status',{name:'st'}).ok,'属性改名应拒绝');
});
T('S1.3 删除保护', ()=>{
  const s=CORE.createEmptyState();
  const a=CORE.addObjectType(s,{name:'a'}).id, b=CORE.addObjectType(s,{name:'b'}).id;
  // 有实例拒绝
  s.data.objects.push({__id:'o1',__type:'a',props:{}});
  ok(!CORE.deleteObjectType(s,a).ok,'有实例应拒绝'); s.data.objects=[];
  // 被 linkType 引用拒绝(Task 3 补上 linkType 后仍成立;此处手工塞一个)
  CORE.schemaOf(s).linkTypes.push({id:'lt1',name:'ab',from:'a',to:'b',cardinality:'N:1',keyMapping:{}});
  ok(!CORE.deleteObjectType(s,a).ok,'被 linkType 引用应拒绝');
});
T('S1.4 共享属性挂载', ()=>{
  const s=CORE.createEmptyState();
  const tid=CORE.addObjectType(s,{name:'x'}).id;
  const sp=CORE.addSharedProp(s,{name:'region',label:'区域',baseType:'string'});
  ok(sp.ok,'建共享属性');
  ok(CORE.attachSharedProp(s,tid,sp.id).ok,'挂载');
  ok(!CORE.attachSharedProp(s,tid,sp.id).ok,'重复挂载应拒绝');
  ok(!CORE.deleteSharedProp(s,sp.id).ok,'被挂载时删除应拒绝');
  ok(CORE.detachSharedProp(s,tid,sp.id).ok,'卸载');
  ok(CORE.deleteSharedProp(s,sp.id).ok,'卸载后可删除');
  ok(!CORE.deleteSharedProp(s,'sp_none').ok,'不存在应拒绝');
});
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `node smoke.mjs` — Expected: S1.x FAIL(`CORE.addObjectType is not a function`),S0/S8 仍绿

- [ ] **Step 3: CORE 追加实现(id="core" 段,`return` 之前插入;导出表追加同名键)**

```js
const NAME_RE=/^[a-z][a-z0-9_]*$/;
function _bump(state){ state.meta.rev++; }
function _findType(state,id){ return schemaOf(state).objectTypes.find(t=>t.id===id); }

function addObjectType(state,def){
  const s=schemaOf(state);
  if(!def||!NAME_RE.test(def.name||'')) return {ok:false,error:'name 需为小写字母开头的蛇形标识'};
  if(s.objectTypes.some(t=>t.name===def.name)) return {ok:false,error:'对象类型 name 冲突: '+def.name};
  const t={ id:uid('ot'), name:def.name, label:def.label||def.name, icon:def.icon||'📦',
            color:def.color||'#2563eb', primaryKey:def.primaryKey||'', properties:[], sharedPropRefs:[] };
  if(t.primaryKey) return {ok:false,error:'primaryKey 需在建属性后通过 updateObjectType 设置'};
  s.objectTypes.push(t); _bump(state); return {ok:true,id:t.id};
}
function updateObjectType(state,id,patch){
  const t=_findType(state,id); if(!t) return {ok:false,error:'对象类型不存在'};
  for(const k of ['label','icon','color']) if(patch[k]!==undefined) t[k]=patch[k];
  if(patch.primaryKey!==undefined){
    if(patch.primaryKey!=='' && !t.properties.some(p=>p.name===patch.primaryKey))
      return {ok:false,error:'primaryKey 须为已有属性 name'};
    t.primaryKey=patch.primaryKey;
  }
  _bump(state); return {ok:true};
}
function deleteObjectType(state,id){
  const s=schemaOf(state); const t=_findType(state,id); if(!t) return {ok:false,error:'对象类型不存在'};
  if(state.data.objects.some(o=>o.__type===t.name)) return {ok:false,error:'存在该类型实例,不可删除'};
  const lt=s.linkTypes.find(l=>l.from===t.name||l.to===t.name);
  if(lt) return {ok:false,error:'被链接类型引用: '+lt.name};
  const at=s.actionTypes.find(a=>(a.targets||[]).some(r=>r.type===t.name)||(a.edits||[]).some(e=>e.objectType===t.name));
  if(at) return {ok:false,error:'被动作类型引用: '+at.name};
  s.objectTypes=s.objectTypes.filter(x=>x.id!==id); _bump(state); return {ok:true};
}
function addProperty(state,typeId,prop){
  const t=_findType(state,typeId); if(!t) return {ok:false,error:'对象类型不存在'};
  if(!NAME_RE.test(prop.name||'')) return {ok:false,error:'属性 name 需为蛇形标识'};
  if(t.properties.some(p=>p.name===prop.name)) return {ok:false,error:'属性重名: '+prop.name};
  if(!BASE_TYPES.includes(prop.baseType)) return {ok:false,error:'非法 baseType'};
  if(prop.baseType==='enum'&&(!Array.isArray(prop.enumValues)||!prop.enumValues.length)) return {ok:false,error:'enum 需给 enumValues'};
  t.properties.push({ name:prop.name, label:prop.label||prop.name, baseType:prop.baseType,
    enumValues:prop.enumValues||null, required:!!prop.required, formatting:prop.formatting||'' });
  _bump(state); return {ok:true};
}
function updateProperty(state,typeId,propName,patch){
  const t=_findType(state,typeId); if(!t) return {ok:false,error:'对象类型不存在'};
  const p=t.properties.find(p=>p.name===propName); if(!p) return {ok:false,error:'属性不存在'};
  if(patch.name!==undefined&&patch.name!==propName) return {ok:false,error:'不允许改属性 name'};
  for(const k of ['label','baseType','enumValues','required','formatting']) if(patch[k]!==undefined) p[k]=patch[k];
  if(p.baseType==='enum'&&(!Array.isArray(p.enumValues)||!p.enumValues.length)) return {ok:false,error:'enum 需给 enumValues'};
  _bump(state); return {ok:true};
}
function deleteProperty(state,typeId,propName){
  const t=_findType(state,typeId); if(!t) return {ok:false,error:'对象类型不存在'};
  if(t.primaryKey===propName) return {ok:false,error:'不可删除主键属性'};
  t.properties=t.properties.filter(p=>p.name!==propName); _bump(state); return {ok:true};
}
function addSharedProp(state,def){
  const s=schemaOf(state);
  if(!NAME_RE.test(def.name||'')) return {ok:false,error:'name 需为蛇形标识'};
  if(s.sharedProps.some(p=>p.name===def.name)) return {ok:false,error:'共享属性重名'};
  if(!BASE_TYPES.includes(def.baseType)) return {ok:false,error:'非法 baseType'};
  const sp={ id:uid('sp'), name:def.name, label:def.label||def.name, baseType:def.baseType, enumValues:def.enumValues||null };
  s.sharedProps.push(sp); _bump(state); return {ok:true,id:sp.id};
}
function attachSharedProp(state,typeId,spId){
  const t=_findType(state,typeId); if(!t) return {ok:false,error:'对象类型不存在'};
  if(!schemaOf(state).sharedProps.some(p=>p.id===spId)) return {ok:false,error:'共享属性不存在'};
  if(t.sharedPropRefs.includes(spId)) return {ok:false,error:'已挂载'};
  t.sharedPropRefs.push(spId); _bump(state); return {ok:true};
}
function detachSharedProp(state,typeId,spId){
  const t=_findType(state,typeId); if(!t) return {ok:false,error:'对象类型不存在'};
  t.sharedPropRefs=t.sharedPropRefs.filter(x=>x!==spId); _bump(state); return {ok:true};
}
function deleteSharedProp(state,spId){
  const s=schemaOf(state);
  if(!s.sharedProps.some(p=>p.id===spId)) return {ok:false,error:'共享属性不存在'};
  const usedBy=s.objectTypes.filter(t=>(t.sharedPropRefs||[]).includes(spId)).map(t=>t.name);
  if(usedBy.length) return {ok:false,error:'被 '+usedBy.join('、')+' 挂载中'};
  s.sharedProps=s.sharedProps.filter(p=>p.id!==spId); _bump(state); return {ok:true};
}
```

- [ ] **Step 4: 运行确认通过** — `node smoke.mjs` → 8 passed, 0 failed

- [ ] **Step 5: Commit**

```bash
git add ontoforge.html smoke.mjs
git commit -m "feat(core): 对象类型/属性/共享属性 CRUD"
```

---

### Task 3: CORE 链接类型与链接实例

**Files:**
- Modify: `ontoforge.html`(id="core" 段)
- Modify: `smoke.mjs`(追加 S2 节)

**Interfaces:**
- Consumes: Task 2 的 `_findType`、`_bump`、`NAME_RE`
- Produces:
  - `CORE.addLinkType(state,{name,label?,from,to,cardinality,keyMapping?}) → {ok,id?|error}` — from/to 为对象类型 **name**;cardinality ∈ `['1:1','1:N','N:1','M:N']`
  - `CORE.updateLinkType(state,id,patch) → {ok|error}` — label/keyMapping/cardinality 可改,from/to 不可改
  - `CORE.deleteLinkType(state,id) → {ok|error}` — 存在该类型 link 实例时拒绝
  - `CORE.createLink(state,linkTypeId,fromObjId,toObjId) → {ok,id?|error}` — 端点类型匹配;去重;`1:1` 双侧唯一、`N:1` from 侧唯一、`1:N` to 侧唯一、`M:N` 不约束
  - `CORE.deleteLink(state,linkId) → {ok|error}`
  - `CORE.linksOf(state,linkTypeId) → link[]`

- [ ] **Step 1: smoke 追加 S2(先确认 FAIL)**

```js
// ── S2 链接类型/链接实例 ──
function _twoTypes(){ const s=CORE.createEmptyState();
  const a=CORE.addObjectType(s,{name:'team'}).id, b=CORE.addObjectType(s,{name:'incident'}).id;
  s.data.objects.push({__id:'t1",__type:'team',props:{}},{__id:'t2',__type:'team',props:{}},{__id:'i1',__type:'incident',props:{}});
  return s; }
T('S2.1 建链接类型+端点校验', ()=>{
  const s=_twoTypes();
  ok(!CORE.addLinkType(s,{name:'x',from:'team',to:'ghost',cardinality:'M:N'}).ok,'端点不存在应拒绝');
  ok(!CORE.addLinkType(s,{name:'x',from:'team',to:'incident',cardinality:'9:9'}).ok,'非法基数应拒绝');
  ok(CORE.addLinkType(s,{name:'assigned',label:'派遣',from:'team',to:'incident',cardinality:'M:N',keyMapping:{fromKey:'team_id',toKey:'inc_id'}}).ok,'合法通过');
});
T('S2.2 链接实例:类型匹配/去重/基数', ()=>{
  const s=_twoTypes();
  const lt=CORE.addLinkType(s,{name:'assigned',from:'team',to:'incident',cardinality:'M:N'}).id;
  ok(!CORE.createLink(s,lt,'i1','t1').ok,'端点方向错应拒绝');
  ok(CORE.createLink(s,lt,'t1','i1').ok,'正向通过');
  ok(!CORE.createLink(s,lt,'t1','i1').ok,'重复对拒绝');
  ok(CORE.createLink(s,lt,'t2','i1').ok,'M:N 多方允许');
  ok(!CORE.deleteLinkType(s,lt).ok,'有实例时删 linkType 拒绝');
});
T('S2.3 N:1 唯一性', ()=>{
  const s=_twoTypes();
  const lt=CORE.addLinkType(s,{name:'on',from:'incident',to:'team',cardinality:'N:1'}).id;
  ok(CORE.createLink(s,lt,'i1','t1').ok,'首条通过');
  ok(!CORE.createLink(s,lt,'i1','t2').ok,'N:1 from 侧重复拒绝');
  ok(CORE.deleteLink(s,CORE.linksOf(s,lt)[0].__id).ok,'删链接');
  ok(CORE.createLink(s,lt,'i1','t2').ok,'删后可重建');
});
```

- [ ] **Step 2: 运行确认 FAIL** — `node smoke.mjs` → S2.x FAIL,S0/S1/S8 绿

- [ ] **Step 3: CORE 追加实现**

```js
const CARDINALITIES=['1:1','1:N','N:1','M:N'];
function _typeByName(state,name){ return schemaOf(state).objectTypes.find(t=>t.name===name); }
function addLinkType(state,def){
  const s=schemaOf(state);
  if(!NAME_RE.test(def.name||'')) return {ok:false,error:'name 需为蛇形标识'};
  if(s.linkTypes.some(l=>l.name===def.name)) return {ok:false,error:'链接类型重名'};
  if(!_typeByName(state,def.from)) return {ok:false,error:'from 类型不存在: '+def.from};
  if(!_typeByName(state,def.to)) return {ok:false,error:'to 类型不存在: '+def.to};
  if(!CARDINALITIES.includes(def.cardinality)) return {ok:false,error:'非法 cardinality'};
  const lt={ id:uid('lt'), name:def.name, label:def.label||def.name, from:def.from, to:def.to,
             cardinality:def.cardinality, keyMapping:def.keyMapping||{fromKey:'',toKey:''} };
  s.linkTypes.push(lt); _bump(state); return {ok:true,id:lt.id};
}
function updateLinkType(state,id,patch){
  const lt=schemaOf(state).linkTypes.find(l=>l.id===id); if(!lt) return {ok:false,error:'链接类型不存在'};
  if(patch.from!==undefined||patch.to!==undefined) return {ok:false,error:'不可改 from/to'};
  if(patch.cardinality!==undefined){ if(!CARDINALITIES.includes(patch.cardinality)) return {ok:false,error:'非法 cardinality'}; lt.cardinality=patch.cardinality; }
  if(patch.label!==undefined) lt.label=patch.label;
  if(patch.keyMapping!==undefined) lt.keyMapping=patch.keyMapping;
  _bump(state); return {ok:true};
}
function deleteLinkType(state,id){
  const s=schemaOf(state);
  if(state.data.links.some(l=>l.__type===id)) return {ok:false,error:'存在该类型链接实例,不可删除'};
  s.linkTypes=s.linkTypes.filter(l=>l.id!==id); _bump(state); return {ok:true};
}
function createLink(state,linkTypeId,fromObjId,toObjId){
  const lt=schemaOf(state).linkTypes.find(l=>l.id===linkTypeId); if(!lt) return {ok:false,error:'链接类型不存在'};
  const fo=state.data.objects.find(o=>o.__id===fromObjId), to=state.data.objects.find(o=>o.__id===toObjId);
  if(!fo||!to) return {ok:false,error:'端点对象不存在'};
  if(fo.__type!==lt.from||to.__type!==lt.to) return {ok:false,error:`端点类型须为 ${lt.from} → ${lt.to}`};
  const L=state.data.links;
  if(L.some(l=>l.__type===linkTypeId&&l.from===fromObjId&&l.to===toObjId)) return {ok:false,error:'链接已存在'};
  const fromSide=l=>l.__type===linkTypeId&&l.from===fromObjId, toSide=l=>l.__type===linkTypeId&&l.to===toObjId;
  if((lt.cardinality==='1:1'||lt.cardinality==='N:1')&&L.some(fromSide)) return {ok:false,error:'基数约束:from 侧已有关联'};
  if((lt.cardinality==='1:1'||lt.cardinality==='1:N')&&L.some(toSide)) return {ok:false,error:'基数约束:to 侧已有关联'};
  const link={ __id:uid('lk'), __type:linkTypeId, from:fromObjId, to:toObjId };
  L.push(link); return {ok:true,id:link.__id};
}
function deleteLink(state,linkId){
  const n=state.data.links.length;
  state.data.links=state.data.links.filter(l=>l.__id!==linkId);
  return state.data.links.length<n?{ok:true}:{ok:false,error:'链接不存在'};
}
function linksOf(state,linkTypeId){ return state.data.links.filter(l=>l.__type===linkTypeId); }
```

(导出表追加:`addLinkType,updateLinkType,deleteLinkType,createLink,deleteLink,linksOf,CARDINALITIES`)

- [ ] **Step 4: 运行确认通过** — `node smoke.mjs` → 11 passed, 0 failed

- [ ] **Step 5: Commit**

```bash
git add ontoforge.html smoke.mjs
git commit -m "feat(core): 链接类型与链接实例(基数约束)"
```

---

### Task 4: CORE 动作类型 CRUD + 模板渲染

**Files:**
- Modify: `ontoforge.html`(id="core" 段)
- Modify: `smoke.mjs`(追加 S3 节)

**Interfaces:**
- Consumes: 前序全部
- Produces:
  - `CORE.addActionType(state,def) → {ok,id?|error}` — def 结构:`{name,label?,targets:[{role,type}],params:[{name,label?,type,required?,enumValues?}],rules:[{target,field,op,value,message}],submissionCriteria:{requireConfirm:boolean,note?},edits:[{op,target?,objectType?,field?,value?,linkType?,from?,to?,props?}],sideEffects:[{type:'notify'|'webhookLog',config}]}`
  - `CORE.updateActionType(state,id,patch) → {ok|error}`(整体替换除 name 外字段,复用同一校验)
  - `CORE.deleteActionType(state,id) → {ok|error}`
  - `CORE.renderTemplate(tpl,ctx) → string` — `{{param.x}}` / `{{targets.role.prop}}` / `{{now}}` / `{{auto}}`
  - 校验规则:targets[].type 须为存在的对象类型 name,role 唯一且 `^[a-z][a-z0-9_]*$`;params[].name 唯一;rules[].op ∈ RULE_OPS;edits[].op ∈ `['set','create','delete','addLink','removeLink']`;create 必须给 objectType+props;addLink/removeLink 必须给 linkType+from+to;sideEffects[].type ∈ `['notify','webhookLog']`

- [ ] **Step 1: smoke 追加 S3(先确认 FAIL)**

```js
// ── S3 动作类型定义/模板 ──
T('S3.1 动作类型 CRUD+结构校验', ()=>{
  const s=CORE.createEmptyState();
  CORE.addObjectType(s,{name:'incident'}); CORE.addObjectType(s,{name:'team'});
  const bad=CORE.addActionType(s,{name:'a1',targets:[{role:'t',type:'ghost'}],params:[],rules:[],edits:[],sideEffects:[]});
  ok(!bad.ok,'target 类型不存在应拒绝');
  const def={ name:'dispatch', label:'派遣',
    targets:[{role:'team',type:'team'},{role:'inc',type:'incident'}],
    params:[{name:'note',type:'string',required:false}],
    rules:[{target:'team',field:'status',op:'eq',value:'待命',message:'仅待命可派遣'}],
    submissionCriteria:{requireConfirm:true},
    edits:[{op:'set',target:'team',field:'status',value:'出动'}],
    sideEffects:[{type:'notify',config:{to:'调度中心',text:'已派遣'}}] };
  const r=CORE.addActionType(s,def); ok(r.ok,r.error);
  ok(!CORE.addActionType(s,def).ok,'重名拒绝');
  ok(CORE.updateActionType(s,r.id,{label:'派遣队伍'}).ok,'改 label');
  ok(CORE.deleteActionType(s,r.id).ok,'删除');
});
T('S3.2 模板渲染', ()=>{
  const ctx={param:{title:'追尾'},targets:{inc:{props:{status:'处理中'}}},now:'2026-10-17',auto:'x_1'};
  eq(CORE.renderTemplate('上报:{{param.title}}/{{targets.inc.props.status}}',ctx),'上报:追尾/处理中');
  eq(CORE.renderTemplate('{{missing.deep}}',ctx),'','缺路径给空串');
  eq(CORE.renderTemplate('{{now}}#{{auto}}',ctx),'2026-10-17#x_1');
});
```

- [ ] **Step 2: 运行确认 FAIL** — S3.x FAIL

- [ ] **Step 3: CORE 追加实现**

```js
const EDIT_OPS=['set','create','delete','addLink','removeLink'];
function renderTemplate(tpl,ctx){
  if(typeof tpl!=='string') return tpl;
  return tpl.replace(/\{\{\s*([^}]+?)\s*\}\}/g,(m,path)=>{
    const v=path.trim().split('.').reduce((o,k)=>(o==null?o:o[k]),ctx);
    return v==null?'':String(v);
  });
}
function _validateActionDef(state,def,excludeId){
  const s=schemaOf(state);
  if(!NAME_RE.test(def.name||'')) return 'name 需为蛇形标识';
  if(s.actionTypes.some(a=>a.name===def.name&&a.id!==excludeId)) return '动作类型重名';
  const roles=new Set();
  for(const t of (def.targets||[])){
    if(!NAME_RE.test(t.role||'')) return 'target role 需为蛇形标识';
    if(roles.has(t.role)) return 'target role 重复: '+t.role;
    roles.add(t.role);
    if(!_typeByName(state,t.type)) return 'target 类型不存在: '+t.type;
  }
  const pnames=new Set();
  for(const p of (def.params||[])){
    if(!NAME_RE.test(p.name||'')) return '参数 name 需为蛇形标识';
    if(pnames.has(p.name)) return '参数重名: '+p.name;
    pnames.add(p.name);
    if(!BASE_TYPES.includes(p.type)) return '参数非法 type: '+p.type;
    if(p.type==='enum'&&(!Array.isArray(p.enumValues)||!p.enumValues.length)) return 'enum 参数需 enumValues';
  }
  for(const r of (def.rules||[])) if(!RULE_OPS.includes(r.op)) return '规则非法 op: '+r.op;
  for(const e of (def.edits||[])){
    if(!EDIT_OPS.includes(e.op)) return 'edit 非法 op: '+e.op;
    if(e.op==='create'&&(!e.objectType||!e.props||typeof e.props!=='object')) return 'create edit 需 objectType+props';
    if(e.op==='create'&&!_typeByName(state,e.objectType)) return 'create 的类型不存在: '+e.objectType;
    if((e.op==='addLink'||e.op==='removeLink')&&!(e.linkType&&e.from&&e.to)) return e.op+' 需 linkType+from+to';
    if((e.op==='addLink'||e.op==='removeLink')&&e.linkType&&!schemaOf(state).linkTypes.some(l=>l.id===e.linkType||l.name===e.linkType)) return 'linkType 不存在: '+e.linkType;
  }
  for(const f of (def.sideEffects||[])) if(!['notify','webhookLog'].includes(f.type)) return '非法副作用: '+f.type;
  return null;
}
function addActionType(state,def){
  const err=_validateActionDef(state,def,null); if(err) return {ok:false,error:err};
  const at={ id:uid('at'), name:def.name, label:def.label||def.name,
    targets:def.targets||[], params:def.params||[], rules:def.rules||[],
    submissionCriteria:def.submissionCriteria||{requireConfirm:false},
    edits:def.edits||[], sideEffects:def.sideEffects||[] };
  schemaOf(state).actionTypes.push(at); _bump(state); return {ok:true,id:at.id};
}
function updateActionType(state,id,patch){
  const s=schemaOf(state); const at=s.actionTypes.find(a=>a.id===id); if(!at) return {ok:false,error:'动作类型不存在'};
  const merged=Object.assign({},at,patch,{id,name:at.name});
  const err=_validateActionDef(state,merged,id); if(err) return {ok:false,error:err};
  Object.assign(at,merged); _bump(state); return {ok:true};
}
function deleteActionType(state,id){
  const s=schemaOf(state);
  s.actionTypes=s.actionTypes.filter(a=>a.id!==id); _bump(state); return {ok:true};
}
```

(导出表追加:`addActionType,updateActionType,deleteActionType,renderTemplate,EDIT_OPS`)

- [ ] **Step 4: 运行确认通过** — `node smoke.mjs` → 13 passed, 0 failed

- [ ] **Step 5: Commit**

```bash
git add ontoforge.html smoke.mjs
git commit -m "feat(core): 动作类型 CRUD + 模板渲染"
```

---

### Task 5: CORE runAction 执行引擎(闭环核心)

**Files:**
- Modify: `ontoforge.html`(id="core" 段)
- Modify: `smoke.mjs`(追加 S4 节)

**Interfaces:**
- Consumes: Task 4 的 `renderTemplate`、EDIT_OPS;Task 3 的 `createLink`(引擎内部用其校验逻辑,但作用于**克隆数据**,见下)
- Produces:
  - `CORE.runAction(state,actionId,{params,targets,actor?,confirmed?}) → {ok:true,changes}|{ok:false,error}|{ok:false,needConfirm:true,preview:[string]}`
  - `CORE.describeEdits(state,at,ctx) → string[]`(预览与审计摘要共用)
  - 副作用落地:`notify` → `state.notices.push({id,ts,to,text,read:false,actionId})`;`webhookLog` → 审计 entry 的 `effects` 里记 `{type:'webhookLog',note}`
  - 审计 entry:`{id,ts,branch,actor,actionId,actionLabel,summary,diff:[string],effects:[]}`
  - **原子性**:edits 在 `clone(state.data)` 上模拟,全部成功才 `state.data=sim`;任一步失败 state 不变
  - ctx 内建:`{param,targets:{role:obj},target:首个 target,now:YYYY-MM-DD,auto:uid('obj')}`(`auto` 每次求值生成新 id — 在 renderTemplate 包装层处理)

- [ ] **Step 1: smoke 追加 S4(先确认 FAIL)**

```js
// ── S4 runAction 引擎 ──
function _engineWorld(){
  const s=CORE.createEmptyState();
  CORE.addObjectType(s,{name:'team'}); CORE.addObjectType(s,{name:'incident'});
  const tid=CORE.schemaOf(s).objectTypes.find(t=>t.name==='team').id;
  CORE.addProperty(s,tid,{name:'status',baseType:'enum',enumValues:['待命','出动']});
  CORE.addLinkType(s,{name:'assigned',from:'team',to:'incident',cardinality:'M:N'});
  s.data.objects.push({__id:'t1',__type:'team',props:{status:'待命'}},{__id:'t2',__type:'team',props:{status:'出动'}},{__id:'i1',__type:'incident',props:{status:'处理中'}});
  return s;
}
const _dispatchDef={ name:'dispatch', targets:[{role:'team',type:'team'},{role:'inc',type:'incident'}],
  params:[{name:'prio',type:'enum',enumValues:['高','低'],required:true}],
  rules:[{target:'team',field:'status',op:'eq',value:'待命',message:'仅待命队伍可派遣'}],
  submissionCriteria:{requireConfirm:true},
  edits:[ {op:'set',target:'team',field:'status',value:'出动'},
          {op:'addLink',linkType:'assigned',from:'team',to:'inc'} ],
  sideEffects:[{type:'notify',config:{to:'调度',text:'{{param.prio}}优先级派遣'}},{type:'webhookLog',config:{url:'http://hook'}}] };
T('S4.1 参数校验', ()=>{
  const s=_engineWorld(); CORE.addActionType(s,_dispatchDef);
  const aid=CORE.schemaOf(s).actionTypes[0].id;
  const r=CORE.runAction(s,aid,{params:{},targets:{team:'t1',inc:'i1'}});
  ok(!r.ok&&!r.needConfirm,'缺必填参数应失败'); ok(/prio/.test(r.error),'错误点名参数');
});
T('S4.2 规则校验', ()=>{
  const s=_engineWorld(); CORE.addActionType(s,_dispatchDef);
  const aid=CORE.schemaOf(s).actionTypes[0].id;
  const r=CORE.runAction(s,aid,{params:{prio:'高'},targets:{team:'t2',inc:'i1'}});
  ok(!r.ok&&r.error==='仅待命队伍可派遣','规则 message 原样返回');
});
T('S4.3 确认门槛+预览', ()=>{
  const s=_engineWorld(); CORE.addActionType(s,_dispatchDef);
  const aid=CORE.schemaOf(s).actionTypes[0].id;
  const r=CORE.runAction(s,aid,{params:{prio:'高'},targets:{team:'t1',inc:'i1'}});
  ok(!r.ok&&r.needConfirm===true,'应要求确认');
  ok(r.preview.length>=2,'预览至少两条'); ok(!s.audit.length,'未确认不写审计');
  ok(s.data.objects.find(o=>o.__id==='t1').props.status==='待命','未确认不改数据');
});
T('S4.4 成功路径:edits+副作用+审计', ()=>{
  const s=_engineWorld(); CORE.addActionType(s,_dispatchDef);
  const aid=CORE.schemaOf(s).actionTypes[0].id;
  const r=CORE.runAction(s,aid,{params:{prio:'高'},targets:{team:'t1',inc:'i1'},confirmed:true,actor:'张三'});
  ok(r.ok,r.error);
  eq(s.data.objects.find(o=>o.__id==='t1').props.status,'出动','set 生效');
  eq(s.data.links.length,1,'addLink 生效');
  eq(s.notices.length,1,'notify 进通知中心');
  ok(s.notices[0].text.includes('高'),'通知文本模板渲染');
  eq(s.audit.length,1,'审计一条');
  eq(s.audit[0].actor,'张三','审计记录 actor');
  ok(s.audit[0].effects.some(e=>e.type==='webhookLog'),'webhookLog 记入审计');
});
T('S4.5 原子性:中途失败不留痕', ()=>{
  const s=_engineWorld();
  CORE.addActionType(s,{ name:'bad', targets:[{role:'team',type:'team'}], params:[], rules:[],
    submissionCriteria:{requireConfirm:false},
    edits:[ {op:'set',target:'team',field:'status',value:'出动'},
            {op:'addLink',linkType:'assigned',from:'team',to:'ghost_role'} ],
    sideEffects:[] });
  const aid=CORE.schemaOf(s).actionTypes[0].id;
  const r=CORE.runAction(s,aid,{params:{},targets:{team:'t1'},confirmed:true});
  ok(!r.ok,'应失败');
  eq(s.data.objects.find(o=>o.__id==='t1').props.status,'待命','数据回滚');
  eq(s.audit.length,0,'不留审计');
});
T('S4.6 create edit + auto/now', ()=>{
  const s=_engineWorld();
  CORE.addActionType(s,{ name:'report', targets:[], params:[{name:'title',type:'string',required:true}], rules:[],
    submissionCriteria:{requireConfirm:false},
    edits:[{op:'create',target:'inc',objectType:'incident',props:{title:'{{param.title}}',reported:'{{now}}',code:'{{auto}}'}}],
    sideEffects:[] });
  const aid=CORE.schemaOf(s).actionTypes[0].id;
  const r=CORE.runAction(s,aid,{params:{title:'追尾'},targets:{},confirmed:true});
  ok(r.ok,r.error);
  const inc=s.data.objects.find(o=>o.props&&o.props.title==='追尾');
  ok(inc,'新对象创建'); ok(/^\d{4}-\d{2}-\d{2}$/.test(inc.props.reported),'now 渲染为日期');
  ok(inc.props.code&&inc.props.code!=='{{auto}}','auto 渲染为新 id');
});
```

- [ ] **Step 2: 运行确认 FAIL** — S4.x FAIL

- [ ] **Step 3: CORE 追加实现(引擎,约 130 行)**

```js
function _today(){ return new Date().toISOString().slice(0,10); }
function _mkCtx(state,at,params,targets){
  const resolved={};
  for(const t of at.targets){
    const oid=targets[t.role];
    const obj=state.data.objects.find(o=>o.__id===oid);
    if(!obj) return {error:'target 对象不存在: '+t.role};
    if(obj.__type!==t.type) return {error:`target ${t.role} 须为 ${t.type}`};
    resolved[t.role]=obj;
  }
  const roles=Object.keys(resolved);
  return { ctx:{ param:params, targets:resolved, target:roles.length?resolved[roles[0]]:null, now:_today() } };
}
function _renderCtx(ctx){
  // 每次渲染提供新 auto id
  return Object.assign({},ctx,{ get auto(){ return uid('obj'); } });
}
function _validateParams(at,params){
  for(const p of at.params){
    const v=params[p.name];
    if(p.required&&(v===undefined||v===null||v==='')) return '参数必填: '+p.name;
    if(v===undefined||v===null||v==='') continue;
    if(p.type==='number'&&isNaN(Number(v))) return '参数须为数字: '+p.name;
    if(p.type==='enum'&&!p.enumValues.includes(v)) return '参数取值非法: '+p.name;
  }
  return null;
}
function _ruleLeft(ctx,target,field){
  if(target==='param') return ctx.param[field];
  const obj=ctx.targets[target];
  return obj?obj.props[field]:undefined;
}
function _checkRules(at,ctx){
  for(const r of at.rules){
    const left=_ruleLeft(ctx,r.target,r.field);
    const right=renderTemplate(String(r.value),ctx);
    const vals=String(right).split('|');
    let hit=false;
    switch(r.op){
      case 'eq': hit=String(left)===right; break;
      case 'neq': hit=String(left)!==right; break;
      case 'in': hit=vals.includes(String(left)); break;
      case 'notIn': hit=!vals.includes(String(left)); break;
      case 'gt': hit=Number(left)>Number(right); break;
      case 'lt': hit=Number(left)<Number(right); break;
      case 'ge': hit=Number(left)>=Number(right); break;
      case 'le': hit=Number(left)<=Number(right); break;
      case 'contains': hit=String(left??'').includes(right); break;
    }
    if(!hit) return r.message||`规则未通过:${r.target}.${r.field} ${r.op} ${r.value}`;
  }
  return null;
}
function _applyEditsSim(state,at,ctx){
  const sim=clone(state.data); const changes=[];
  const simObj=(role)=>{ const real=ctx.targets[role]; return real?sim.objects.find(o=>o.__id===real.__id):null; };
  const newObjs={};
  for(const e of at.edits){
    if(e.op==='set'){
      const o=simObj(e.target)||newObjs[e.target];
      if(!o) return {error:'set 目标不存在: '+e.target};
      const v=renderTemplate(e.value,_renderCtx(ctx));
      changes.push(`${e.target}.${e.field}: ${o.props[e.field]??'∅'} → ${v}`);
      o.props[e.field]=v;
    } else if(e.op==='create'){
      const props={};
      for(const [k,tpl] of Object.entries(e.props)) props[k]=renderTemplate(tpl,_renderCtx(ctx));
      const obj={ __id:uid('obj'), __type:e.objectType, props };
      sim.objects.push(obj); if(e.target) newObjs[e.target]=obj;
      changes.push(`新建 ${e.objectType}(${e.target||obj.__id})`);
    } else if(e.op==='delete'){
      const o=simObj(e.target); if(!o) return {error:'delete 目标不存在: '+e.target};
      sim.objects=sim.objects.filter(x=>x.__id!==o.__id);
      sim.links=sim.links.filter(l=>l.from!==o.__id&&l.to!==o.__id);
      changes.push(`删除 ${e.target}(${o.__id})`);
    } else if(e.op==='addLink'||e.op==='removeLink'){
      const lt=schemaOf(state).linkTypes.find(l=>l.id===e.linkType||l.name===e.linkType);
      const fo=(simObj(e.from)||newObjs[e.from]), to=(simObj(e.to)||newObjs[e.to]);
      if(!lt) return {error:'linkType 不存在: '+e.linkType};
      if(!fo||!to) return {error:e.op+' 端点角色未解析: '+e.from+'/'+e.to};
      if(fo.__type!==lt.from||to.__type!==lt.to) return {error:`链接端点类型须为 ${lt.from} → ${lt.to}`};
      if(e.op==='addLink'){
        if(sim.links.some(l=>l.__type===lt.id&&l.from===fo.__id&&l.to===to.__id)) return {error:'链接已存在(基数/重复)'};
        const fromSide=l=>l.__type===lt.id&&l.from===fo.__id, toSide=l=>l.__type===lt.id&&l.to===to.__id;
        if((lt.cardinality==='1:1'||lt.cardinality==='N:1')&&sim.links.some(fromSide)) return {error:'基数约束:from 侧已有关联'};
        if((lt.cardinality==='1:1'||lt.cardinality==='1:N')&&sim.links.some(toSide)) return {error:'基数约束:to 侧已有关联'};
        sim.links.push({__id:uid('lk'),__type:lt.id,from:fo.__id,to:to.__id});
        changes.push(`建链接 ${lt.name}:${e.from} → ${e.to}`);
      } else {
        const n=sim.links.length;
        sim.links=sim.links.filter(l=>!(l.__type===lt.id&&l.from===fo.__id&&l.to===to.__id));
        if(sim.links.length===n) return {error:'待删链接不存在'};
        changes.push(`删链接 ${lt.name}:${e.from} → ${e.to}`);
      }
    }
  }
  // create 产生的对象补充进 ctx.targets 供后续 edits/模板引用
  for(const [role,obj] of Object.entries(newObjs)) ctx.targets[role]=obj;
  return { sim, changes };
}
function describeEdits(state,at,ctx){
  const r=_applyEditsSim(state,at,clone(ctx));
  if(r.error) return ['(预览失败) '+r.error];
  return r.changes;
}
function runAction(state,actionId,input){
  const at=schemaOf(state).actionTypes.find(a=>a.id===actionId);
  if(!at) return {ok:false,error:'动作不存在'};
  const params=input.params||{}, targets=input.targets||{};
  const pe=_validateParams(at,params); if(pe) return {ok:false,error:pe};
  const cr=_mkCtx(state,at,params,targets); if(cr.error) return {ok:false,error:cr.error};
  const ctx=cr.ctx;
  const re=_checkRules(at,ctx); if(re) return {ok:false,error:re};
  if(at.submissionCriteria&&at.submissionCriteria.requireConfirm&&!input.confirmed){
    return {ok:false,needConfirm:true,preview:describeEdits(state,at,ctx)};
  }
  const r=_applyEditsSim(state,at,ctx);
  if(r.error) return {ok:false,error:r.error};
  state.data=r.sim;
  const effects=[];
  for(const f of at.sideEffects){
    if(f.type==='notify'){
      const text=renderTemplate((f.config&&f.config.text)||'',ctx);
      state.notices.push({ id:uid('nt'), ts:new Date().toISOString(), to:(f.config&&f.config.to)||'', text, read:false, actionId });
      effects.push({type:'notify',text});
    } else if(f.type==='webhookLog'){
      effects.push({type:'webhookLog',note:'已记录 webhook 调用(原型不落网)'});
    }
  }
  state.audit.push({ id:uid('au'), ts:new Date().toISOString(), branch:state.branch.current,
    actor:input.actor||'本地用户', actionId, actionLabel:at.label,
    summary:`${at.label} · ${r.changes.length} 项变更`, diff:r.changes, effects });
  return {ok:true,changes:r.changes};
}
```

(导出表追加:`runAction,describeEdits`)

- [ ] **Step 4: 运行确认通过** — `node smoke.mjs` → 19 passed, 0 failed

- [ ] **Step 5: Commit**

```bash
git add ontoforge.html smoke.mjs
git commit -m "feat(core): runAction 执行引擎(校验/确认/原子 edits/副作用/审计)"
```

---

### Task 6: CORE 查询 / 搜索 / 审计统计

**Files:**
- Modify: `ontoforge.html`(id="core" 段)
- Modify: `smoke.mjs`(追加 S5 节)

**Interfaces:**
- Consumes: 前序全部
- Produces:
  - `CORE.objectsOfType(state,typeName) → obj[]`
  - `CORE.objectLabel(state,obj) → string` — 依次取 `props.name`、`props.title`、`props[primaryKey]`、`__id`
  - `CORE.searchObjects(state,typeName,q) → obj[]` — 大小写不敏感,匹配所有 string 属性值
  - `CORE.linkedObjects(state,objectId) → [{linkType,direction:'out'|'in',object}]`
  - `CORE.auditFor(state,{actionId?,objectId?}) → entry[]` — objectId 匹配 diff 文本中该对象角色或 __id
  - `CORE.usageByDay(state,actionId,days=30) → [{day:'YYYY-MM-DD',count}]`(含 0 填充,升序)
  - `CORE.unreadNotices(state) → number`;`CORE.markNoticesRead(state)`

- [ ] **Step 1: smoke 追加 S5(先确认 FAIL)**

```js
// ── S5 查询/搜索/审计统计 ──
function _queryWorld(){
  const s=CORE.createEmptyState();
  CORE.addObjectType(s,{name:'seg'}); CORE.addObjectType(s,{name:'inc'});
  const sid=CORE.schemaOf(s).objectTypes.find(t=>t.name==='seg').id;
  CORE.addProperty(s,sid,{name:'name',baseType:'string'});
  CORE.addProperty(s,sid,{name:'level',baseType:'string'});
  CORE.updateObjectType(s,sid,{primaryKey:'name'});
  CORE.addLinkType(s,{name:'on',from:'inc',to:'seg',cardinality:'N:1'});
  s.data.objects.push(
    {__id:'g1',__type:'seg',props:{name:'成渝立交',level:'高速'}},
    {__id:'g2',__type:'seg',props:{name:'机场快速',level:'主干'}},
    {__id:'e1',__type:'inc',props:{title:'两车追尾'}});
  CORE.createLink(s,CORE.schemaOf(s).linkTypes[0].id,'e1','g1');
  return s;
}
T('S5.1 查询与 label', ()=>{
  const s=_queryWorld();
  eq(CORE.objectsOfType(s,'seg').length,2,'两段');
  eq(CORE.objectLabel(s,s.data.objects[0]),'成渝立交','name 优先');
});
T('S5.2 搜索大小写不敏感+跨属性', ()=>{
  const s=_queryWorld();
  eq(CORE.searchObjects(s,'seg','高速').length,1,'按 level 命中');
  eq(CORE.searchObjects(s,'seg','成渝').length,1,'按 name 命中');
  eq(CORE.searchObjects(s,'seg','').length,2,'空串全量');
});
T('S5.3 关联遍历', ()=>{
  const s=_queryWorld();
  const r=CORE.linkedObjects(s,'e1');
  eq(r.length,1,'一条出边'); eq(r[0].direction,'out'); eq(r[0].object.__id,'g1');
  eq(CORE.linkedObjects(s,'g1')[0].direction,'in','反向 in');
});
T('S5.4 审计过滤与用量柱状', ()=>{
  const s=_queryWorld();
  CORE.addActionType(s,{name:'ping',targets:[{role:'x',type:'seg'}],params:[],rules:[],
    submissionCriteria:{requireConfirm:false},edits:[{op:'set',target:'x',field:'level',value:'拥堵'}],sideEffects:[]});
  const aid=CORE.schemaOf(s).actionTypes[0].id;
  CORE.runAction(s,aid,{params:{},targets:{x:'g1'},confirmed:true});
  CORE.runAction(s,aid,{params:{},targets:{x:'g2'},confirmed:true});
  eq(CORE.auditFor(s,{actionId:aid}).length,2,'按 action 过滤');
  eq(CORE.auditFor(s,{objectId:'g1'}).length,1,'按对象过滤');
  const u=CORE.usageByDay(s,aid,30);
  eq(u.length,30,'30 天'); eq(u[u.length-1].count,2,'今天 2 次');
  eq(CORE.unreadNotices(s),0,'无通知');
});
```

- [ ] **Step 2: 运行确认 FAIL** — S5.x FAIL

- [ ] **Step 3: CORE 追加实现**

```js
function objectsOfType(state,typeName){ return state.data.objects.filter(o=>o.__type===typeName); }
function objectLabel(state,obj){
  const t=_typeByName(state,obj.__type);
  return obj.props.name||obj.props.title||(t&&t.primaryKey?obj.props[t.primaryKey]:null)||obj.__id;
}
function searchObjects(state,typeName,q){
  const all=objectsOfType(state,typeName);
  if(!q) return all;
  const needle=String(q).toLowerCase();
  return all.filter(o=>Object.values(o.props).some(v=>typeof v==='string'&&v.toLowerCase().includes(needle)));
}
function linkedObjects(state,objectId){
  const s=schemaOf(state); const out=[];
  for(const l of state.data.links){
    const lt=s.linkTypes.find(x=>x.id===l.__type); if(!lt) continue;
    if(l.from===objectId){ const o=state.data.objects.find(o=>o.__id===l.to); if(o) out.push({linkType:lt,direction:'out',object:o}); }
    if(l.to===objectId){ const o=state.data.objects.find(o=>o.__id===l.from); if(o) out.push({linkType:lt,direction:'in',object:o}); }
  }
  return out;
}
function auditFor(state,filter){
  return state.audit.filter(e=>{
    if(filter.actionId&&e.actionId!==filter.actionId) return false;
    if(filter.objectId){
      const hit=e.diff.some(d=>d.includes(filter.objectId));
      const obj=state.data.objects.find(o=>o.__id===filter.objectId);
      const hitRole=obj&&e.diff.some(d=>d.includes(obj.__type));
      if(!hit&&!hitRole) return false;
    }
    return true;
  });
}
function usageByDay(state,actionId,days){
  days=days||30; const map={};
  for(const e of state.audit) if(e.actionId===actionId){ const d=e.ts.slice(0,10); map[d]=(map[d]||0)+1; }
  const out=[]; const today=new Date();
  for(let i=days-1;i>=0;i--){
    const d=new Date(today.getTime()-i*86400000).toISOString().slice(0,10);
    out.push({day:d,count:map[d]||0});
  }
  return out;
}
function unreadNotices(state){ return state.notices.filter(n=>!n.read).length; }
function markNoticesRead(state){ state.notices.forEach(n=>n.read=true); }
```

(导出表追加:`objectsOfType,objectLabel,searchObjects,linkedObjects,auditFor,usageByDay,unreadNotices,markNoticesRead`)

- [ ] **Step 4: 运行确认通过** — `node smoke.mjs` → 23 passed, 0 failed

- [ ] **Step 5: Commit**

```bash
git add ontoforge.html smoke.mjs
git commit -m "feat(core): 查询/搜索/关联遍历/审计统计"
```

---

### Task 7: CORE 分支 / diff / 提案合并

**Files:**
- Modify: `ontoforge.html`(id="core" 段)
- Modify: `smoke.mjs`(追加 S6 节)

**Interfaces:**
- Consumes: `schemaOf`、`clone`、`_bump`
- Produces:
  - `CORE.createBranch(state,name) → {ok|error}` — name 唯一、`^[a-z][a-z0-9-]*$`;深克隆 **main** schema 为起点;切到该分支
  - `CORE.switchBranch(state,name) → {ok|error}`
  - `CORE.diffSchemas(a,b) → {objectTypes:{added,removed,changed},linkTypes:{…},actionTypes:{…},sharedProps:{…}}` — 按 name 对齐;changed 为去 id 后 JSON 不同者,元素 `{name,before,after}`
  - `CORE.diffEmpty(diff) → boolean`
  - `CORE.proposeMerge(state,branchName) → {ok,proposalId?|error}` — 当前须在 main;diff 为空报错「无变更」;同分支已有 open 提案报错
  - `CORE.mergeProposal(state,proposalId) → {ok|error}` — main schema 整换为分支 schema 深克隆,rev++,提案 status='merged',分支 status='merged'
  - `CORE.rejectProposal(state,proposalId) → {ok|error}` — status='rejected'

- [ ] **Step 1: smoke 追加 S6(先确认 FAIL)**

```js
// ── S6 分支/diff/合并 ──
T('S6.1 建分支+隔离 schema', ()=>{
  const s=CORE.createEmptyState();
  CORE.addObjectType(s,{name:'seg'});
  ok(CORE.createBranch(s,'feature-x').ok,'建分支');
  eq(s.branch.current,'feature-x','切到新分支');
  CORE.addObjectType(s,{name:'tunnel'});          // 分支上加类型
  eq(CORE.schemaOf(s).objectTypes.length,2,'分支 2 类');
  CORE.switchBranch(s,'main');
  eq(CORE.schemaOf(s).objectTypes.length,1,'main 仍 1 类(隔离)');
});
T('S6.2 diff 三类变更', ()=>{
  const s=CORE.createEmptyState();
  CORE.addObjectType(s,{name:'seg',label:'路段'});
  CORE.createBranch(s,'b1');
  CORE.addObjectType(s,{name:'tunnel'});
  const tid=CORE.schemaOf(s).objectTypes.find(t=>t.name==='seg').id;
  CORE.updateObjectType(s,tid,{label:'路段v2'});
  CORE.switchBranch(s,'main');
  CORE.addObjectType(s,{name:'temp_del'});
  // 注意:diff 是 main→branch;temp_del 在 branch 不存在 → removed
  const d=CORE.diffSchemas(s.schemas.main,s.schemas['b1']);
  ok(d.objectTypes.added.some(t=>t.name==='tunnel'),'added 含 tunnel');
  ok(d.objectTypes.changed.some(c=>c.name==='seg'),'changed 含 seg');
  ok(!CORE.diffEmpty(d),'非空 diff');
});
T('S6.3 提案→合并', ()=>{
  const s=CORE.createEmptyState();
  CORE.addObjectType(s,{name:'seg'});
  CORE.createBranch(s,'b1'); CORE.addObjectType(s,{name:'tunnel'});
  CORE.switchBranch(s,'main');
  const p=CORE.proposeMerge(s,'b1');
  ok(p.ok,p.error);
  ok(!CORE.proposeMerge(s,'b1').ok,'重复 open 提案拒绝');
  ok(CORE.mergeProposal(s,p.proposalId).ok,'合并');
  eq(CORE.schemaOf(s).objectTypes.length,2,'main 拿到 tunnel');
  eq(s.proposals[0].status,'merged','提案状态');
});
T('S6.4 拒绝+空 diff', ()=>{
  const s=CORE.createEmptyState();
  CORE.addObjectType(s,{name:'seg'});
  CORE.createBranch(s,'b2'); CORE.switchBranch(s,'main');
  ok(!CORE.proposeMerge(s,'b2').ok,'无变更提案拒绝');
  CORE.switchBranch(s,'b2'); CORE.addObjectType(s,{name:'x'}); CORE.switchBranch(s,'main');
  const p=CORE.proposeMerge(s,'b2');
  ok(CORE.rejectProposal(s,p.proposalId).ok,'拒绝');
  eq(s.proposals[0].status,'rejected');
  eq(CORE.schemaOf(s).objectTypes.length,1,'main 不变');
});
```

- [ ] **Step 2: 运行确认 FAIL** — S6.x FAIL

- [ ] **Step 3: CORE 追加实现**

```js
function createBranch(state,name){
  if(!/^[a-z][a-z0-9-]*$/.test(name||'')) return {ok:false,error:'分支名需为小写字母/数字/连字符'};
  if(state.schemas[name]) return {ok:false,error:'分支已存在'};
  state.schemas[name]=clone(state.schemas.main);
  state.branch.list.push({name, baseRev:state.meta.rev, status:'active', createdAt:new Date().toISOString()});
  state.branch.current=name; return {ok:true};
}
function switchBranch(state,name){
  if(!state.schemas[name]) return {ok:false,error:'分支不存在'};
  state.branch.current=name; return {ok:true};
}
function _diffColl(a,b){
  const added=b.filter(x=>!a.some(y=>y.name===x.name));
  const removed=a.filter(x=>!b.some(y=>y.name===x.name));
  const changed=[];
  for(const y of b){ const x=a.find(z=>z.name===y.name);
    if(x){ const strip=o=>{const c=clone(o); delete c.id; return JSON.stringify(c); };
      if(strip(x)!==strip(y)) changed.push({name:y.name,before:x,after:y}); } }
  return {added,removed,changed};
}
function diffSchemas(a,b){
  return { objectTypes:_diffColl(a.objectTypes,b.objectTypes), linkTypes:_diffColl(a.linkTypes,b.linkTypes),
           actionTypes:_diffColl(a.actionTypes,b.actionTypes), sharedProps:_diffColl(a.sharedProps,b.sharedProps) };
}
function diffEmpty(d){
  return Object.values(d).every(c=>!c.added.length&&!c.removed.length&&!c.changed.length);
}
function proposeMerge(state,branchName){
  if(state.branch.current!=='main') return {ok:false,error:'请在 main 分支发起提案'};
  if(!state.schemas[branchName]) return {ok:false,error:'分支不存在'};
  if(branchName==='main') return {ok:false,error:'main 无需提案'};
  if(state.proposals.some(p=>p.branch===branchName&&p.status==='open')) return {ok:false,error:'该分支已有待审提案'};
  const diff=diffSchemas(state.schemas.main,state.schemas[branchName]);
  if(diffEmpty(diff)) return {ok:false,error:'无变更'};
  const p={ id:uid('pr'), branch:branchName, diff, status:'open', createdAt:new Date().toISOString() };
  state.proposals.push(p); return {ok:true,proposalId:p.id};
}
function mergeProposal(state,proposalId){
  const p=state.proposals.find(x=>x.id===proposalId); if(!p||p.status!=='open') return {ok:false,error:'提案不存在或已处理'};
  state.schemas.main=clone(state.schemas[p.branch]); _bump(state);
  p.status='merged'; p.mergedAt=new Date().toISOString();
  const b=state.branch.list.find(x=>x.name===p.branch); if(b) b.status='merged';
  return {ok:true};
}
function rejectProposal(state,proposalId){
  const p=state.proposals.find(x=>x.id===proposalId); if(!p||p.status!=='open') return {ok:false,error:'提案不存在或已处理'};
  p.status='rejected'; p.rejectedAt=new Date().toISOString(); return {ok:true};
}
```

(导出表追加:`createBranch,switchBranch,diffSchemas,diffEmpty,proposeMerge,mergeProposal,rejectProposal`)

- [ ] **Step 4: 运行确认通过** — `node smoke.mjs` → 27 passed, 0 failed

- [ ] **Step 5: Commit**

```bash
git add ontoforge.html smoke.mjs
git commit -m "feat(core): schema 分支/diff/提案合并"
```

---

### Task 8: 种子数据(交通应急 + 空白)

**Files:**
- Modify: `ontoforge.html`(id="seed" 段)
- Modify: `smoke.mjs`(追加 S7 节)

**Interfaces:**
- Consumes: CORE 全部建模/引擎 API
- Produces:
  - `SEED.traffic() → state`(全新交通应急本体,每次调用独立)
  - `SEED.blank() → state`(空本体,ontologyName='空白本体')
  - 种子内容(spec §6):
    - 对象类型:`road_segment` 路段(seg_id pk,name,level enum[高速,主干,次干,支路],length_km number,status enum[畅通,缓行,拥堵,中断])、`incident` 交通事件(inc_id pk,title,type enum[事故,故障车,恶劣天气,占道施工,其他],severity enum[一般,较大,重大,特别重大],status enum[待处置,处理中,已关闭],reported_at date)、`rescue_team` 应急队伍(team_id pk,name,kind enum[交警,消防,医疗,路政,清障],status enum[待命,出动,休整],members number)、`vehicle` 车辆(veh_id pk,plate,kind enum[巡逻车,清障车,救护车,消防车],status enum[可用,任务中,维修])、`hub` 枢纽(hub_id pk,name,kind enum[立交,隧道,桥梁,收费站],district)
    - 链接类型:`inc_on_seg`(incident→road_segment,N:1)、`team_assigned`(rescue_team→incident,M:N)、`veh_belongs`(vehicle→rescue_team,N:1)
    - 动作类型:`report_incident` 上报事件(params:title/type/severity/seg_inc_id? 无 — targets:[{role:'seg',type:'road_segment'}],params title/type/severity,edits create incident{inc_id:'{{auto}}',title,type,severity,status:'待处置',reported_at:'{{now}}'}+addLink inc_on_seg from 新建 role 至 seg,notify 调度中心)、`dispatch_team` 派遣队伍(targets team+inc,rules team.status eq 待命 + inc.status neq 已关闭,requireConfirm,edits set team.status 出动+set inc.status 处理中+addLink team_assigned,notify+webhookLog)、`close_incident` 关闭事件(targets inc,rule inc.status eq 处理中,requireConfirm,edits set inc.status 已关闭,notify)
    - 实例:5 路段 / 5 事件(含 1 已关闭)/ 4 队伍 / 4 车辆 / 2 枢纽 = 20 对象;links:每事件挂路段(5 条)、2 车挂队、1 队已派往处理中事件

- [ ] **Step 1: smoke 追加 S7(先确认 FAIL:SEED 未定义)**

```js
// ── S7 种子完整性 ──
T('S7.1 结构完整性', ()=>{
  ok(globalThis.SEED&&SEED.traffic,'SEED.traffic 存在');
  const s=SEED.traffic();
  const errs=CORE.validateState(s); eq(errs,[],'validateState');
  const sch=s.schemas.main;
  eq(sch.objectTypes.length,5,'5 对象类型');
  eq(sch.linkTypes.length,3,'3 链接类型');
  eq(sch.actionTypes.length,3,'3 动作类型');
  eq(s.data.objects.length,20,'20 实例');
  // 主键唯一
  for(const t of sch.objectTypes){
    const keys=CORE.objectsOfType(s,t.name).map(o=>o.props[t.primaryKey]);
    eq(new Set(keys).size,keys.length,t.name+' 主键唯一');
  }
  // link 端点有效
  for(const l of s.data.links){
    ok(s.data.objects.some(o=>o.__id===l.from)&&s.data.objects.some(o=>o.__id===l.to),'link 端点存在');
  }
});
T('S7.2 空白种子', ()=>{
  const s=SEED.blank();
  eq(s.schemas.main.objectTypes.length,0,'无类型'); eq(s.data.objects.length,0,'无实例');
});
T('S7.3 种子动作端到端:派遣+关闭', ()=>{
  const s=SEED.traffic();
  const sch=s.schemas.main;
  const dispatch=sch.actionTypes.find(a=>a.name==='dispatch_team');
  const idle=CORE.objectsOfType(s,'rescue_team').find(t=>t.props.status==='待命');
  const open=CORE.objectsOfType(s,'incident').find(i=>i.props.status==='待处置');
  const r1=CORE.runAction(s,dispatch.id,{params:{},targets:{team:idle.__id,inc:open.__id}});
  ok(r1.needConfirm,'派遣需确认');
  const r2=CORE.runAction(s,dispatch.id,{params:{},targets:{team:idle.__id,inc:open.__id},confirmed:true});
  ok(r2.ok,r2.error);
  const close=sch.actionTypes.find(a=>a.name==='close_incident');
  const r3=CORE.runAction(s,close.id,{params:{},targets:{inc:open.__id},confirmed:true});
  ok(r3.ok,'处理中事件可关闭: '+(r3.error||''));
  eq(CORE.objectsOfType(s,'incident').find(i=>i.__id===open.__id).props.status,'已关闭','闭环完成');
  ok(s.audit.length>=2,'审计留痕');
});
T('S7.4 上报事件动作', ()=>{
  const s=SEED.traffic();
  const sch=s.schemas.main;
  const report=sch.actionTypes.find(a=>a.name==='report_incident');
  const seg=CORE.objectsOfType(s,'road_segment')[0];
  const before=CORE.objectsOfType(s,'incident').length;
  const r=CORE.runAction(s,report.id,{params:{title:'三车追尾',type:'事故',severity:'较大'},targets:{seg:seg.__id},confirmed:true});
  ok(r.ok,r.error);
  eq(CORE.objectsOfType(s,'incident').length,before+1,'事件+1');
  const inc=CORE.objectsOfType(s,'incident').find(i=>i.props.title==='三车追尾');
  eq(CORE.linkedObjects(s,inc.__id)[0].object.__id,seg.__id,'挂到路段');
});
```

- [ ] **Step 2: 运行确认 FAIL** — S7.x FAIL

- [ ] **Step 3: 写 id="seed" 段(全部经 CORE API 构建,天然合法)**

```js
const SEED=(()=>{
function traffic(){
  const s=CORE.createEmptyState();
  s.meta.ontologyName='城市交通应急本体';
  const T=(n,l,icon,color,pk)=>CORE.addObjectType(s,{name:n,label:l,icon,color}).id;
  const seg=T('road_segment','路段','🛣️','#2563eb'), inc=T('incident','交通事件','⚠️','#dc2626'),
        team=T('rescue_team','应急队伍','🚒','#ea580c'), veh=T('vehicle','车辆','🚗','#0891b2'),
        hub=T('hub','枢纽','🏗️','#7c3aed');
  const P=(tid,n,l,bt,ev,req)=>CORE.addProperty(s,tid,{name:n,label:l,baseType:bt,enumValues:ev,required:req});
  // 路段
  P(seg,'seg_id','编号','string',null,true); P(seg,'name','名称','string');
  P(seg,'level','等级','enum',['高速','主干','次干','支路']); P(seg,'length_km','长度(km)','number');
  P(seg,'status','路况','enum',['畅通','缓行','拥堵','中断']);
  // 事件
  P(inc,'inc_id','编号','string',null,true); P(inc,'title','标题','string');
  P(inc,'type','类型','enum',['事故','故障车','恶劣天气','占道施工','其他']);
  P(inc,'severity','严重度','enum',['一般','较大','重大','特别重大']);
  P(inc,'status','状态','enum',['待处置','处理中','已关闭']); P(inc,'reported_at','上报时间','date');
  // 队伍
  P(team,'team_id','编号','string',null,true); P(team,'name','名称','string');
  P(team,'kind','类型','enum',['交警','消防','医疗','路政','清障']);
  P(team,'status','状态','enum',['待命','出动','休整']); P(team,'members','人数','number');
  // 车辆
  P(veh,'veh_id','编号','string',null,true); P(veh,'plate','车牌','string');
  P(veh,'kind','类型','enum',['巡逻车','清障车','救护车','消防车']);
  P(veh,'status','状态','enum',['可用','任务中','维修']);
  // 枢纽
  P(hub,'hub_id','编号','string',null,true); P(hub,'name','名称','string');
  P(hub,'kind','类型','enum',['立交','隧道','桥梁','收费站']); P(hub,'district','辖区','string');
  for(const [tid,pk] of [[seg,'seg_id'],[inc,'inc_id'],[team,'team_id'],[veh,'veh_id'],[hub,'hub_id']])
    CORE.updateObjectType(s,tid,{primaryKey:pk});
  // 链接类型
  CORE.addLinkType(s,{name:'inc_on_seg',label:'发生于',from:'incident',to:'road_segment',cardinality:'N:1',keyMapping:{fromKey:'inc_id',toKey:'seg_id'}});
  CORE.addLinkType(s,{name:'team_assigned',label:'派遣至',from:'rescue_team',to:'incident',cardinality:'M:N',keyMapping:{fromKey:'team_id',toKey:'inc_id'}});
  CORE.addLinkType(s,{name:'veh_belongs',label:'隶属于',from:'vehicle',to:'rescue_team',cardinality:'N:1',keyMapping:{fromKey:'veh_id',toKey:'team_id'}});
  // 动作类型
  CORE.addActionType(s,{ name:'report_incident', label:'上报事件',
    targets:[{role:'seg',type:'road_segment'}],
    params:[ {name:'title',label:'标题',type:'string',required:true},
             {name:'type',label:'类型',type:'enum',enumValues:['事故','故障车','恶劣天气','占道施工','其他'],required:true},
             {name:'severity',label:'严重度',type:'enum',enumValues:['一般','较大','重大','特别重大'],required:true} ],
    rules:[], submissionCriteria:{requireConfirm:false},
    edits:[ {op:'create',target:'inc',objectType:'incident',props:{inc_id:'{{auto}}',title:'{{param.title}}',type:'{{param.type}}',severity:'{{param.severity}}',status:'待处置',reported_at:'{{now}}'}},
            {op:'addLink',linkType:'inc_on_seg',from:'inc',to:'seg'} ],
    sideEffects:[{type:'notify',config:{to:'调度中心',text:'新事件上报:{{param.title}}'}}] });
  CORE.addActionType(s,{ name:'dispatch_team', label:'派遣队伍',
    targets:[{role:'team',type:'rescue_team'},{role:'inc',type:'incident'}],
    params:[],
    rules:[ {target:'team',field:'status',op:'eq',value:'待命',message:'仅待命队伍可派遣'},
            {target:'inc',field:'status',op:'neq',value:'已关闭',message:'已关闭事件不可派遣'} ],
    submissionCriteria:{requireConfirm:true,note:'派遣后队伍状态将变为出动'},
    edits:[ {op:'set',target:'team',field:'status',value:'出动'},
            {op:'set',target:'inc',field:'status',value:'处理中'},
            {op:'addLink',linkType:'team_assigned',from:'team',to:'inc'} ],
    sideEffects:[ {type:'notify',config:{to:'队伍负责人',text:'你队已被派遣'}},
                  {type:'webhookLog',config:{url:'https://example.internal/hook'}} ] });
  CORE.addActionType(s,{ name:'close_incident', label:'关闭事件',
    targets:[{role:'inc',type:'incident'}], params:[],
    rules:[{target:'inc',field:'status',op:'eq',value:'处理中',message:'仅处理中事件可关闭'}],
    submissionCriteria:{requireConfirm:true},
    edits:[{op:'set',target:'inc',field:'status',value:'已关闭'}],
    sideEffects:[{type:'notify',config:{to:'调度中心',text:'事件已关闭'}}] });
  // 实例
  const O=(type,props)=>{ const o={__id:CORE.uid('obj'),__type:type,props}; s.data.objects.push(o); return o.__id; };
  const g1=O('road_segment',{seg_id:'SEG-001',name:'成渝立交段',level:'高速',length_km:'12.5',status:'拥堵'});
  const g2=O('road_segment',{seg_id:'SEG-002',name:'机场快速路',level:'主干',length_km:'8.2',status:'畅通'});
  const g3=O('road_segment',{seg_id:'SEG-003',name:'两江隧道连接线',level:'主干',length_km:'4.6',status:'缓行'});
  const g4=O('road_segment',{seg_id:'SEG-004',name:'大学城南路',level:'次干',length_km:'3.1',status:'畅通'});
  const g5=O('road_segment',{seg_id:'SEG-005',name:'北环大道',level:'高速',length_km:'15.0',status:'中断'});
  const e1=O('incident',{inc_id:'INC-1001',title:'两车追尾',type:'事故',severity:'较大',status:'处理中',reported_at:'2026-10-16'});
  const e2=O('incident',{inc_id:'INC-1002',title:'货车故障占道',type:'故障车',severity:'一般',status:'待处置',reported_at:'2026-10-17'});
  const e3=O('incident',{inc_id:'INC-1003',title:'团雾预警',type:'恶劣天气',severity:'重大',status:'待处置',reported_at:'2026-10-17'});
  const e4=O('incident',{inc_id:'INC-1004',title:'夜间占道施工',type:'占道施工',severity:'一般',status:'待处置',reported_at:'2026-10-15'});
  const e5=O('incident',{inc_id:'INC-1005',title:'轻微刮擦',type:'事故',severity:'一般',status:'已关闭',reported_at:'2026-10-14'});
  const t1=O('rescue_team',{team_id:'TM-01',name:'交警一大队',kind:'交警',status:'待命',members:'24'});
  const t2=O('rescue_team',{team_id:'TM-02',name:'消防特勤站',kind:'消防',status:'出动',members:'30'});
  const t3=O('rescue_team',{team_id:'TM-03',name:'急救中心二组',kind:'医疗',status:'待命',members:'12'});
  const t4=O('rescue_team',{team_id:'TM-04',name:'清障突击队',kind:'清障',status:'休整',members:'8'});
  const v1=O('vehicle',{veh_id:'VH-01',plate:'渝A·D1023',kind:'巡逻车',status:'可用'});
  const v2=O('vehicle',{veh_id:'VH-02',plate:'渝A·Q2087',kind:'清障车',status:'任务中'});
  const v3=O('vehicle',{veh_id:'VH-03',plate:'渝B·J3301',kind:'救护车',status:'可用'});
  const v4=O('vehicle',{veh_id:'VH-04',plate:'渝A·X5566',kind:'消防车',status:'维修'});
  O('hub',{hub_id:'HUB-01',name:'成渝立交',kind:'立交',district:'九龙坡'});
  O('hub',{hub_id:'HUB-02',name:'两江隧道',kind:'隧道',district:'江北'});
  const lt=(name)=>s.schemas.main.linkTypes.find(l=>l.name===name).id;
  for(const [e,g] of [[e1,g1],[e2,g2],[e3,g5],[e4,g3],[e5,g4]]) CORE.createLink(s,lt('inc_on_seg'),e,g);
  CORE.createLink(s,lt('veh_belongs'),v1,t1); CORE.createLink(s,lt('veh_belongs'),v2,t4);
  CORE.createLink(s,lt('team_assigned'),t2,e1);
  return s;
}
function blank(){ const s=CORE.createEmptyState(); s.meta.ontologyName='空白本体'; return s; }
return { traffic, blank };
})();
if(typeof globalThis!=='undefined') globalThis.SEED=SEED;
```

- [ ] **Step 4: 运行确认通过** — `node smoke.mjs` → 31 passed, 0 failed

- [ ] **Step 5: Commit**

```bash
git add ontoforge.html smoke.mjs
git commit -m "feat(seed): 交通应急种子本体(5类型/3链接/3动作/20实例) + 空白种子"
```

---

### Task 9: UI 骨架(CSS / topbar / sidebar / router / toast / modal / STORE 持久化)

**Files:**
- Modify: `ontoforge.html`(head CSS + body DOM + id="appjs" 段)
- Modify: `smoke.mjs`(追加 S8 静态断言若干项)

**Interfaces:**
- Consumes: CORE、SEED
- Produces(后续 UI 任务全部依赖):
  - DOM 骨架:`#topbar`(logo/搜索 `#global-search`/新建下拉 `#btn-new`/分支切换 `#branch-switch`/通知铃 `#btn-notify` 带未读角标 `#notify-badge`)、`#sidebar`(nav 项 data-view)、`#main`、toast 容器 `#toasts`、modal 容器 `#modal-root`
  - `APP` 命名空间(id="appjs"):
    - `APP.store`:`load()`(localStorage `ontoforge.v1`;JSON 解析失败→尝试 `ontoforge.v1.bak`→`SEED.traffic()`;首次无数据→展示种子选择由 Task 14  onboarding 处理,先直接 traffic)、`save()`(防抖 300ms;写主键前先复制现主键值到 `.bak`)、`state`(当前 state 引用)、`replace(newState)`、`reset()`
    - `APP.go(view,sel)` → 更新 `state.ui.view/sel` + `render()`
    - `APP.render()` → 按 `state.ui.view` 分发到 `VIEWS[view](el,state)`;渲染后刷新 topbar(分支名、通知角标)
    - `APP.toast(msg,kind='info')`
    - `APP.modal({title,bodyHTML,actions:[{label,kind,onClick}]})` → 返回 close();ESC/遮罩点击关闭
    - `APP.esc(s)` HTML 转义
    - `VIEWS = {}`(后续任务逐个挂:`VIEWS.discover=…`)
  - CSS:企业工作台风,深色 sidebar(#1e293b)+ 浅色主区;`.card` `.badge` `.btn` `.btn-primary` `.btn-danger` `.table` `.chip` `.form-row` `.toast` `.modal-mask` 等类名后续任务直接用

- [ ] **Step 1: smoke S14 追加静态断言(先确认 FAIL;S8 编号已被 Task 1 静态检查占用,UI 骨架用 S14)**

```js
// ── S14 UI 骨架静态断言 ──
T('S14.1 DOM 骨架存在', ()=>{
  for(const id of ['topbar','sidebar','main','toasts','modal-root','global-search','branch-switch','btn-notify','notify-badge','btn-new'])
    ok(html.includes(`id="${id}"`),'缺 #'+id);
});
T('S14.2 APP 基础件', ()=>{
  const app=section('appjs');
  for(const fn of ['store','render','go','toast','modal','esc'])
    ok(app.includes(fn),`APP 缺 ${fn}`);
  ok(app.includes('ontoforge.v1'),'localStorage 键');
  ok(app.includes('VIEWS'),'视图注册表');
});
```

- [ ] **Step 2: 运行确认 FAIL**

- [ ] **Step 3: 写 UI 骨架**

HTML body:

```html
<div id="topbar">
  <div class="logo">OntoForge <span class="logo-sub">本体工坊</span></div>
  <input id="global-search" placeholder="搜索对象类型 / 动作 / 实例…" />
  <div class="topbar-right">
    <div class="dropdown">
      <button id="btn-new" class="btn">＋ 新建</button>
      <div class="dropdown-menu" id="new-menu" hidden>
        <a data-new="objectType">对象类型</a><a data-new="linkType">链接类型</a>
        <a data-new="actionType">动作类型</a><a data-new="sharedProp">共享属性</a>
      </div>
    </div>
    <select id="branch-switch" title="分支切换"></select>
    <button id="btn-notify" class="btn">🔔<span id="notify-badge" hidden></span></button>
  </div>
</div>
<div id="layout">
  <div id="sidebar">
    <div class="side-group">概览</div>
    <a class="side-item" data-view="discover">✨ Discover</a>
    <div class="side-group">语义层</div>
    <div id="side-objectTypes"></div>
    <a class="side-item" data-view="linkTypes">🔗 链接类型</a>
    <a class="side-item" data-view="sharedProps">🧩 共享属性</a>
    <div class="side-group">动力层</div>
    <div id="side-actionTypes"></div>
    <div class="side-group">消费与治理</div>
    <a class="side-item" data-view="explorer">🔍 Object Explorer</a>
    <a class="side-item" data-view="branches">🌿 分支中心</a>
    <a class="side-item" data-view="settings">⚙️ 数据 / 导入导出</a>
  </div>
  <div id="main"></div>
</div>
<div id="toasts"></div>
<div id="modal-root"></div>
```

CSS(head 内 `<style>`,要点):

```css
:root{--side:#1e293b;--side-hi:#334155;--bg:#f1f5f9;--card:#fff;--ink:#0f172a;--mut:#64748b;--pri:#2563eb;--dan:#dc2626;--line:#e2e8f0}
*{box-sizing:border-box} body{margin:0;font:14px/1.6 "PingFang SC","Microsoft YaHei",system-ui,sans-serif;color:var(--ink);background:var(--bg)}
#topbar{height:52px;background:#fff;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:16px;padding:0 16px;position:sticky;top:0;z-index:50}
.logo{font-weight:700;font-size:16px}.logo-sub{font-size:12px;color:var(--mut);font-weight:400}
#global-search{flex:0 1 360px;padding:6px 12px;border:1px solid var(--line);border-radius:6px}
.topbar-right{margin-left:auto;display:flex;gap:8px;align-items:center}
.btn{padding:6px 12px;border:1px solid var(--line);border-radius:6px;background:#fff;cursor:pointer}
.btn:hover{background:#f8fafc}.btn-primary{background:var(--pri);color:#fff;border-color:var(--pri)}
.btn-danger{background:var(--dan);color:#fff;border-color:var(--dan)}
#notify-badge{background:var(--dan);color:#fff;border-radius:9px;font-size:11px;padding:0 5px;margin-left:2px}
#layout{display:flex;min-height:calc(100vh - 52px)}
#sidebar{width:220px;background:var(--side);color:#cbd5e1;padding:12px 0;flex-shrink:0}
.side-group{padding:10px 16px 4px;font-size:11px;color:#64748b;letter-spacing:1px}
.side-item{display:block;padding:7px 16px;color:#cbd5e1;cursor:pointer;text-decoration:none;border-left:3px solid transparent}
.side-item:hover{background:var(--side-hi)}.side-item.active{background:var(--side-hi);border-left-color:var(--pri);color:#fff}
.side-item .cnt{float:right;font-size:11px;color:#64748b}
#main{flex:1;padding:20px;min-width:0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px;margin-bottom:16px}
.card h3{margin:0 0 12px;font-size:15px}
.badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;background:#e2e8f0}
.chip{display:inline-block;padding:2px 10px;border:1px solid var(--line);border-radius:14px;margin:2px;cursor:pointer;background:#fff}
.chip:hover{border-color:var(--pri);color:var(--pri)}
.table{width:100%;border-collapse:collapse}.table th,.table td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;font-size:13px}
.table th{color:var(--mut);font-weight:600;background:#f8fafc}
.form-row{margin-bottom:12px}.form-row label{display:block;font-size:13px;color:var(--mut);margin-bottom:4px}
.form-row input,.form-row select,.form-row textarea{width:100%;padding:6px 10px;border:1px solid var(--line);border-radius:6px;font:inherit}
.form-err{color:var(--dan);font-size:12px;margin-top:4px}
#toasts{position:fixed;right:16px;bottom:16px;z-index:100}
.toast{background:#0f172a;color:#fff;padding:10px 16px;border-radius:8px;margin-top:8px;box-shadow:0 4px 12px rgba(0,0,0,.25)}
.toast.error{background:var(--dan)}
.modal-mask{position:fixed;inset:0;background:rgba(15,23,42,.45);z-index:90;display:flex;align-items:center;justify-content:center}
.modal{background:#fff;border-radius:10px;width:min(640px,92vw);max-height:86vh;overflow:auto;padding:20px}
.modal h3{margin:0 0 14px}.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:16px}
.dropdown{position:relative}.dropdown-menu{position:absolute;right:0;top:110%;background:#fff;border:1px solid var(--line);border-radius:8px;min-width:140px;box-shadow:0 8px 24px rgba(0,0,0,.12);z-index:60}
.dropdown-menu a{display:block;padding:8px 14px;cursor:pointer}.dropdown-menu a:hover{background:#f1f5f9}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.mut{color:var(--mut)}.mono{font-family:ui-monospace,Consolas,monospace;font-size:12px}
```

appjs 骨架:

```js
const APP=(()=>{
const LS_KEY='ontoforge.v1', LS_BAK='ontoforge.v1.bak';
let state=null, saveTimer=null;
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function load(){
  try{ const raw=localStorage.getItem(LS_KEY);
    if(raw){ const s=JSON.parse(raw); const errs=CORE.validateState(s); if(!errs.length) return s; } }catch(e){}
  try{ const raw=localStorage.getItem(LS_BAK);
    if(raw){ const s=JSON.parse(raw); const errs=CORE.validateState(s); if(!errs.length){ toast('主存档损坏,已从备份恢复','error'); return s; } } }catch(e){}
  return SEED.traffic();
}
function save(){
  clearTimeout(saveTimer);
  saveTimer=setTimeout(()=>{
    try{ const prev=localStorage.getItem(LS_KEY); if(prev) localStorage.setItem(LS_BAK,prev);
      localStorage.setItem(LS_KEY,JSON.stringify(state)); }catch(e){ toast('保存失败:'+e.message,'error'); }
  },300);
}
function replace(ns){ state=ns; save(); render(); }
function reset(){ localStorage.removeItem(LS_KEY); localStorage.removeItem(LS_BAK); location.reload(); }

const VIEWS={};   // 各 Task 挂视图: VIEWS.discover=(el,state)=>{...}
function go(view,sel){ state.ui.view=view; state.ui.sel=sel||null; save(); render(); }
function render(){
  // 侧栏动态区
  const sch=CORE.schemaOf(state);
  $('#side-objectTypes').innerHTML=sch.objectTypes.map(t=>
    `<a class="side-item" data-view="objectType" data-sel="${t.id}">${t.icon||'📦'} ${esc(t.label||t.name)}<span class="cnt">${CORE.objectsOfType(state,t.name).length}</span></a>`).join('');
  $('#side-actionTypes').innerHTML=sch.actionTypes.map(a=>
    `<a class="side-item" data-view="actionType" data-sel="${a.id}">⚡ ${esc(a.label||a.name)}</a>`).join('');
  $$('.side-item').forEach(el=>{
    el.classList.toggle('active', el.dataset.view===state.ui.view && (!el.dataset.sel||el.dataset.sel===state.ui.sel));
    el.onclick=()=>go(el.dataset.view, el.dataset.sel||null);
  });
  // topbar
  const bs=$('#branch-switch');
  bs.innerHTML=state.branch.list.map(b=>`<option ${b.name===state.branch.current?'selected':''}>${b.name}</option>`).join('');
  bs.onchange=()=>{ const r=CORE.switchBranch(state,bs.value); if(r.ok){save();render();toast('已切换到分支 '+bs.value);} };
  const un=CORE.unreadNotices(state);
  $('#notify-badge').hidden=!un; $('#notify-badge').textContent=un;
  // 主视图
  const main=$('#main');
  const v=VIEWS[state.ui.view]||VIEWS.discover;
  v(main,state);
}
function toast(msg,kind){
  const t=document.createElement('div'); t.className='toast'+(kind==='error'?' error':''); t.textContent=msg;
  $('#toasts').appendChild(t); setTimeout(()=>t.remove(),3600);
}
function modal({title,bodyHTML,actions}){
  const root=$('#modal-root');
  root.innerHTML=`<div class="modal-mask"><div class="modal"><h3>${esc(title)}</h3><div class="modal-body">${bodyHTML}</div><div class="modal-actions"></div></div></div>`;
  const close=()=>{root.innerHTML='';};
  root.querySelector('.modal-mask').addEventListener('click',e=>{ if(e.target.classList.contains('modal-mask')) close(); });
  const escH=e=>{ if(e.key==='Escape'){close();document.removeEventListener('keydown',escH);} };
  document.addEventListener('keydown',escH);
  const bar=root.querySelector('.modal-actions');
  (actions||[{label:'关闭'}]).forEach(a=>{
    const b=document.createElement('button'); b.className='btn'+(a.kind?' btn-'+a.kind:''); b.textContent=a.label;
    b.onclick=()=>{ const r=a.onClick&&a.onClick(root); if(r!==false) close(); };
    bar.appendChild(b);
  });
  return close;
}
// 新建下拉(委托给各视图暴露的创建表单)
function bindChrome(){
  const nm=$('#new-menu');
  $('#btn-new').onclick=e=>{ nm.hidden=!nm.hidden; e.stopPropagation(); };
  document.addEventListener('click',()=>nm.hidden=true);
  nm.querySelectorAll('a').forEach(a=>a.onclick=()=>{
    nm.hidden=true;
    const kind=a.dataset.new;
    if(kind==='objectType'&&VIEWS._newObjectType) VIEWS._newObjectType();
    if(kind==='linkType'&&VIEWS._newLinkType) VIEWS._newLinkType();
    if(kind==='actionType'&&VIEWS._newActionType) VIEWS._newActionType();
    if(kind==='sharedProp'&&VIEWS._newSharedProp) VIEWS._newSharedProp();
  });
}
function boot(){ state=load(); bindChrome(); render(); }
document.addEventListener('DOMContentLoaded',boot);
return { get state(){return state;}, set state(s){state=s;}, store:{load,save,reset}, replace, go, render, toast, modal, esc, VIEWS, $, $$ };
})();
```

- [ ] **Step 4: 运行 smoke 确认通过**(S14.1/S14.2 转绿;总计 33 passed)

- [ ] **Step 5: Commit**

```bash
git add ontoforge.html smoke.mjs
git commit -m "feat(ui): 应用骨架(topbar/sidebar/router/toast/modal/持久化)"
```

---

### Task 10: Discover 视图 + ObjectType 7-section 视图 + Property 编辑器

**Files:**
- Modify: `ontoforge.html`(id="appjs" 段追加)
- Modify: `smoke.mjs`(追加 S9 静态断言)

**Interfaces:**
- Consumes: `APP.*`、`CORE.addObjectType/updateObjectType/deleteObjectType/addProperty/updateProperty/deleteProperty/attachSharedProp/detachSharedProp/objectsOfType/objectLabel`
- Produces:
  - `VIEWS.discover(el,state)` — 收藏/最近/全部类型卡片;卡片点击进 objectType 视图;卡上 ☆/★ 切换 `state.ui.favorites`
  - `VIEWS.objectType(el,state)` — sel=typeId;7 个 section:① 元数据(名称/label/icon/color/primaryKey 可编辑)② Properties 表(点行进 property editor)③ 引用它的 Action types ④ Link type 关系图占位(`APP.renderLinkGraph(el,typeId)` 由 Task 11 提供,本任务先留 `<div class="link-graph-slot">` 并在 Task 11 填充)⑤ Dependents(依赖检查:若删除会被谁挡)⑥ Data 实例预览表(前 20 行)⑦ Usage(该类型对象作为 target 的 action 调用数,来自 audit)
  - 顶部操作:收藏切换、删除类型(走 CORE 约束,错误 toast)
  - `VIEWS.property(el,state)` — sel={typeId,propName}:编辑 label/baseType(禁改,只读展示)/required/enumValues/共享属性挂载卸载;新建属性表单也复用(`sel={typeId,propName:null}`)
  - `VIEWS._newObjectType()` — modal 表单(name/label/icon/color)→ CORE.addObjectType
  - `state.ui.favorites`/`recent` 维护:进入 objectType 视图时 unshift recent(去重,截 8)

- [ ] **Step 1: smoke S9(静态断言,先 FAIL)**

```js
// ── S9 Discover/ObjectType/Property 静态断言 ──
T('S9.1 视图挂载', ()=>{
  const app=section('appjs');
  for(const v of ['VIEWS.discover','VIEWS.objectType','VIEWS.property','_newObjectType'])
    ok(app.includes(v),'缺 '+v);
});
T('S9.2 7-section 覆盖', ()=>{
  const app=section('appjs');
  for(const kw of ['元数据','Properties','Dependents','Data','Usage','favorite','recent'])
    ok(app.includes(kw),'7-section 缺 '+kw);
});
```

- [ ] **Step 2: 运行确认 FAIL**

- [ ] **Step 3: appjs 追加实现**

```js
// ── Discover ──
APP.VIEWS.discover=(el,state)=>{
  const sch=CORE.schemaOf(state);
  const fav=state.ui.favorites, rec=state.ui.recent;
  const card=t=>{
    const cnt=CORE.objectsOfType(state,t.name).length;
    const isFav=fav.includes(t.id);
    return `<div class="card ot-card" data-id="${t.id}" style="cursor:pointer">
      <div style="font-size:22px">${t.icon||'📦'} <b>${APP.esc(t.label||t.name)}</b>
      <span class="fav-star" data-id="${t.id}" style="float:right;cursor:pointer">${isFav?'★':'☆'}</span></div>
      <div class="mut mono">${t.name}</div>
      <div style="margin-top:6px"><span class="badge">${cnt} 实例</span> <span class="badge">${t.properties.length} 属性</span></div></div>`;
  };
  const grid=ts=>ts.length?`<div class="grid2">${ts.map(card).join('')}</div>`:'<p class="mut">暂无</p>';
  el.innerHTML=`<h2>Discover</h2>
    <div class="card"><h3>⭐ 收藏</h3>${grid(sch.objectTypes.filter(t=>fav.includes(t.id)))}</div>
    <div class="card"><h3>🕘 最近查看</h3>${grid(rec.map(id=>sch.objectTypes.find(t=>t.id===id)).filter(Boolean))}</div>
    <div class="card"><h3>📦 全部对象类型(${sch.objectTypes.length})</h3>${grid(sch.objectTypes)}</div>`;
  el.querySelectorAll('.ot-card').forEach(c=>c.onclick=e=>{
    if(e.target.classList.contains('fav-star'))return;
    APP.go('objectType',c.dataset.id);
  });
  el.querySelectorAll('.fav-star').forEach(s=>s.onclick=()=>{
    const i=fav.indexOf(s.dataset.id); i>=0?fav.splice(i,1):fav.push(s.dataset.id);
    APP.store.save(); APP.render();
  });
};

// ── ObjectType 7-section ──
APP.VIEWS.objectType=(el,state)=>{
  const sch=CORE.schemaOf(state);
  const t=sch.objectTypes.find(x=>x.id===state.ui.sel);
  if(!t){ el.innerHTML='<p class="mut">类型不存在</p>'; return; }
  // recent
  state.ui.recent=[t.id,...state.ui.recent.filter(x=>x!==t.id)].slice(0,8);
  const objs=CORE.objectsOfType(state,t.name);
  const refActions=sch.actionTypes.filter(a=>a.targets.some(tg=>tg.type===t.name));
  const refLinks=sch.linkTypes.filter(l=>l.from===t.name||l.to===t.name);
  const usageN=state.audit.filter(e=>refActions.some(a=>a.id===e.actionId)).length;
  const isFav=state.ui.favorites.includes(t.id);
  el.innerHTML=`
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px">
    <span style="font-size:28px">${t.icon||'📦'}</span>
    <h2 style="margin:0">${APP.esc(t.label||t.name)}</h2>
    <span class="badge" style="background:${t.color||'#e2e8f0'}22;color:${t.color||'#475569'}">${t.name}</span>
    <span style="margin-left:auto"></span>
    <button class="btn" id="ot-fav">${isFav?'★ 已收藏':'☆ 收藏'}</button>
    <button class="btn btn-danger" id="ot-del">删除类型</button>
  </div>
  <div class="card"><h3>① 元数据</h3>
    <div class="grid2">
      <div class="form-row"><label>Label</label><input id="ot-label" value="${APP.esc(t.label||'')}"></div>
      <div class="form-row"><label>图标(emoji)</label><input id="ot-icon" value="${APP.esc(t.icon||'')}"></div>
      <div class="form-row"><label>颜色</label><input id="ot-color" type="color" value="${t.color||'#2563eb'}"></div>
      <div class="form-row"><label>主键属性</label><select id="ot-pk">
        <option value="">(未设)</option>${t.properties.map(p=>`<option ${p.name===t.primaryKey?'selected':''}>${p.name}</option>`).join('')}</select></div>
    </div>
    <button class="btn btn-primary" id="ot-save">保存元数据</button>
  </div>
  <div class="card"><h3>② Properties(${t.properties.length}) <button class="btn" id="prop-add" style="float:right">＋ 新建属性</button></h3>
    <table class="table"><tr><th>名称</th><th>Label</th><th>类型</th><th>必填</th><th>主键</th><th>共享</th></tr>
    ${t.properties.map(p=>`<tr data-prop="${p.name}" style="cursor:pointer"><td class="mono">${p.name}</td><td>${APP.esc(p.label||'')}</td>
      <td><span class="badge">${p.baseType}</span></td><td>${p.required?'✓':''}</td><td>${p.name===t.primaryKey?'🔑':''}</td>
      <td>${sch.sharedProps.some(sp=>sp.name===p.name&&(t.sharedPropRefs||[]).includes(sp.id))?'🧩':''}</td></tr>`).join('')}</table></div>
  <div class="card"><h3>③ 引用它的 Action types(${refActions.length})</h3>
    ${refActions.map(a=>`<span class="chip" data-act="${a.id}">⚡ ${APP.esc(a.label||a.name)}</span>`).join('')||'<span class="mut">无</span>'}</div>
  <div class="card"><h3>④ Link type 关系图</h3><div class="link-graph-slot" data-type="${t.id}"></div></div>
  <div class="card"><h3>⑤ Dependents(删除前置检查)</h3>
    <div class="mut">${refActions.length?`动作:${refActions.map(a=>APP.esc(a.label||a.name)).join('、')}`:'无动作依赖'} ·
    ${refLinks.length?`链接:${refLinks.map(l=>l.name).join('、')}`:'无链接依赖'} · 实例 ${objs.length} 个</div></div>
  <div class="card"><h3>⑥ Data(前 20 条)</h3>
    <table class="table"><tr>${t.properties.slice(0,6).map(p=>`<th>${APP.esc(p.label||p.name)}</th>`).join('')}</tr>
    ${objs.slice(0,20).map(o=>`<tr data-obj="${o.__id}" style="cursor:pointer">${t.properties.slice(0,6).map(p=>`<td>${APP.esc(o.props[p.name]??'')}</td>`).join('')}</tr>`).join('')||'<tr><td class="mut">无实例</td></tr>'}</table></div>
  <div class="card"><h3>⑦ Usage</h3><div class="mut">相关动作累计执行 <b>${usageN}</b> 次(全分支审计)</div></div>`;
  // 绑定
  el.querySelector('#ot-fav').onclick=()=>{ const f=state.ui.favorites,i=f.indexOf(t.id); i>=0?f.splice(i,1):f.push(t.id); APP.store.save(); APP.render(); };
  el.querySelector('#ot-save').onclick=()=>{
    const r=CORE.updateObjectType(state,t.id,{label:el.querySelector('#ot-label').value,icon:el.querySelector('#ot-icon').value,color:el.querySelector('#ot-color').value,primaryKey:el.querySelector('#ot-pk').value||null});
    r.ok?(APP.store.save(),APP.render(),APP.toast('已保存')):APP.toast(r.error,'error');
  };
  el.querySelector('#ot-del').onclick=()=>{
    APP.modal({title:'删除对象类型',bodyHTML:`<p>确定删除 <b>${APP.esc(t.label||t.name)}</b>?有依赖时将被拒绝。</p>`,actions:[
      {label:'取消'},{label:'删除',kind:'danger',onClick:()=>{ const r=CORE.deleteObjectType(state,t.id);
        r.ok?(APP.store.save(),APP.go('discover'),APP.toast('已删除')):APP.toast(r.error,'error'); }}]});
  };
  el.querySelector('#prop-add').onclick=()=>APP.go('property',{typeId:t.id,propName:null});
  el.querySelectorAll('[data-prop]').forEach(r=>r.onclick=()=>APP.go('property',{typeId:t.id,propName:r.dataset.prop}));
  el.querySelectorAll('[data-act]').forEach(c=>c.onclick=()=>APP.go('actionType',c.dataset.act));
  el.querySelectorAll('[data-obj]').forEach(r=>r.onclick=()=>APP.go('objectView',{typeName:t.name,objectId:r.dataset.obj}));
  if(APP.renderLinkGraph) APP.renderLinkGraph(el.querySelector('.link-graph-slot'),state,t.id);
};

// ── Property 编辑器 ──
APP.VIEWS.property=(el,state)=>{
  const {typeId,propName}=state.ui.sel||{};
  const t=CORE.schemaOf(state).objectTypes.find(x=>x.id===typeId);
  if(!t){ el.innerHTML='<p class="mut">类型不存在</p>'; return; }
  const p=propName?t.properties.find(x=>x.name===propName):null;
  const isNew=!p;
  el.innerHTML=`<h2><a style="cursor:pointer;color:var(--pri)" id="back">${APP.esc(t.label||t.name)}</a> / ${isNew?'新建属性':APP.esc(p.label||p.name)}</h2>
  <div class="card"><h3>${isNew?'新建属性':'编辑属性'}</h3>
    <div class="grid2">
      <div class="form-row"><label>名称(小写 snake)</label><input id="p-name" ${isNew?'':'disabled'} value="${APP.esc(p?.name||'')}" placeholder="如 severity"></div>
      <div class="form-row"><label>Label</label><input id="p-label" value="${APP.esc(p?.label||'')}"></div>
      <div class="form-row"><label>基础类型${isNew?'':'(不可改)'}</label><select id="p-bt" ${isNew?'':'disabled'}>
        ${CORE.BASE_TYPES.map(b=>`<option ${p?.baseType===b?'selected':''}>${b}</option>`).join('')}</select></div>
      <div class="form-row"><label>必填</label><select id="p-req"><option value="">否</option><option value="1" ${p?.required?'selected':''}>是</option></select></div>
    </div>
    <div class="form-row" id="p-enum-row" hidden><label>枚举值(逗号分隔)</label><input id="p-enum" value="${APP.esc((p?.enumValues||[]).join(','))}"></div>
    <div class="form-err" id="p-err"></div>
    <button class="btn btn-primary" id="p-save">${isNew?'创建':'保存'}</button>
    ${isNew?'':'<button class="btn btn-danger" id="p-del" style="margin-left:8px">删除属性</button>'}
  </div>
  ${isNew?'':`<div class="card"><h3>共享属性</h3>
    <div class="mut">挂载共享属性可跨类型复用同一属性定义。</div>
    ${(CORE.schemaOf(state).sharedProps||[]).map(sp=>{
      const on=(t.sharedPropRefs||[]).includes(sp.id);
      return `<span class="chip" data-sp="${sp.id}">${on?'✓ ':''}🧩 ${APP.esc(sp.label||sp.name)}</span>`;}).join('')||'<span class="mut">尚无共享属性定义</span>'}
  </div>`}`;
  const syncEnum=()=>{ el.querySelector('#p-enum-row').hidden=el.querySelector('#p-bt').value!=='enum'; };
  el.querySelector('#p-bt').onchange=syncEnum; syncEnum();
  el.querySelector('#back').onclick=()=>APP.go('objectType',t.id);
  el.querySelector('#p-save').onclick=()=>{
    const bt=el.querySelector('#p-bt').value;
    const payload={ label:el.querySelector('#p-label').value, baseType:bt, required:el.querySelector('#p-req').value==='1',
      enumValues:bt==='enum'?el.querySelector('#p-enum').value.split(',').map(s=>s.trim()).filter(Boolean):null };
    const r=isNew?CORE.addProperty(state,t.id,{name:el.querySelector('#p-name').value.trim(),...payload})
                 :CORE.updateProperty(state,t.id,p.name,payload);
    if(r.ok){ APP.store.save(); APP.go('objectType',t.id); APP.toast('已保存'); }
    else el.querySelector('#p-err').textContent=r.error;
  };
  const del=el.querySelector('#p-del');
  if(del) del.onclick=()=>{ const r=CORE.deleteProperty(state,t.id,p.name);
    r.ok?(APP.store.save(),APP.go('objectType',t.id),APP.toast('已删除')):APP.toast(r.error,'error'); };
  el.querySelectorAll('[data-sp]').forEach(c=>c.onclick=()=>{
    const on=(t.sharedPropRefs||[]).includes(c.dataset.sp);
    const r=on?CORE.detachSharedProp(state,t.id,c.dataset.sp):CORE.attachSharedProp(state,t.id,c.dataset.sp);
    r.ok?(APP.store.save(),APP.render()):APP.toast(r.error,'error');
  });
};

注意:sharedPropRefs 存共享属性 **id**(CORE 签名 `attachSharedProp(state,typeId,spId)`),chip 的 `data-sp` 必须是 `sp.id`,比较也按 id。

// ── 新建对象类型(顶栏 ＋新建)──
APP.VIEWS._newObjectType=()=>{
  APP.modal({title:'新建对象类型',bodyHTML:`
    <div class="form-row"><label>名称(小写 snake,如 sensor)</label><input id="n-name"></div>
    <div class="form-row"><label>Label</label><input id="n-label"></div>
    <div class="form-row"><label>图标 emoji</label><input id="n-icon" value="📦"></div>
    <div class="form-err" id="n-err"></div>`,actions:[
    {label:'取消'},{label:'创建',kind:'primary',onClick:root=>{
      const r=CORE.addObjectType(APP.state,{name:root.querySelector('#n-name').value.trim(),
        label:root.querySelector('#n-label').value,icon:root.querySelector('#n-icon').value});
      if(!r.ok){ root.querySelector('#n-err').textContent=r.error; return false; }
      APP.store.save(); APP.go('objectType',r.id); APP.toast('类型已创建');
    }}]});
};
```

- [ ] **Step 4: 运行 smoke 确认通过**(35 passed)

- [ ] **Step 5: Commit**

```bash
git add ontoforge.html smoke.mjs
git commit -m "feat(ui): Discover/ObjectType 7-section/Property 编辑器"
```

---

### Task 11: LinkType 视图 + Canvas 关系图 + 共享属性视图

**Files:**
- Modify: `ontoforge.html`(id="appjs" 段追加)
- Modify: `smoke.mjs`(追加 S10 静态断言)

**Interfaces:**
- Consumes: `CORE.addLinkType/updateLinkType/deleteLinkType/linksOf/addSharedProp`
- Produces:
  - `APP.renderLinkGraph(slot,state,focusTypeId)` — Canvas 画 schema 关系图:节点=对象类型(圆角矩形+icon+名),边=链接类型(线+基数标注);focusTypeId 高亮;点击节点跳 objectType,点击边中点标签跳 linkType。固定网格布局(col=⌈√n⌉),无需力导向
  - `VIEWS.linkTypes(el,state)` — 链接类型列表卡 + 新建按钮;卡片进 linkType 详情
  - `VIEWS.linkType(el,state)` — Overview(两端类型/基数可改/label)+ Datasources(keyMapping fromKey/toKey 编辑)+ 实例数(`state.data.links` 按类型计数);删除走 CORE 约束
  - `VIEWS._newLinkType()` — modal(name/label/from/to/cardinality)
  - `VIEWS.sharedProps(el,state)` — 共享属性列表 + 新建/删除(CORE.addSharedProp;删除 CORE 侧已拒绝被引用者——若无该约束则 UI 层检查 sharedPropRefs)
  - `VIEWS._newSharedProp()` — modal

- [ ] **Step 1: smoke S10(静态断言,先 FAIL)**

```js
// ── S10 LinkType/关系图/共享属性 静态断言 ──
T('S10.1 视图挂载', ()=>{
  const app=section('appjs');
  for(const v of ['VIEWS.linkTypes','VIEWS.linkType','VIEWS.sharedProps','renderLinkGraph','_newLinkType','_newSharedProp'])
    ok(app.includes(v),'缺 '+v);
  ok(app.includes('<canvas')||app.includes("createElement('canvas')")||app.includes('getContext'),'canvas 绘制');
});
```

- [ ] **Step 2: 运行确认 FAIL**

- [ ] **Step 3: appjs 追加实现**

```js
// ── Schema 关系图(canvas)──
APP.renderLinkGraph=(slot,state,focusTypeId)=>{
  const sch=CORE.schemaOf(state);
  const types=sch.objectTypes;
  if(!types.length){ slot.innerHTML='<span class="mut">尚无对象类型</span>'; return; }
  const W=Math.max(slot.clientWidth||520,420), col=Math.ceil(Math.sqrt(types.length));
  const rows=Math.ceil(types.length/col), cellW=W/col, cellH=110, H=rows*cellH+20;
  const pos={}; types.forEach((t,i)=>{ pos[t.name]={x:(i%col)*cellW+cellW/2, y:Math.floor(i/col)*cellH+cellH/2+10}; });
  const cv=document.createElement('canvas'); cv.width=W; cv.height=H; cv.style.width='100%';
  slot.innerHTML=''; slot.appendChild(cv);
  const ctx=cv.getContext('2d');
  ctx.font='12px sans-serif';
  // 边
  sch.linkTypes.forEach(lt=>{
    const a=pos[lt.from], b=pos[lt.to]; if(!a||!b) return;
    ctx.strokeStyle='#94a3b8'; ctx.lineWidth=1.5;
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
    const mx=(a.x+b.x)/2, my=(a.y+b.y)/2;
    ctx.fillStyle='#475569';
    const tag=`${lt.label||lt.name} ${lt.cardinality}`;
    ctx.fillText(tag,mx-ctx.measureText(tag).width/2,my-6);
  });
  // 节点
  types.forEach(t=>{
    const p=pos[t.name], w=110,h=44, x=p.x-w/2, y=p.y-h/2;
    ctx.fillStyle=t.id===focusTypeId?'#dbeafe':'#ffffff';
    ctx.strokeStyle=t.color||'#cbd5e1'; ctx.lineWidth=t.id===focusTypeId?2.5:1.5;
    ctx.beginPath(); ctx.roundRect(x,y,w,h,8); ctx.fill(); ctx.stroke();
    ctx.fillStyle='#0f172a'; ctx.textAlign='center';
    ctx.fillText(`${t.icon||''} ${(t.label||t.name).slice(0,8)}`,p.x,p.y+4); ctx.textAlign='start';
  });
  cv.onclick=e=>{
    const r=cv.getBoundingClientRect(), sx=cv.width/r.width;
    const cx=(e.clientX-r.left)*sx, cy=(e.clientY-r.top)*sx;
    for(const t of types){ const p=pos[t.name];
      if(Math.abs(cx-p.x)<55&&Math.abs(cy-p.y)<22){ APP.go('objectType',t.id); return; } }
  };
};

// ── LinkType 列表 ──
APP.VIEWS.linkTypes=(el,state)=>{
  const sch=CORE.schemaOf(state);
  el.innerHTML=`<h2>链接类型 <button class="btn btn-primary" id="lt-new" style="float:right">＋ 新建链接类型</button></h2>
  ${sch.linkTypes.map(lt=>{
    const n=state.data.links.filter(l=>l.__type===lt.id).length;
    return `<div class="card" data-id="${lt.id}" style="cursor:pointer">
      <b>🔗 ${APP.esc(lt.label||lt.name)}</b> <span class="badge">${lt.cardinality}</span>
      <div class="mut mono">${lt.from} → ${lt.to} · ${n} 条实例</div></div>`;
  }).join('')||'<p class="mut">暂无链接类型</p>'}`;
  el.querySelector('#lt-new').onclick=()=>APP.VIEWS._newLinkType();
  el.querySelectorAll('[data-id]').forEach(c=>c.onclick=()=>APP.go('linkType',c.dataset.id));
};

// ── LinkType 详情 ──
APP.VIEWS.linkType=(el,state)=>{
  const sch=CORE.schemaOf(state);
  const lt=sch.linkTypes.find(x=>x.id===state.ui.sel);
  if(!lt){ el.innerHTML='<p class="mut">链接类型不存在</p>'; return; }
  const n=state.data.links.filter(l=>l.__type===lt.id).length;
  const names=sch.objectTypes.map(t=>t.name);
  el.innerHTML=`<h2>🔗 ${APP.esc(lt.label||lt.name)}</h2>
  <div class="card"><h3>Overview</h3>
    <div class="grid2">
      <div class="form-row"><label>Label</label><input id="lt-label" value="${APP.esc(lt.label||'')}"></div>
      <div class="form-row"><label>基数</label><select id="lt-card">${CORE.CARDINALITIES.map(c=>`<option ${c===lt.cardinality?'selected':''}>${c}</option>`).join('')}</select></div>
      <div class="form-row"><label>From(源类型)</label><select id="lt-from">${names.map(x=>`<option ${x===lt.from?'selected':''}>${x}</option>`).join('')}</select></div>
      <div class="form-row"><label>To(目标类型)</label><select id="lt-to">${names.map(x=>`<option ${x===lt.to?'selected':''}>${x}</option>`).join('')}</select></div>
    </div>
    <button class="btn btn-primary" id="lt-save">保存</button>
    <button class="btn btn-danger" id="lt-del" style="margin-left:8px">删除</button>
    <div class="mut" style="margin-top:8px">实例 ${n} 条 · 修改端点后既有实例不受影响,新增按新约束校验</div>
  </div>
  <div class="card"><h3>Datasources(外键映射)</h3>
    <div class="grid2">
      <div class="form-row"><label>源端键(fromKey)</label><input id="lt-fk" value="${APP.esc(lt.keyMapping?.fromKey||'')}"></div>
      <div class="form-row"><label>目标端键(toKey)</label><input id="lt-tk" value="${APP.esc(lt.keyMapping?.toKey||'')}"></div>
    </div>
    <button class="btn" id="lt-km-save">保存映射</button>
  </div>`;
  el.querySelector('#lt-save').onclick=()=>{
    const r=CORE.updateLinkType(state,lt.id,{label:el.querySelector('#lt-label').value,
      cardinality:el.querySelector('#lt-card').value,from:el.querySelector('#lt-from').value,to:el.querySelector('#lt-to').value});
    r.ok?(APP.store.save(),APP.render(),APP.toast('已保存')):APP.toast(r.error,'error');
  };
  el.querySelector('#lt-km-save').onclick=()=>{
    const r=CORE.updateLinkType(state,lt.id,{keyMapping:{fromKey:el.querySelector('#lt-fk').value,toKey:el.querySelector('#lt-tk').value}});
    r.ok?(APP.store.save(),APP.toast('已保存')):APP.toast(r.error,'error');
  };
  el.querySelector('#lt-del').onclick=()=>{
    const r=CORE.deleteLinkType(state,lt.id);
    r.ok?(APP.store.save(),APP.go('linkTypes'),APP.toast('已删除')):APP.toast(r.error,'error');
  };
};

APP.VIEWS._newLinkType=()=>{
  const sch=CORE.schemaOf(APP.state);
  const names=sch.objectTypes.map(t=>t.name);
  if(names.length<1){ APP.toast('请先创建对象类型','error'); return; }
  APP.modal({title:'新建链接类型',bodyHTML:`
    <div class="form-row"><label>名称(小写 snake)</label><input id="nl-name"></div>
    <div class="form-row"><label>Label</label><input id="nl-label"></div>
    <div class="grid2">
      <div class="form-row"><label>From</label><select id="nl-from">${names.map(n=>`<option>${n}</option>`).join('')}</select></div>
      <div class="form-row"><label>To</label><select id="nl-to">${names.map(n=>`<option>${n}</option>`).join('')}</select></div>
    </div>
    <div class="form-row"><label>基数</label><select id="nl-card">${CORE.CARDINALITIES.map(c=>`<option>${c}</option>`).join('')}</select></div>
    <div class="form-err" id="nl-err"></div>`,actions:[
    {label:'取消'},{label:'创建',kind:'primary',onClick:root=>{
      const r=CORE.addLinkType(APP.state,{name:root.querySelector('#nl-name').value.trim(),
        label:root.querySelector('#nl-label').value,from:root.querySelector('#nl-from').value,
        to:root.querySelector('#nl-to').value,cardinality:root.querySelector('#nl-card').value});
      if(!r.ok){ root.querySelector('#nl-err').textContent=r.error; return false; }
      APP.store.save(); APP.go('linkType',r.id); APP.toast('链接类型已创建');
    }}]});
};

// ── 共享属性 ──
APP.VIEWS.sharedProps=(el,state)=>{
  const sch=CORE.schemaOf(state);
  el.innerHTML=`<h2>共享属性 <button class="btn btn-primary" id="sp-new" style="float:right">＋ 新建共享属性</button></h2>
  ${(sch.sharedProps||[]).map(sp=>{
    const used=sch.objectTypes.filter(t=>(t.sharedPropRefs||[]).includes(sp.name));
    return `<div class="card"><b>🧩 ${APP.esc(sp.label||sp.name)}</b> <span class="badge">${sp.baseType}</span>
      <button class="btn btn-danger" data-del="${sp.id}" style="float:right" ${used.length?'disabled title="被引用中"':''}>删除</button>
      <div class="mut mono">${sp.name} · 挂载于:${used.map(t=>APP.esc(t.label||t.name)).join('、')||'无'}</div></div>`;
  }).join('')||'<p class="mut">暂无共享属性</p>'}`;
  el.querySelector('#sp-new').onclick=()=>APP.VIEWS._newSharedProp();
  el.querySelectorAll('[data-del]').forEach(b=>b.onclick=()=>{
    const r=CORE.deleteSharedProp(state,b.dataset.del);
    r.ok?(APP.store.save(),APP.render(),APP.toast('已删除')):APP.toast(r.error,'error');
  });
};
APP.VIEWS._newSharedProp=()=>{
  APP.modal({title:'新建共享属性',bodyHTML:`
    <div class="form-row"><label>名称(小写 snake)</label><input id="ns-name"></div>
    <div class="form-row"><label>Label</label><input id="ns-label"></div>
    <div class="form-row"><label>基础类型</label><select id="ns-bt">${CORE.BASE_TYPES.map(b=>`<option>${b}</option>`).join('')}</select></div>
    <div class="form-err" id="ns-err"></div>`,actions:[
    {label:'取消'},{label:'创建',kind:'primary',onClick:root=>{
      const r=CORE.addSharedProp(APP.state,{name:root.querySelector('#ns-name').value.trim(),
        label:root.querySelector('#ns-label').value,baseType:root.querySelector('#ns-bt').value});
      if(!r.ok){ root.querySelector('#ns-err').textContent=r.error; return false; }
      APP.store.save(); APP.render(); APP.toast('共享属性已创建');
    }}]});
};
```

- [ ] **Step 4: 运行 smoke 确认通过**(36 passed)

- [ ] **Step 5: Commit**

```bash
git add ontoforge.html smoke.mjs
git commit -m "feat(ui): LinkType 视图/canvas schema 关系图/共享属性"
```

---

### Task 12: ActionType 视图(Logic 编辑器 + Observability)+ RunActionModal + 通知中心

**Files:**
- Modify: `ontoforge.html`(id="appjs" 段追加)
- Modify: `smoke.mjs`(追加 S11 静态断言)

**Interfaces:**
- Consumes: `CORE.runAction/addActionType/updateActionType/deleteActionType/usageByDay/auditFor/unreadNotices/markNoticesRead/describeEdits`
- Produces:
  - `VIEWS.actionType(el,state)` — 三页签 Overview / Logic / Observability:
    - Overview:label、targets(role+type chips)、删除动作
    - Logic 流水线编辑器:参数表(增删行:name/label/type/required/enumValues)、规则表(target/field/op/value/message)、submissionCriteria(requireConfirm 勾选+note)、edits 表(op 下拉驱动字段显隐:set→target/field/value;create→target role/objectType/props JSON;delete→target;addLink/removeLink→linkType/from/to)、sideEffects 表(notify:to/text;webhookLog:url)——全部表单化,保存走 `CORE.updateActionType`(传整个 def patch);结构错误内联展示
    - Observability:近 30 天调用柱状图(div 条形,`usageByDay`)+ 最近 10 条审计(`auditFor`)
  - `APP.openRunAction(actionId,prefillTargets?)` — 运行弹窗:target 选择器(每个 role 一个下拉,候选=该 type 全部实例,label 用 `objectLabel`)+ 参数表单(enum 下拉/其它 input)→ `CORE.runAction`;返回 `needConfirm` 时弹确认框展示 `preview`(diff 行列表),确认后带 `confirmed:true` 重跑;`ok` → toast + 关闭 + `APP.render()`;`error` → 内联红字
  - 通知中心:`#btn-notify` 点击 → modal 列出 `state.notices` 倒序(时间/to/text),底部「全部已读」按钮调 `markNoticesRead`+save+render
  - `VIEWS._newActionType()` — modal(name/label)→ 创建后跳 actionType 视图

- [ ] **Step 1: smoke S11(静态断言,先 FAIL)**

```js
// ── S11 ActionType/运行弹窗/通知 静态断言 ──
T('S11.1 视图挂载', ()=>{
  const app=section('appjs');
  for(const v of ['VIEWS.actionType','openRunAction','_newActionType','Observability','Logic'])
    ok(app.includes(v),'缺 '+v);
  ok(app.includes('needConfirm'),'确认流');
  ok(app.includes('usageByDay'),'用量柱状数据源');
});
```

- [ ] **Step 2: 运行确认 FAIL**

- [ ] **Step 3: appjs 追加实现**

```js
// ── ActionType 视图 ──
APP.VIEWS.actionType=(el,state)=>{
  const sch=CORE.schemaOf(state);
  const a=sch.actionTypes.find(x=>x.id===state.ui.sel);
  if(!a){ el.innerHTML='<p class="mut">动作不存在</p>'; return; }
  const tab=(state.ui.sel2||'overview');
  const tabs=[['overview','Overview'],['logic','Logic'],['obs','Observability']];
  el.innerHTML=`<h2>⚡ ${APP.esc(a.label||a.name)} <span class="badge mono">${a.name}</span>
    <button class="btn btn-primary" id="at-run" style="float:right">▶ 运行</button></h2>
  <div style="margin-bottom:14px">${tabs.map(([k,l])=>`<button class="btn ${tab===k?'btn-primary':''}" data-tab="${k}">${l}</button>`).join(' ')}
    <button class="btn btn-danger" id="at-del" style="float:right">删除动作</button></div>
  <div id="at-body"></div>`;
  el.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{ state.ui.sel2=b.dataset.tab; APP.store.save(); APP.render(); });
  el.querySelector('#at-run').onclick=()=>APP.openRunAction(a.id);
  el.querySelector('#at-del').onclick=()=>{
    const r=CORE.deleteActionType(state,a.id);
    r.ok?(APP.store.save(),APP.go('discover'),APP.toast('已删除')):APP.toast(r.error,'error');
  };
  const body=el.querySelector('#at-body');
  if(tab==='overview'){
    body.innerHTML=`<div class="card"><h3>基本信息</h3>
      <div class="form-row"><label>Label</label><input id="a-label" value="${APP.esc(a.label||'')}"></div>
      <div class="mut">目标角色:${a.targets.map(t=>`<span class="chip">${t.role} : ${t.type}</span>`).join('')||'无'}</div>
      <div style="margin-top:10px"><button class="btn btn-primary" id="a-label-save">保存 Label</button></div></div>
      <div class="card"><h3>说明</h3><div class="mut">在 Logic 页配置参数→规则→提交条件→编辑→副作用流水线;在 Observability 页查看调用量与历史。</div></div>`;
    body.querySelector('#a-label-save').onclick=()=>{
      const r=CORE.updateActionType(state,a.id,{label:body.querySelector('#a-label').value});
      r.ok?(APP.store.save(),APP.render(),APP.toast('已保存')):APP.toast(r.error,'error');
    };
  }
  if(tab==='logic'){
    const E=APP.esc;
    body.innerHTML=`
    <div class="card"><h3>① 参数 Params</h3><div id="lg-params"></div><button class="btn" id="lg-add-param">＋ 参数</button></div>
    <div class="card"><h3>② 规则 Rules(执行前校验)</h3><div id="lg-rules"></div><button class="btn" id="lg-add-rule">＋ 规则</button></div>
    <div class="card"><h3>③ 提交条件</h3>
      <label><input type="checkbox" id="lg-confirm" ${a.submissionCriteria?.requireConfirm?'checked':''}> 需要用户确认</label>
      <div class="form-row" style="margin-top:8px"><label>确认提示</label><input id="lg-note" value="${E(a.submissionCriteria?.note||'')}"></div></div>
    <div class="card"><h3>④ 编辑 Edits(模板支持 {{param.x}} {{targets.role.prop}} {{now}} {{auto}})</h3><div id="lg-edits"></div><button class="btn" id="lg-add-edit">＋ 编辑</button></div>
    <div class="card"><h3>⑤ 副作用 Side effects</h3><div id="lg-effects"></div><button class="btn" id="lg-add-eff">＋ 副作用</button></div>
    <button class="btn btn-primary" id="lg-save" style="position:sticky;bottom:12px">💾 保存 Logic</button>
    <div class="form-err" id="lg-err"></div>`;
    const paramRow=(p={})=>`<div class="grid2 lg-row" style="border-bottom:1px dashed var(--line);padding:8px 0">
      <input data-f="name" placeholder="name" class="mono" value="${E(p.name||'')}">
      <input data-f="label" placeholder="label" value="${E(p.label||'')}">
      <select data-f="type">${CORE.BASE_TYPES.map(b=>`<option ${p.type===b?'selected':''}>${b}</option>`).join('')}</select>
      <input data-f="enumValues" placeholder="枚举值,逗号分隔" value="${E((p.enumValues||[]).join(','))}">
      <label><input type="checkbox" data-f="required" ${p.required?'checked':''}> 必填</label>
      <button class="btn lg-del">删</button></div>`;
    const ruleRow=(r={})=>`<div class="grid2 lg-row" style="border-bottom:1px dashed var(--line);padding:8px 0">
      <input data-f="target" placeholder="target role" class="mono" value="${E(r.target||'')}">
      <input data-f="field" placeholder="field" class="mono" value="${E(r.field||'')}">
      <select data-f="op">${CORE.RULE_OPS.map(o=>`<option ${r.op===o?'selected':''}>${o}</option>`).join('')}</select>
      <input data-f="value" placeholder="value(in 用 | 分隔)" value="${E(r.value||'')}">
      <input data-f="message" placeholder="失败提示" value="${E(r.message||'')}">
      <button class="btn lg-del">删</button></div>`;
    const editRow=(e={})=>`<div class="grid2 lg-row" style="border-bottom:1px dashed var(--line);padding:8px 0">
      <select data-f="op">${CORE.EDIT_OPS.map(o=>`<option ${e.op===o?'selected':''}>${o}</option>`).join('')}</select>
      <input data-f="target" placeholder="target role" class="mono" value="${E(e.target||'')}">
      <input data-f="field" placeholder="field(set)" class="mono" value="${E(e.field||'')}">
      <input data-f="value" placeholder="value 模板" value="${E(e.value||'')}">
      <input data-f="objectType" placeholder="objectType(create)" class="mono" value="${E(e.objectType||'')}">
      <input data-f="props" placeholder='props JSON(create)' class="mono" value="${E(e.props?JSON.stringify(e.props):'')}">
      <input data-f="linkType" placeholder="linkType(add/removeLink)" class="mono" value="${E(e.linkType||'')}">
      <input data-f="from" placeholder="from role" class="mono" value="${E(e.from||'')}">
      <input data-f="to" placeholder="to role" class="mono" value="${E(e.to||'')}">
      <button class="btn lg-del">删</button></div>`;
    const effRow=(f={})=>`<div class="grid2 lg-row" style="border-bottom:1px dashed var(--line);padding:8px 0">
      <select data-f="type"><option ${f.type==='notify'?'selected':''}>notify</option><option ${f.type==='webhookLog'?'selected':''}>webhookLog</option></select>
      <input data-f="to" placeholder="to(notify)" value="${E(f.config?.to||'')}">
      <input data-f="text" placeholder="text 模板(notify)" value="${E(f.config?.text||'')}">
      <input data-f="url" placeholder="url(webhookLog)" class="mono" value="${E(f.config?.url||'')}">
      <button class="btn lg-del">删</button></div>`;
    body.querySelector('#lg-params').innerHTML=a.params.map(paramRow).join('');
    body.querySelector('#lg-rules').innerHTML=a.rules.map(ruleRow).join('');
    body.querySelector('#lg-edits').innerHTML=a.edits.map(editRow).join('');
    body.querySelector('#lg-effects').innerHTML=a.sideEffects.map(effRow).join('');
    const addRow=(box,row)=>{ box.insertAdjacentHTML('beforeend',row()); };
    body.querySelector('#lg-add-param').onclick=()=>addRow(body.querySelector('#lg-params'),paramRow);
    body.querySelector('#lg-add-rule').onclick=()=>addRow(body.querySelector('#lg-rules'),ruleRow);
    body.querySelector('#lg-add-edit').onclick=()=>addRow(body.querySelector('#lg-edits'),editRow);
    body.querySelector('#lg-add-eff').onclick=()=>addRow(body.querySelector('#lg-effects'),effRow);
    body.addEventListener('click',e=>{ if(e.target.classList.contains('lg-del')) e.target.closest('.lg-row').remove(); });
    body.querySelector('#lg-save').onclick=()=>{
      const rows=sel=>[...body.querySelectorAll(sel)];
      const val=(row,f)=>row.querySelector(`[data-f="${f}"]`)?.value??'';
      const chk=(row,f)=>row.querySelector(`[data-f="${f}"]`)?.checked;
      const patch={
        params:rows('#lg-params .lg-row').map(r=>({name:val(r,'name').trim(),label:val(r,'label'),type:val(r,'type'),
          required:chk(r,'required'),enumValues:val(r,'type')==='enum'?val(r,'enumValues').split(',').map(s=>s.trim()).filter(Boolean):null})),
        rules:rows('#lg-rules .lg-row').map(r=>({target:val(r,'target').trim(),field:val(r,'field').trim(),op:val(r,'op'),value:val(r,'value'),message:val(r,'message')})),
        submissionCriteria:{requireConfirm:body.querySelector('#lg-confirm').checked,note:body.querySelector('#lg-note').value},
        edits:rows('#lg-edits .lg-row').map(r=>{ const e={op:val(r,'op'),target:val(r,'target').trim()};
          if(val(r,'field')) e.field=val(r,'field').trim();
          if(val(r,'value')) e.value=val(r,'value');
          if(val(r,'objectType')) e.objectType=val(r,'objectType').trim();
          if(val(r,'props')){ try{ e.props=JSON.parse(val(r,'props')); }catch(x){ return {_bad:'props JSON 错误'}; } }
          if(val(r,'linkType')) e.linkType=val(r,'linkType').trim();
          if(val(r,'from')) e.from=val(r,'from').trim();
          if(val(r,'to')) e.to=val(r,'to').trim();
          return e; }),
        sideEffects:rows('#lg-effects .lg-row').map(r=>({type:val(r,'type'),
          config:val(r,'type')==='notify'?{to:val(r,'to'),text:val(r,'text')}:{url:val(r,'url')}}))
      };
      if(patch.edits.some(e=>e._bad)){ body.querySelector('#lg-err').textContent='存在 props JSON 格式错误'; return; }
      const r=CORE.updateActionType(state,a.id,patch);
      r.ok?(APP.store.save(),APP.render(),APP.toast('Logic 已保存')):body.querySelector('#lg-err').textContent=r.error;
    };
  }
  if(tab==='obs'){
    const days=CORE.usageByDay(state,a.id,30);
    const max=Math.max(1,...days.map(d=>d.count));
    const audit=CORE.auditFor(state,{actionId:a.id}).slice(-10).reverse();
    body.innerHTML=`<div class="card"><h3>近 30 天调用量</h3>
      <div style="display:flex;align-items:flex-end;gap:2px;height:80px">
      ${days.map(d=>`<div title="${d.day}: ${d.count}" style="flex:1;background:${d.count?'var(--pri)':'#e2e8f0'};height:${Math.max(4,d.count/max*76)}px;border-radius:2px"></div>`).join('')}</div>
      <div class="mut" style="display:flex;justify-content:space-between"><span>${days[0].day}</span><span>${days[29].day}</span></div></div>
    <div class="card"><h3>最近执行(≤10)</h3>
      ${audit.map(e=>`<div style="border-bottom:1px solid var(--line);padding:8px 0">
        <span class="mut mono">${e.ts.replace('T',' ').slice(0,19)}</span> · ${APP.esc(e.actor||'本地用户')} · ${APP.esc(e.summary)}
        <div class="mut mono" style="font-size:11px">${e.diff.map(APP.esc).join('<br>')}</div></div>`).join('')||'<span class="mut">尚无执行记录</span>'}</div>`;
  }
};

// ── 运行动作弹窗 ──
APP.openRunAction=(actionId,prefill)=>{
  const state=APP.state, sch=CORE.schemaOf(state);
  const a=sch.actionTypes.find(x=>x.id===actionId);
  if(!a) return APP.toast('动作不存在','error');
  const E=APP.esc;
  const targetFields=a.targets.map(t=>{
    const cands=CORE.objectsOfType(state,t.type);
    return `<div class="form-row"><label>目标 ${t.role} : ${t.type}</label>
      <select data-tg="${t.role}">${cands.map(o=>`<option value="${o.__id}" ${prefill&&prefill[t.role]===o.__id?'selected':''}>${E(CORE.objectLabel(state,o))}(${o.__id})</option>`).join('')}</select></div>`;
  }).join('');
  const paramFields=a.params.map(p=>`<div class="form-row"><label>${E(p.label||p.name)}${p.required?' *':''}</label>
    ${p.type==='enum'
      ?`<select data-pr="${p.name}">${(p.enumValues||[]).map(v=>`<option>${E(v)}</option>`).join('')}</select>`
      :`<input data-pr="${p.name}" type="${p.type==='number'?'number':p.type==='date'?'date':p.type==='boolean'?'checkbox':'text'}">`}
  </div>`).join('');
  const collect=root=>{
    const params={},targets={};
    root.querySelectorAll('[data-tg]').forEach(s=>targets[s.dataset.tg]=s.value);
    root.querySelectorAll('[data-pr]').forEach(s=>params[s.dataset.pr]=s.type==='checkbox'?s.checked:s.value);
    return {params,targets};
  };
  APP.modal({title:`▶ ${E(a.label||a.name)}`,bodyHTML:`${targetFields}${paramFields}<div class="form-err" id="ra-err"></div>`,actions:[
    {label:'取消'},{label:'执行',kind:'primary',onClick:root=>{
      const {params,targets}=collect(root);
      const r=CORE.runAction(state,a.id,{params,targets,actor:'本地用户'});
      if(r.ok){ APP.store.save(); APP.render(); APP.toast('执行成功'); return; }
      if(r.needConfirm){
        APP.modal({title:'确认执行',bodyHTML:`${a.submissionCriteria?.note?`<p>${E(a.submissionCriteria.note)}</p>`:''}
          <div class="card"><b>将产生以下变更:</b><div class="mono" style="font-size:12px">${r.preview.map(E).join('<br>')}</div></div>`,actions:[
          {label:'再想想'},{label:'确认执行',kind:'primary',onClick:()=>{
            const r2=CORE.runAction(state,a.id,{params,targets,actor:'本地用户',confirmed:true});
            r2.ok?(APP.store.save(),APP.render(),APP.toast('执行成功')):APP.toast(r2.error,'error');
          }}]});
        return; // 保留底层表单(确认框叠在上面,关闭后仍在)
      }
      root.querySelector('#ra-err').textContent=r.error; return false;
    }}]});
};

// ── 通知中心 ──
document.addEventListener('DOMContentLoaded',()=>{
  document.querySelector('#btn-notify').addEventListener('click',()=>{
    const state=APP.state;
    const list=[...state.notices].reverse();
    APP.modal({title:'🔔 通知中心',bodyHTML:
      list.map(n=>`<div style="border-bottom:1px solid var(--line);padding:8px 0;${n.read?'opacity:.55':''}">
        <span class="mut mono">${n.ts.replace('T',' ').slice(0,19)}</span> → <b>${APP.esc(n.to)}</b><br>${APP.esc(n.text)}</div>`).join('')
      ||'<p class="mut">暂无通知</p>',actions:[
      {label:'全部已读',onClick:()=>{ CORE.markNoticesRead(state); APP.store.save(); APP.render(); }},
      {label:'关闭'}]});
  });
});

APP.VIEWS._newActionType=()=>{
  APP.modal({title:'新建动作类型',bodyHTML:`
    <div class="form-row"><label>名称(小写 snake)</label><input id="na-name"></div>
    <div class="form-row"><label>Label</label><input id="na-label"></div>
    <div class="form-err" id="na-err"></div>`,actions:[
    {label:'取消'},{label:'创建',kind:'primary',onClick:root=>{
      const r=CORE.addActionType(APP.state,{name:root.querySelector('#na-name').value.trim(),
        label:root.querySelector('#na-label').value,targets:[],params:[],rules:[],
        submissionCriteria:{requireConfirm:false},edits:[],sideEffects:[]});
      if(!r.ok){ root.querySelector('#na-err').textContent=r.error; return false; }
      APP.store.save(); APP.go('actionType',r.id); APP.toast('动作已创建,请在 Logic 页配置');
    }}]});
};
```

注意:modal 嵌套(确认框叠在运行表单上)依赖 `APP.modal` 每次整体替换 `#modal-root` —— 本实现中确认框会**替换**运行表单。为保留表单,Step 3 的 `APP.modal` 需支持栈式:把 `modal()` 改为每次创建独立 `.modal-mask` 节点 append 到 `#modal-root` 而非 innerHTML 覆盖,close 时移除自身节点。**执行时按此修正 Task 9 的 modal 实现**(smoke 不涉及,无需改断言)。

- [ ] **Step 4: 运行 smoke 确认通过**(37 passed)

- [ ] **Step 5: Commit**

```bash
git add ontoforge.html smoke.mjs
git commit -m "feat(ui): ActionType 三页签视图/运行弹窗(确认流)/通知中心"
```

---

### Task 13: Object Explorer + Object View

**Files:**
- Modify: `ontoforge.html`(id="appjs" 段追加)
- Modify: `smoke.mjs`(追加 S12 静态断言)

**Interfaces:**
- Consumes: `CORE.searchObjects/objectsOfType/objectLabel/linkedObjects/auditFor/createLink/deleteLink`
- Produces:
  - `VIEWS.explorer(el,state)` — 三栏:左=类型列表(带实例计数);中=搜索框+结果表(选中类型的实例,行点击进 Object View;列=该类型前 5 属性);右=提示
  - `VIEWS.objectView(el,state)` — sel={typeName,objectId}:
    - 属性卡(全部属性键值,主键 🔑 标注)
    - 链接对象 chips:按 `linkedObjects` 分组展示(linkType label + direction 箭头 + chip),点 chip 跳对方 Object View;chip 上 ✕ 删除该 link(confirm modal)
    - 添加链接:下拉选 linkType(限定端点类型匹配)+ 下拉选对端对象 → `CORE.createLink`
    - 可用 Actions:schema 中 targets 含该类型(单 target 或该类型可作为某 role)的动作按钮;点击 → `APP.openRunAction(actionId,{role:objectId} 预填)`
    - 编辑历史:`auditFor(state,{objectId})` 倒序列表
    - 顶部全局搜索结果也跳这里

- [ ] **Step 1: smoke S12(静态断言,先 FAIL)**

```js
// ── S12 Explorer/ObjectView 静态断言 ──
T('S12.1 视图挂载', ()=>{
  const app=section('appjs');
  for(const v of ['VIEWS.explorer','VIEWS.objectView','linkedObjects','添加链接','编辑历史','可用动作'])
    ok(app.includes(v),'缺 '+v);
});
```

- [ ] **Step 2: 运行确认 FAIL**

- [ ] **Step 3: appjs 追加实现**

```js
// ── Object Explorer ──
APP.VIEWS.explorer=(el,state)=>{
  const sch=CORE.schemaOf(state);
  const selType=state.ui.sel?.typeName||sch.objectTypes[0]?.name||null;
  const q=state.ui.sel?.q||'';
  const t=sch.objectTypes.find(x=>x.name===selType);
  const results=t?CORE.searchObjects(state,selType,q):[];
  el.innerHTML=`<h2>🔍 Object Explorer</h2>
  <div style="display:grid;grid-template-columns:200px 1fr;gap:16px">
    <div class="card" style="margin:0"><h3>类型</h3>
      ${sch.objectTypes.map(x=>`<a class="side-item" data-type="${x.name}" style="color:var(--ink);${x.name===selType?'background:#dbeafe;border-radius:6px':''}">
        ${x.icon||'📦'} ${APP.esc(x.label||x.name)}<span class="cnt">${CORE.objectsOfType(state,x.name).length}</span></a>`).join('')||'<span class="mut">无类型</span>'}
    </div>
    <div class="card" style="margin:0">
      <input id="ex-q" placeholder="搜索 ${APP.esc(t?.label||'')} 实例…" value="${APP.esc(q)}" style="width:100%;padding:8px 12px;border:1px solid var(--line);border-radius:6px;margin-bottom:12px">
      ${t?`<table class="table"><tr>${t.properties.slice(0,5).map(p=>`<th>${APP.esc(p.label||p.name)}</th>`).join('')}</tr>
        ${results.slice(0,50).map(o=>`<tr data-obj="${o.__id}" style="cursor:pointer">${t.properties.slice(0,5).map(p=>`<td>${APP.esc(o.props[p.name]??'')}</td>`).join('')}</tr>`).join('')||'<tr><td class="mut">无匹配实例</td></tr>'}</table>
        <div class="mut" style="margin-top:6px">${results.length} 条结果${results.length>50?'(仅显示前 50)':''}</div>`:'<p class="mut">请先创建对象类型</p>'}
    </div>
  </div>`;
  el.querySelectorAll('[data-type]').forEach(a=>a.onclick=()=>APP.go('explorer',{typeName:a.dataset.type,q:''}));
  const qi=el.querySelector('#ex-q');
  if(qi){ qi.oninput=()=>{ state.ui.sel={typeName:selType,q:qi.value}; APP.store.save();
      clearTimeout(APP._exT); APP._exT=setTimeout(()=>{ APP.render(); const nq=document.querySelector('#ex-q'); if(nq){nq.focus();nq.setSelectionRange(nq.value.length,nq.value.length);} },250); };
    if(q){ qi.focus(); qi.setSelectionRange(q.length,q.length); } }
  el.querySelectorAll('[data-obj]').forEach(r=>r.onclick=()=>APP.go('objectView',{typeName:selType,objectId:r.dataset.obj}));
};

// ── Object View ──
APP.VIEWS.objectView=(el,state)=>{
  const {typeName,objectId}=state.ui.sel||{};
  const sch=CORE.schemaOf(state);
  const t=sch.objectTypes.find(x=>x.name===typeName);
  const o=state.data.objects.find(x=>x.__id===objectId);
  if(!t||!o){ el.innerHTML='<p class="mut">对象不存在</p>'; return; }
  const linked=CORE.linkedObjects(state,objectId);
  const history=CORE.auditFor(state,{objectId}).slice(-10).reverse();
  const availActions=sch.actionTypes.filter(a=>a.targets.some(tg=>tg.type===typeName));
  el.innerHTML=`
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px">
    <a style="cursor:pointer;color:var(--pri)" id="ov-back">← Explorer</a>
    <span style="font-size:22px">${t.icon||'📦'}</span>
    <h2 style="margin:0">${APP.esc(CORE.objectLabel(state,o))}</h2>
    <span class="badge mono">${o.__id}</span>
  </div>
  <div class="grid2">
    <div>
      <div class="card"><h3>属性</h3>
        <table class="table">${t.properties.map(p=>`<tr><td class="mut">${APP.esc(p.label||p.name)}${p.name===t.primaryKey?' 🔑':''}</td>
          <td>${APP.esc(o.props[p.name]??'—')}</td></tr>`).join('')}</table></div>
      <div class="card"><h3>可用动作</h3>
        ${availActions.map(a=>{
          const role=a.targets.find(tg=>tg.type===typeName).role;
          return `<button class="btn btn-primary" data-act="${a.id}" data-role="${role}" style="margin:2px">▶ ${APP.esc(a.label||a.name)}</button>`;
        }).join('')||'<span class="mut">无适用动作</span>'}</div>
      <div class="card"><h3>编辑历史</h3>
        ${history.map(e=>`<div style="border-bottom:1px solid var(--line);padding:6px 0">
          <span class="mut mono">${e.ts.replace('T',' ').slice(0,19)}</span> · ${APP.esc(e.summary)}
          <div class="mut mono" style="font-size:11px">${e.diff.map(APP.esc).join('<br>')}</div></div>`).join('')||'<span class="mut">暂无历史</span>'}</div>
    </div>
    <div>
      <div class="card"><h3>链接对象(${linked.length})</h3>
        ${linked.map((l,i)=>`<div style="margin-bottom:6px">
          <span class="badge">${APP.esc(l.linkType.label||l.linkType.name)} ${l.direction==='out'?'→':'←'}</span>
          <span class="chip" data-linked="${l.object.__id}" data-ltype="${l.object.__type}">${APP.esc(CORE.objectLabel(state,l.object))}</span>
          <a data-unlink="${i}" style="cursor:pointer;color:var(--dan);font-size:12px">✕ 解除</a></div>`).join('')||'<span class="mut">无链接</span>'}
      </div>
      <div class="card"><h3>添加链接</h3>
        <div class="form-row"><label>链接类型</label><select id="ov-lt">
          ${sch.linkTypes.filter(l=>l.from===typeName||l.to===typeName).map(l=>`<option value="${l.id}">${APP.esc(l.label||l.name)}(${l.from}→${l.to})</option>`).join('')}
        </select></div>
        <div class="form-row"><label>对端对象</label><select id="ov-peer"></select></div>
        <button class="btn btn-primary" id="ov-link">建立链接</button>
        <div class="form-err" id="ov-lerr"></div>
      </div>
    </div>
  </div>`;
  el.querySelector('#ov-back').onclick=()=>APP.go('explorer',{typeName,q:''});
  el.querySelectorAll('[data-linked]').forEach(c=>c.onclick=()=>APP.go('objectView',{typeName:c.dataset.ltype,objectId:c.dataset.linked}));
  el.querySelectorAll('[data-unlink]').forEach(a=>a.onclick=()=>{
    const l=linked[+a.dataset.unlink];
    APP.modal({title:'解除链接',bodyHTML:`确认解除与 <b>${APP.esc(CORE.objectLabel(state,l.object))}</b> 的链接?`,actions:[
      {label:'取消'},{label:'解除',kind:'danger',onClick:()=>{
        const lt=l.linkType;
        const from=l.direction==='out'?objectId:l.object.__id, to=l.direction==='out'?l.object.__id:objectId;
        const r=CORE.deleteLink(state,lt.id,from,to);
        r.ok?(APP.store.save(),APP.render(),APP.toast('已解除')):APP.toast(r.error,'error');
      }}]});
  });
  const syncPeer=()=>{
    const ltId=el.querySelector('#ov-lt').value;
    const lt=sch.linkTypes.find(x=>x.id===ltId); if(!lt){ el.querySelector('#ov-peer').innerHTML=''; return; }
    const peerType=lt.from===typeName?lt.to:lt.from;
    el.querySelector('#ov-peer').innerHTML=CORE.objectsOfType(state,peerType)
      .filter(p=>p.__id!==objectId)
      .map(p=>`<option value="${p.__id}">${APP.esc(CORE.objectLabel(state,p))}</option>`).join('');
  };
  el.querySelector('#ov-lt').onchange=syncPeer; syncPeer();
  el.querySelector('#ov-link').onclick=()=>{
    const ltId=el.querySelector('#ov-lt').value, peer=el.querySelector('#ov-peer').value;
    const lt=sch.linkTypes.find(x=>x.id===ltId); if(!lt||!peer) return;
    const from=lt.from===typeName?objectId:peer, to=lt.from===typeName?peer:objectId;
    const r=CORE.createLink(state,ltId,from,to);
    r.ok?(APP.store.save(),APP.render(),APP.toast('链接已建立')):el.querySelector('#ov-lerr').textContent=r.error;
  };
  el.querySelectorAll('[data-act]').forEach(b=>b.onclick=()=>APP.openRunAction(b.dataset.act,{[b.dataset.role]:objectId}));
};

// ── 全局搜索(topbar)──
document.addEventListener('DOMContentLoaded',()=>{
  const gs=document.querySelector('#global-search');
  gs.addEventListener('keydown',e=>{
    if(e.key!=='Enter'||!gs.value.trim()) return;
    const state=APP.state, sch=CORE.schemaOf(state), q=gs.value.trim().toLowerCase();
    const t=sch.objectTypes.find(t=>(t.label||'').toLowerCase().includes(q)||t.name.includes(q));
    if(t){ APP.go('objectType',t.id); return; }
    const a=sch.actionTypes.find(a=>(a.label||'').toLowerCase().includes(q)||a.name.includes(q));
    if(a){ APP.go('actionType',a.id); return; }
    for(const t of sch.objectTypes){
      const hit=CORE.searchObjects(state,t.name,gs.value.trim())[0];
      if(hit){ APP.go('objectView',{typeName:t.name,objectId:hit.__id}); return; }
    }
    APP.toast('未找到匹配: '+gs.value,'error');
  });
});
```

- [ ] **Step 4: 运行 smoke 确认通过**(38 passed)

- [ ] **Step 5: Commit**

```bash
git add ontoforge.html smoke.mjs
git commit -m "feat(ui): Object Explorer/Object View(链接管理/动作入口/历史)/全局搜索"
```

---

### Task 14: 分支中心 + 设置页(导入导出/重置/种子切换)

**Files:**
- Modify: `ontoforge.html`(id="appjs" 段追加)
- Modify: `smoke.mjs`(追加 S13 静态断言)

**Interfaces:**
- Consumes: `CORE.createBranch/switchBranch/proposeMerge/mergeProposal/rejectProposal/diffSchemas/diffEmpty/serialize/deserialize`、`SEED`
- Produces:
  - `VIEWS.branches(el,state)` — 三分区:
    - 分支列表(name/baseRev/status,active 显示「切换」;main 常驻)
    - 新建分支 input+按钮(`createBranch`)
    - 提案区:open 提案卡片(branch 名 + diff 摘要渲染:added/removed/changed 分色列表,changed 展示 before/after 字段级 JSON 差异行)+「合并」「拒绝」按钮;历史提案(merged/rejected)只读列出
    - 「从当前分支发起提案」:选分支(非 main)→ `proposeMerge`,错误 toast(如无变更/已有 open)
    - 顶部常驻提示:分支仅隔离 schema,实例数据全局共享
  - `VIEWS.settings(el,state)` — 导出 JSON(下载 state 序列化文件)、导入 JSON(file input → `CORE.deserialize` 校验 → replace)、重置为交通应急种子 / 空白本体(confirm)、清空存档恢复默认
  - 首次启动 onboarding:localStorage 无任何键时,modal 二选一(交通应急种子/空白),选择后 replace —— 修改 Task 9 的 `load()` 返回 `null` 当无存档,boot 时 `state===null` 则弹 onboarding 而非直接 SEED.traffic();**执行时同步修正 Task 9 代码**(smoke 不断言该行为)

- [ ] **Step 1: smoke S13(静态断言,先 FAIL)**

```js
// ── S13 分支中心/设置 静态断言 ──
T('S13.1 视图挂载', ()=>{
  const app=section('appjs');
  for(const v of ['VIEWS.branches','VIEWS.settings','proposeMerge','mergeProposal','rejectProposal','导入','导出','仅隔离 schema','空白本体'])
    ok(app.includes(v),'缺 '+v);
});
```

- [ ] **Step 2: 运行确认 FAIL**

- [ ] **Step 3: appjs 追加实现**

```js
// ── 分支中心 ──
APP.VIEWS.branches=(el,state)=>{
  const E=APP.esc;
  const diffHTML=d=>{
    const sec=(t,c)=>{ const items=[];
      c.added.forEach(x=>items.push(`<div style="color:#16a34a">＋ ${E(x.name)}</div>`));
      c.removed.forEach(x=>items.push(`<div style="color:var(--dan)">－ ${E(x.name)}</div>`));
      c.changed.forEach(x=>items.push(`<div style="color:#d97706">✎ ${E(x.name)}</div>`));
      return items.length?`<div style="margin-bottom:6px"><b>${t}</b>${items.join('')}</div>`:'';
    };
    return sec('对象类型',d.objectTypes)+sec('链接类型',d.linkTypes)+sec('动作类型',d.actionTypes)+sec('共享属性',d.sharedProps)||'<span class="mut">无差异</span>';
  };
  const open=state.proposals.filter(p=>p.status==='open');
  const hist=state.proposals.filter(p=>p.status!=='open');
  el.innerHTML=`<h2>🌿 分支中心</h2>
  <div class="card" style="background:#fffbeb;border-color:#fde68a"><b>说明:</b>分支仅隔离 schema(类型/链接/动作定义),实例数据全局共享 —— 这是原型的诚实简化。</div>
  <div class="grid2">
    <div class="card"><h3>分支</h3>
      ${state.branch.list.map(b=>`<div style="padding:6px 0;border-bottom:1px solid var(--line)">
        🌿 <b>${E(b.name)}</b> <span class="badge">${b.status}</span>
        ${b.name===state.branch.current?'<span class="badge" style="background:#dbeafe">当前</span>'
          :`<a data-sw="${E(b.name)}" style="cursor:pointer;color:var(--pri);font-size:12px">切换</a>`}
      </div>`).join('')}
      <div class="form-row" style="margin-top:12px"><label>新建分支(基于 main)</label>
        <div style="display:flex;gap:8px"><input id="br-name" placeholder="feature-xxx"><button class="btn btn-primary" id="br-new">创建</button></div>
        <div class="form-err" id="br-err"></div></div>
    </div>
    <div class="card"><h3>发起提案(合并回 main)</h3>
      <div style="display:flex;gap:8px">
        <select id="pr-branch">${state.branch.list.filter(b=>b.name!=='main'&&b.status==='active').map(b=>`<option>${E(b.name)}</option>`).join('')}</select>
        <button class="btn btn-primary" id="pr-new">创建提案</button></div>
      <div class="form-err" id="pr-err"></div>
      <div class="mut" style="margin-top:8px">提案会计算该分支与 main 的 schema diff,评审后合并或拒绝。</div>
    </div>
  </div>
  <div class="card"><h3>待评审提案(${open.length})</h3>
    ${open.map(p=>`<div class="card" style="background:#f8fafc">
      <b>${E(p.branch)}</b> → main <span class="mut mono">${p.createdAt.slice(0,10)}</span>
      <div style="margin:10px 0">${diffHTML(p.diff)}</div>
      <button class="btn btn-primary" data-merge="${p.id}">✓ 合并</button>
      <button class="btn btn-danger" data-reject="${p.id}">✕ 拒绝</button></div>`).join('')||'<span class="mut">无待审提案</span>'}
  </div>
  <div class="card"><h3>历史提案</h3>
    ${hist.map(p=>`<div style="padding:4px 0"><span class="badge">${p.status}</span> ${E(p.branch)} <span class="mut mono">${p.createdAt.slice(0,10)}</span></div>`).join('')||'<span class="mut">无</span>'}
  </div>`;
  el.querySelectorAll('[data-sw]').forEach(a=>a.onclick=()=>{
    const r=CORE.switchBranch(state,a.dataset.sw); r.ok?(APP.store.save(),APP.render(),APP.toast('已切换')):APP.toast(r.error,'error');
  });
  el.querySelector('#br-new').onclick=()=>{
    const r=CORE.createBranch(state,el.querySelector('#br-name').value.trim());
    r.ok?(APP.store.save(),APP.render(),APP.toast('分支已创建并切换')):el.querySelector('#br-err').textContent=r.error;
  };
  const prBtn=el.querySelector('#pr-new');
  if(prBtn) prBtn.onclick=()=>{
    const r=CORE.proposeMerge(state,el.querySelector('#pr-branch').value);
    r.ok?(APP.store.save(),APP.render(),APP.toast('提案已创建')):el.querySelector('#pr-err').textContent=r.error;
  };
  el.querySelectorAll('[data-merge]').forEach(b=>b.onclick=()=>{
    const r=CORE.mergeProposal(state,b.dataset.merge);
    r.ok?(APP.store.save(),APP.render(),APP.toast('已合并到 main')):APP.toast(r.error,'error');
  });
  el.querySelectorAll('[data-reject]').forEach(b=>b.onclick=()=>{
    const r=CORE.rejectProposal(state,b.dataset.reject);
    r.ok?(APP.store.save(),APP.render(),APP.toast('已拒绝')):APP.toast(r.error,'error');
  });
};

// ── 设置 / 导入导出 ──
APP.VIEWS.settings=(el,state)=>{
  el.innerHTML=`<h2>⚙️ 数据管理</h2>
  <div class="card"><h3>导出</h3>
    <button class="btn btn-primary" id="st-export">⬇ 导出本体 JSON</button>
    <div class="mut" style="margin-top:6px">含全部 schema、实例、审计、分支与提案,可备份或迁移。</div></div>
  <div class="card"><h3>导入</h3>
    <input type="file" id="st-import" accept=".json,application/json">
    <div class="form-err" id="st-err"></div>
    <div class="mut" style="margin-top:6px">导入前做 schema 校验,非法文件将被拒绝。</div></div>
  <div class="card"><h3>重置</h3>
    <button class="btn" id="st-seed-traffic">🚦 重置为交通应急种子</button>
    <button class="btn" id="st-seed-blank">⬜ 重置为空白本体</button>
    <button class="btn btn-danger" id="st-wipe">🗑 清空存档</button>
    <div class="mut" style="margin-top:6px">重置/清空将覆盖当前全部数据(原存档仍保留在浏览器备份键一次)。</div></div>`;
  el.querySelector('#st-export').onclick=()=>{
    const blob=new Blob([CORE.serialize(state)],{type:'application/json'});
    const a=document.createElement('a'); a.href=URL.createObjectURL(blob);
    a.download=`ontoforge-${state.meta.ontologyName}-${new Date().toISOString().slice(0,10)}.json`; a.click();
    URL.revokeObjectURL(a.href);
  };
  el.querySelector('#st-import').onchange=e=>{
    const f=e.target.files[0]; if(!f) return;
    const rd=new FileReader();
    rd.onload=()=>{ const r=CORE.deserialize(rd.result);
      if(!r.ok){ el.querySelector('#st-err').textContent='导入失败: '+r.error; return; }
      APP.replace(r.state); APP.toast('导入成功'); };
    rd.readAsText(f);
  };
  const confirmReset=(label,fn)=>APP.modal({title:label,bodyHTML:'确定?当前数据将被覆盖。',actions:[
    {label:'取消'},{label:'确定',kind:'danger',onClick:()=>{ fn(); }}]});
  el.querySelector('#st-seed-traffic').onclick=()=>confirmReset('重置为交通应急种子',()=>APP.replace(SEED.traffic()));
  el.querySelector('#st-seed-blank').onclick=()=>confirmReset('重置为空白本体',()=>APP.replace(SEED.blank()));
  el.querySelector('#st-wipe').onclick=()=>confirmReset('清空存档',()=>APP.store.reset());
};

// ── 首次启动 onboarding(替代 Task 9 的直接 traffic 默认)──
// load() 在无任何存档键时返回 null;boot 检测后弹选择。
```

对 Task 9 的两处修正(执行时一并应用):
1. `load()` 末尾 `return SEED.traffic()` 改为 `return null`;
2. `boot()` 改为:
```js
function boot(){
  state=load(); bindChrome();
  if(!state){
    APP.modal({title:'欢迎使用 OntoForge 本体工坊',bodyHTML:'<p>选择初始本体:</p>',actions:[
      {label:'🚦 交通应急示例',kind:'primary',onClick:()=>{ state=SEED.traffic(); save(); render(); }},
      {label:'⬜ 空白本体',onClick:()=>{ state=SEED.blank(); save(); render(); }}]});
    return;
  }
  render();
}
```
注意 onboarding modal 的 actions 内需要赋值局部 `state`(在闭包内可直接赋值,因 `state` 是模块级 let)。

- [ ] **Step 4: 运行 smoke 确认通过**(39 passed)

- [ ] **Step 5: Commit**

```bash
git add ontoforge.html smoke.mjs
git commit -m "feat(ui): 分支中心(提案 diff/评审)/设置页(导入导出/重置)/onboarding"
```

---

### Task 15: verify_ui.mjs 无头 E2E + 终检

**Files:**
- Create: `verify_ui.mjs`
- Modify: 无(除非 E2E 暴露 bug)

**Interfaces:**
- Consumes: 完整 `ontoforge.html`、playwright(`NODE_PATH=$HOME/agentrix-arch-3d-tooling/node_modules`,chromium 于 `~/.cache/ms-playwright`)

- [ ] **Step 1: 写 verify_ui.mjs**

```js
// OntoForge 无头 E2E:file:// 直开,验证核心交互路径
// 用法: NODE_PATH=$HOME/agentrix-arch-3d-tooling/node_modules node verify_ui.mjs
import { chromium } from 'playwright';
const fileUrl='file://'+new URL('./ontoforge.html',import.meta.url).pathname;
let pass=0,fail=0;
const T=(n,ok)=>{ ok?(pass++,console.log('  PASS',n)):(fail++,console.log('  FAIL',n)); };
const browser=await chromium.launch();
const page=await browser.newPage();
const errors=[]; page.on('pageerror',e=>errors.push(e.message));
await page.goto(fileUrl);
// 1 onboarding → 选种子
await page.click('text=交通应急示例');
await page.waitForSelector('#sidebar .side-item');
T('onboarding 进入主界面', await page.locator('#topbar .logo').count()===1);
T('侧栏渲染 5 个对象类型', await page.locator('#side-objectTypes .side-item').count()===5);
T('无 JS 错误', errors.length===0);
// 2 ObjectType 视图
await page.click('#side-objectTypes .side-item >> nth=0');
T('ObjectType 7-section', await page.locator('text=① 元数据').count()===1 && await page.locator('text=⑦ Usage').count()===1);
// 3 Explorer → Object View
await page.click('text=🔍 Object Explorer');
await page.click('#main table tbody tr, #main .table tr[data-obj] >> nth=0').catch(()=>{});
await page.waitForTimeout(400);
T('Object View 打开', await page.locator('text=可用动作').count()===1);
// 4 运行派遣动作(含确认流)
const runBtn=page.locator('[data-act]').first();
if(await runBtn.count()){
  await runBtn.click();
  await page.waitForSelector('.modal');
  await page.click('.modal-actions .btn-primary');
  await page.waitForTimeout(300);
  // 若出现确认框再确认
  const confirm=page.locator('.modal-actions .btn-primary >> text=确认执行');
  if(await confirm.count()) await confirm.click();
  await page.waitForTimeout(300);
  T('动作执行 toast', await page.locator('.toast >> text=执行成功').count()>=1);
} else T('动作执行(无可用动作,跳过)', false);
// 5 持久化:刷新后审计仍在
await page.reload();
await page.click('text=交通应急示例').catch(()=>{});
await page.waitForTimeout(400);
T('刷新后 localStorage 生效', await page.evaluate(()=>!!localStorage.getItem('ontoforge.v1')));
// 6 分支中心建分支+提案
await page.click('text=🌿 分支中心');
await page.fill('#br-name','e2e-test');
await page.click('#br-new');
await page.waitForTimeout(300);
T('建分支并切换', await page.evaluate(()=>JSON.parse(localStorage.getItem('ontoforge.v1')).branch.current==='e2e-test'));
// 7 商标红线
T('页面无 Palantir 字样', (await page.content()).toLowerCase().includes('palantir')===false);
console.log(`\nE2E: ${pass} passed, ${fail} failed`);
await browser.close();
process.exit(fail?1:0);
```

- [ ] **Step 2: 运行 E2E 确认通过**

```bash
cd ~/palantir_re
NODE_PATH=$HOME/agentrix-arch-3d-tooling/node_modules node verify_ui.mjs
```

预期全 PASS;失败则修 UI bug 后重跑(不允许改断言迁就)。

- [ ] **Step 3: 终检清单**

```bash
cd ~/palantir_re
node smoke.mjs                                        # 全部 passed(含 !/palantir/i 红线)
ls -la ontoforge.html smoke.mjs verify_ui.mjs         # 三个交付物
grep -ci palantir ontoforge.html || echo "商标检查 OK" # 应输出 0 或 OK
```

并人工 file:// 打开过一遍:onboarding → 建模 → 跑动作 → 分支提案合并 → 导出导入。

- [ ] **Step 4: Commit**

```bash
git add verify_ui.mjs ontoforge.html smoke.mjs
git commit -m "test(e2e): playwright 无头验证核心路径 + 交付终检"
```

---

## 附:执行备注

1. **Task 9 的两处修正**由 Task 12(modal 栈式)与 Task 14(onboarding/load 返回 null)在执行到对应任务时应用,smoke 断言无需变更。
2. 每个 Task 的 smoke 预期计数为累计值;若中途增删断言以实际输出为准,但必须 0 failed。
3. UI 任务(9–14)以静态断言+最终 E2E 兜底;不逐任务跑浏览器。
4. 提交信息保持中文一句话;red line:任何文件不得出现 `palantir` 字样(smoke S8 已含大小写不敏感检查)。
