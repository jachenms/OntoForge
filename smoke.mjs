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

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
