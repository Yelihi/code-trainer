import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright');
const browser=await chromium.launch({headless:true});
const page=await browser.newPage();
let state='running', initial=false, previous=false;
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.route('**/api/**',async route=>{
 const path=new URL(route.request().url()).pathname.slice(4);
 const ok=json=>route.fulfill({json});
 if(path==='/session')return ok({user:{id:'fixture',username:'preview',admin:1},setup_required:false,auth_mode:'preview'});
 if(path==='/health')return ok({ai:true,sandbox:true,languages:[]});
 if(path==='/study/visit')return ok({});
 if(path==='/learning-target')return ok({target:null});
 if(path==='/related-questions')return ok({items:[]});
 if(path==='/interpretations/loading'){
  if(initial){await new Promise(r=>setTimeout(r,1500));}
  return ok({id:'loading',resource_id:'source',revision:1,current_revision:1,source_name:'클로저와 메모리',state,error:'',created_at:'2026-11-20T05:00:00Z',model:'fixture',archived:0,document:previous?{title:'저장된 해석',summary:'이전 해석의 내용은 생성 중에도 유지합니다.',concepts:[],sections:[]}:null});
 }
 if(path.startsWith('/resources/'))return ok({content:'검증용 원문',revision:1});
 return ok({items:[],total:0,page:1,pages:1});
});
const checks=[];
try {
 for(const width of [1440,768,390])for(const next of ['queued','running']){
  state=next;initial=false;previous=false;
  await page.setViewportSize({width,height:900});await page.goto('http://127.0.0.1:5173/interpretations/loading');
  const loading=page.locator('.loading-state');await loading.waitFor();
  assert.equal(await loading.getAttribute('role'),'status');
  assert.equal(await loading.locator('svg').evaluate(el=>getComputedStyle(el).animationName),'loading-state-spin');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.ok((await loading.boundingBox()).height<230);
  await page.waitForTimeout(450);
  await page.screenshot({path:fileURLToPath(new URL(`./interpretation-${next}-${width}.png`,import.meta.url)),fullPage:true});checks.push(`${next}/${width}`);
 }
 previous=true;await page.reload();await page.getByRole('heading',{name:'저장된 해석',exact:true}).waitFor();
 await page.locator('.loading-state-compact').waitFor();await page.getByText('이전 해석의 내용은 생성 중에도 유지합니다.',{exact:true}).waitFor();checks.push('previous document retained');
 await page.emulateMedia({reducedMotion:'reduce'});
 assert.equal(await page.locator('.loading-state-mark svg').evaluate(el=>getComputedStyle(el).animationName),'none');checks.push('reduced motion');
 initial=true;await page.reload();await page.locator('.loading-skeleton').waitFor();assert.equal(await page.locator('[data-slot=skeleton]').first().evaluate(el=>getComputedStyle(el).animationName),'none');
 await page.screenshot({path:fileURLToPath(new URL('./initial-skeleton-390.png',import.meta.url)),fullPage:true});checks.push('initial skeleton');
 initial=false;state='ready';previous=true;await page.reload();await page.getByRole('heading',{name:'저장된 해석',exact:true}).waitFor();assert.equal(await page.locator('.loading-state').count(),0);checks.push('completed state removes loader');
 assert.deepEqual(errors,[]);console.log(JSON.stringify({checks,errors},null,2));
}finally{await browser.close();}
