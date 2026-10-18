// OntoForge 无头 E2E:file:// 直开,验证核心交互路径(含终检清单的 headless 等价路径)
// 用法: npm run test:e2e(本地装过 playwright);或 NODE_PATH=$HOME/.hermes/hermes-agent/node_modules node verify_ui.mjs
// 注1:ESM bare import 不读 NODE_PATH,故用 createRequire(CJS 解析)加载 playwright
// 注2:解析顺序 —— 本仓库 node_modules(CI/他人机器)→ NODE_PATH → ~/.hermes(本机缓存 chromium-1234 配对的 1.62.x)
import { createRequire } from 'module';
import { readFileSync } from 'fs';
const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch {
  ({ chromium } = require(process.env.HOME + '/.hermes/hermes-agent/node_modules/playwright'));
}

const fileUrl = 'file://' + new URL('./ontoforge.html', import.meta.url).pathname;
let pass = 0, fail = 0;
const T = (n, ok) => { ok ? (pass++, console.log('  PASS', n)) : (fail++, console.log('  FAIL', n)); };
const readState = page => page.evaluate(() => JSON.parse(localStorage.getItem('ontoforge.v1')));

const browser = await chromium.launch();
const page = await browser.newPage();
const errors = []; page.on('pageerror', e => errors.push(e.message));
await page.goto(fileUrl);

// 1 onboarding → 选种子
await page.click('text=交通应急示例');
await page.waitForSelector('#side-objectTypes .side-item');
T('onboarding 进入主界面', await page.locator('#topbar .logo').count() === 1);
T('侧栏渲染 5 个对象类型', await page.locator('#side-objectTypes .side-item').count() === 5);
T('无 JS 错误', errors.length === 0);

// 2 ObjectType 视图
await page.click('#side-objectTypes .side-item >> nth=0');
T('ObjectType 7-section', await page.locator('text=① 元数据').count() === 1 && await page.locator('text=⑦ Usage').count() === 1);

// 3 Explorer → Object View(选「应急队伍」类型,首行 TM-01 待命 —— 派遣动作的路径)
await page.click('text=🔍 Object Explorer');
await page.click('#main [data-type="rescue_team"]');
await page.waitForSelector('#main tr[data-obj]');
await page.click('#main tr[data-obj] >> nth=0');
await page.waitForTimeout(400);
T('Object View 打开', await page.locator('text=可用动作').count() === 1);

// 4 运行派遣动作(含确认流):Object View 的 [data-act] → 执行 → 确认执行 → toast
const runBtn = page.locator('#main [data-act]').first();
if (await runBtn.count()) {
  await runBtn.click();
  await page.waitForSelector('.modal');
  await page.click('.modal-actions .btn-primary');            // 「执行」(此时仅一个 modal)
  await page.waitForTimeout(300);
  // 派遣动作为 requireConfirm:true,弹出确认框(栈式叠加在运行框上)
  const confirm = page.locator('.modal-actions .btn-primary >> text=确认执行');
  if (await confirm.count()) await confirm.click();
  await page.waitForTimeout(600);                              // save() 防抖 300ms,等落盘
  T('动作执行 toast', await page.locator('.toast >> text=执行成功').count() >= 1);
  T('派遣已落盘(TM-01 → 出动)', await page.evaluate(() => {
    const s = JSON.parse(localStorage.getItem('ontoforge.v1'));
    const tm = s.data.objects.find(o => o.props.team_id === 'TM-01');
    return tm && tm.props.status === '出动';
  }));
} else T('动作执行(无可用动作)', false);

// 5 持久化:刷新后审计仍在(有存档时不再出 onboarding,直接渲染)
await page.reload();
await page.waitForSelector('#side-objectTypes .side-item');
T('刷新后 localStorage 生效', await page.evaluate(() => !!localStorage.getItem('ontoforge.v1')));
T('刷新后审计仍在(派遣队伍)', (await readState(page)).audit.some(e => e.actionLabel === '派遣队伍'));

// 6 分支中心建分支(创建后自动切换到新分支)
await page.click('text=🌿 分支中心');
await page.fill('#br-name', 'e2e-test');
await page.click('#br-new');
await page.waitForTimeout(600);                                // save() 防抖 300ms,等落盘
T('建分支并切换', (await readState(page)).branch.current === 'e2e-test');

// 6b 建模:在 e2e-test 分支新建对象类型(顶栏 ＋新建 → 对象类型)
await page.click('#btn-new');
await page.click('[data-new="objectType"]');
await page.waitForSelector('#n-name');
await page.fill('#n-name', 'e2e_probe');
await page.fill('#n-label', 'E2E 探针');
await page.click('.modal-actions .btn-primary');               // 「创建」
await page.waitForTimeout(600);
{
  const s = await readState(page);
  T('建模落盘(新类型进 e2e-test 分支)', s.schemas['e2e-test'].objectTypes.some(t => t.name === 'e2e_probe'));
  T('分支隔离(main 尚无新类型)', !s.schemas.main.objectTypes.some(t => t.name === 'e2e_probe'));
}

// 6c 切回 main → 分支中心发提案 → 合并
await page.selectOption('#branch-switch', 'main');
await page.waitForTimeout(400);
await page.click('text=🌿 分支中心');
await page.click('#pr-new');                                   // #pr-branch 默认选中 e2e-test
await page.waitForTimeout(600);
T('提案已创建(待评审)', (await readState(page)).proposals.some(p => p.branch === 'e2e-test' && p.status === 'open'));
await page.click('[data-merge]');
await page.waitForTimeout(600);
{
  const s = await readState(page);
  T('提案已合并', s.proposals.find(p => p.branch === 'e2e-test')?.status === 'merged');
  T('合并后 main 含新类型', s.schemas.main.objectTypes.some(t => t.name === 'e2e_probe'));
}

// 7 导出 → 导入(设置页)
await page.click('text=⚙️ 数据 / 导入导出');
await page.waitForSelector('#st-export');
const [download] = await Promise.all([
  page.waitForEvent('download'),
  page.click('#st-export'),
]);
T('导出文件名合法', /^ontoforge-.*\.json$/.test(download.suggestedFilename()));
const exported = readFileSync(await download.path(), 'utf8');
{
  let parsed = null; try { parsed = JSON.parse(exported); } catch {}
  T('导出 JSON 可解析且为本体格式', !!parsed && parsed.app === 'ontoforge' && parsed.v === 1 && !!parsed.state);
}
await page.setInputFiles('#st-import', { name: 'ontoforge-e2e.json', mimeType: 'application/json', buffer: Buffer.from(exported) });
await page.waitForTimeout(600);
T('导入成功 toast', await page.locator('.toast >> text=导入成功').count() >= 1);
T('导入后状态仍有效', !!(await readState(page))?.schemas);

// 8 商标红线(检查词拼接以避免字面命中) + 全程无 JS 错误
const tmWord = ['pal', 'antir'].join('');
T('页面无 ' + tmWord + ' 字样', (await page.content()).toLowerCase().includes(tmWord) === false);
T('全程无 JS 错误', errors.length === 0);

console.log(`\nE2E: ${pass} passed, ${fail} failed`);
await browser.close();
process.exit(fail ? 1 : 0);
