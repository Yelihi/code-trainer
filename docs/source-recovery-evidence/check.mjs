import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {writeFile} from 'node:fs/promises';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright');
const out=fileURLToPath(new URL('./',import.meta.url)),browser=await chromium.launch({headless:true}),page=await browser.newPage({reducedMotion:'reduce'});
const errors=[],unknown=[],writes=[],checks=[];let mode='failed',failPaste=false;
page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());page.setDefaultTimeout(10000);
const date='2026-11-20T00:00:00Z',body='# 검증용 원문\n\n수집한 원문은 해당 버전과 URL을 보존합니다.\n\n```js\nconsole.log(42);\n```';
let resource={id:'resource',name:'검증용 · URL에서 원문 가져오기',kind:'url',note_id:null,url:'https://example.com/post',revision:2,content:body,state:'ready',error:'',updated_at:date,archived:0,versions:[{revision:2,created_at:date},{revision:1,created_at:date}],feed_pending:false};
const value=()=>({...resource,...(mode==='failed'?{revision:0,content:null,state:'failed',error:'원문 서버가 접근을 제한했습니다. 본문을 직접 입력할 수 있습니다.',versions:[],feed_pending:true}:mode==='fetching'?{revision:0,content:null,state:'fetching',versions:[],feed_pending:true}:mode==='failed-old'?{state:'failed',error:'원문 서버가 HTTP 503으로 응답했습니다.'}:{})});
await page.route('**/api/**',async route=>{
 const req=route.request(),path=new URL(req.url()).pathname.slice(4);const ok=json=>route.fulfill({json});
 if(req.method()!=='GET'){
  writes.push({path,data:req.postDataJSON()});if(path==='/study/visit')return ok({});
  if(path==='/resources/resource/content'){
   if(failPaste)return route.fulfill({status:503,json:{detail:'저장하지 못했습니다. 다시 시도해주세요.'}});
   resource={...resource,content:req.postDataJSON().content};mode='ready';return ok(value());
  }
  if(path==='/resources'){mode='ready';return ok(value());}
  throw Error('Unexpected mutation '+path);
 }
 const fixtures={'/session':{user:{id:'fixture',username:'preview',admin:1},setup_required:false,auth_mode:'preview'},'/health':{sandbox:true,ai:false,languages:[]},'/learning-target':{target:null},'/related-questions':{items:[]},'/resources/resource':value(),'/resources':{items:[{...value(),excerpt:null},{...resource,id:'note',kind:'note',name:'검증용 · 직접 작성한 노트',excerpt:'직접 기록한 내용입니다.'}],total:2,page:1,pages:1},'/resources/resource/versions/1':{revision:1,name:resource.name,content:'이전 버전의 본문입니다.',url:'https://example.com/old'}};
 if(!(path in fixtures)){unknown.push(path);return route.fulfill({status:404,json:{detail:'Missing '+path}});}
 return ok(fixtures[path]);
});
try{
 for(const width of [1440,768,390]){
  await page.setViewportSize({width,height:1000});
  for(mode of ['failed','fetching','ready','failed-old']){
   await page.goto('http://127.0.0.1:5173/library/resource');await page.getByRole('heading',{name:resource.name,exact:true}).waitFor();
   if(mode==='failed'||mode==='fetching'){await page.locator('.resource-recovery').waitFor();assert.equal(await page.locator('.reading-workspace').count(),0);}
   else await page.locator('.reading-workspace').waitFor();
   assert.ok(await page.locator('[data-slot=badge]').count());assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   if(width!==768)await page.screenshot({path:`${out}${mode}-${width}.png`,fullPage:true});checks.push(`${mode}@${width}`);
  }
  await page.goto('http://127.0.0.1:5173/library');await page.locator('.reference-list-item').first().waitFor();
  const list=await page.locator('.library-page .reference-list').boundingBox(),row=page.locator('.reference-list-item').first(),box=await row.boundingBox();assert.ok(Math.abs(list.width-box.width)<1);assert.ok(Math.abs(list.x-box.x)<1);
  const padding=await row.evaluate(e=>[getComputedStyle(e).paddingTop,getComputedStyle(e).paddingRight,getComputedStyle(e).paddingBottom,getComputedStyle(e).paddingLeft].map(parseFloat));assert.ok(padding.every(x=>x>=20));
  const normal=await row.evaluate(e=>getComputedStyle(e).backgroundColor);await row.hover({position:{x:4,y:24}});assert.notEqual(await row.evaluate(e=>getComputedStyle(e).backgroundColor),normal);
  assert.ok(await row.locator('[data-slot=badge]').count());if(width!==768)await page.screenshot({path:`${out}list-hover-${width}.png`,fullPage:true});checks.push(`list-hover@${width}`);
 }
 mode='ready';await page.goto('http://127.0.0.1:5173/library/resource');await page.getByLabel('본문 버전',{exact:true}).selectOption('1');await page.getByText('당시 원문 URL · https://example.com/old',{exact:true}).waitFor();assert.ok((await page.locator('#resource-body').innerText()).includes('이전 버전'));
 await page.getByLabel('본문 버전',{exact:true}).selectOption('2');await page.getByRole('heading',{name:'검증용 원문',exact:true}).waitFor();
 mode='failed';await page.goto('http://127.0.0.1:5173/library/resource');await page.getByRole('button',{name:'본문 직접 입력',exact:true}).click();const input=page.getByLabel('본문',{exact:true});await input.fill('직접 붙여넣는 검증용 원문입니다.');failPaste=true;await page.getByRole('button',{name:'본문 저장',exact:true}).click();await page.locator('.resource-paste').getByRole('alert').waitFor();assert.equal(await input.inputValue(),'직접 붙여넣는 검증용 원문입니다.');
 await page.reload();await page.getByRole('button',{name:'본문 직접 입력',exact:true}).click();assert.equal(await input.inputValue(),'직접 붙여넣는 검증용 원문입니다.');failPaste=false;await page.getByRole('button',{name:'본문 저장',exact:true}).click();await page.locator('#resource-body').waitFor();assert.equal(resource.url,'https://example.com/post');assert.ok(writes.some(x=>x.path==='/resources/resource/content'));
 mode='failed';await page.goto('http://127.0.0.1:5173/library/resource');await page.getByRole('button',{name:'다시 가져오기',exact:true}).click();await page.locator('#resource-body').waitFor();
 assert.deepEqual(errors,[]);assert.deepEqual(unknown,[]);await writeFile(out+'checks.json',JSON.stringify({checks,interactions:['version selection preserves source URL','whole row hover with inner padding','status badges','manual paste keeps URL and identity','paste failure preserves draft','reload draft recovery','retry fetch'],errors,unknown},null,2));console.log('Passed 15 resource layouts/hover checks and source recovery/version/draft interactions.');
}finally{await browser.close();}
