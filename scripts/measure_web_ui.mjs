/** Reproducible local UI timing probe; raw observations remain in ignored artifacts. */
import { chromium } from '../web/node_modules/@playwright/test/index.mjs';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const out=resolve(root,'artifacts/web-ui');
await mkdir(out,{recursive:true});
const base=process.env.GC_WEB_URL || 'http://127.0.0.1:8765';
const browser=await chromium.launch({channel:'msedge',headless:true});
const results=[];
try {
  for(const [kind,title] of [['western_chess','国际象棋'],['standard_shogi','将棋'],['generated','生成棋'],['hybrid','混合生成棋']]) {
    const context=await browser.newContext({viewport:{width:1366,height:1000}});
    const page=await context.newPage();
    await page.goto(base);
    if(kind==='western_chess') await page.screenshot({path:resolve(out,'landing.png'),fullPage:true});
    await page.getByRole('button',{name:'开始一局',exact:true}).click();
    await page.getByRole('dialog').getByRole('button',{name:title,exact:true}).click();
    await page.getByRole('button',{name:'开始对局',exact:true}).click();
    await page.getByRole('grid',{name:'棋盘'}).waitFor();
    const id=await page.evaluate(()=>localStorage.getItem('gc-last-game'));
    const endpoint=`${base}/api/games/${id}`;
    let state=await (await page.request.get(endpoint)).json();
    const action=state.actions.find(o=>o.action.from&&!o.action.promotion_target_id).action;
    const coord=p=>String.fromCharCode(97+p[0])+(p[1]+1);
    const from=coord(action.from),to=coord(action.to);
    const selection=[];
    for(let i=0;i<8;i++) {
      await page.evaluate(from=>{
        window.gcSelectionMs=null;
        const el=document.querySelector(`[data-square="${from}"]`);
        el.addEventListener('pointerdown',()=>{
          const start=performance.now();
          const observer=new MutationObserver(()=>{
            if(el.getAttribute('aria-selected')==='true') {
              observer.disconnect();
              requestAnimationFrame(()=>{window.gcSelectionMs=performance.now()-start;});
            }
          });
          observer.observe(el,{attributes:true,attributeFilter:['aria-selected']});
        },{once:true});
      },from);
      await page.locator(`[data-square="${from}"]`).click();
      await page.waitForFunction(()=>window.gcSelectionMs!==null);
      selection.push(await page.evaluate(()=>window.gcSelectionMs));
      await page.locator(`[data-square="${from}"]`).click();
    }
    await page.locator(`[data-square="${from}"]`).click();
    await page.screenshot({path:resolve(out,`${kind}-desktop.png`),fullPage:true});
    await page.locator(`[data-square="${to}"]`).click();
    for(let i=0;i<100;i++) {
      state=await (await page.request.get(endpoint)).json();
      if(state.ai.thinking) break;
      await new Promise(r=>setTimeout(r,5));
    }
    if(!state.ai.thinking) throw new Error('AI did not start');
    const status=[];
    for(let i=0;i<10;i++) {
      const start=performance.now();
      state=await (await page.request.get(endpoint)).json();
      status.push(performance.now()-start);
    }
    const start=performance.now();
    const paused=await page.request.post(`${endpoint}/operations`,{data:{kind:'pause_ai',expected_revision:state.revision,request_id:crypto.randomUUID()}});
    const cancel=performance.now()-start;
    if(!paused.ok()) throw new Error(await paused.text());
    state=await paused.json();
    await page.request.post(`${endpoint}/operations`,{data:{kind:'suspend',expected_revision:state.revision,request_id:crypto.randomUUID()}});
    results.push({kind,selection_ms:selection,status_during_ai_ms:status,cancel_ms:cancel});
    await context.close();
  }
  const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const page=await context.newPage();await page.goto(base);
  await page.getByRole('button',{name:'开始一局',exact:true}).click();
  await page.getByLabel('对局方式').selectOption('pvp');
  await page.getByRole('button',{name:'开始对局',exact:true}).click();
  await page.getByRole('grid',{name:'棋盘'}).waitFor();
  await page.screenshot({path:resolve(out,'mobile.png'),fullPage:true});
  await context.close();
  const percentile=(values,p)=>[...values].sort((a,b)=>a-b)[Math.ceil(values.length*p)-1];
  const selection=results.flatMap(r=>r.selection_ms),status=results.flatMap(r=>r.status_during_ai_ms);
  const report={measured_at:new Date().toISOString(),browser:'Microsoft Edge / headless',viewport:'1366x1000',ai_budget_seconds:1,
    selection_samples:selection.length,selection_p95_ms:percentile(selection,.95),selection_max_ms:Math.max(...selection),
    status_samples:status.length,status_p95_ms:percentile(status,.95),status_max_ms:Math.max(...status),
    cancel_samples:results.length,cancel_max_ms:Math.max(...results.map(r=>r.cancel_ms)),results};
  await writeFile(resolve(out,'timings.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify({...report,results:undefined},null,2));
} finally {await browser.close();}
