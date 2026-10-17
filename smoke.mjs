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

// ── S2 链接类型/链接实例 ──
function _twoTypes(){ const s=CORE.createEmptyState();
  const a=CORE.addObjectType(s,{name:'team'}).id, b=CORE.addObjectType(s,{name:'incident'}).id;
  s.data.objects.push({__id:'t1',__type:'team',props:{}},{__id:'t2',__type:'team',props:{}},{__id:'i1',__type:'incident',props:{}});
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

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
