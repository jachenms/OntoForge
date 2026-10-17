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
