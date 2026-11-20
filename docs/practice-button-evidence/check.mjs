import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {writeFile} from 'node:fs/promises';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright');
const out=fileURLToPath(new URL('./',import.meta.url));
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({reducedMotion:'reduce'});const errors=[],unknown=[],checks=[];let kind='READ',failSave=false;const saved=[];
page.on('pageerror',e=>errors.push(e.message));
await page.route('**/api/**',route=>{
 const path=new URL(route.request().url()).pathname.slice(4);
 const fixtures={
 '/session':{user:{id:'fixture',username:'preview',admin:1},setup_required:false},
 '/health':{ai:false,sandbox:true,languages:[]},'/learning-target':{target:null},'/related-questions':{items:[]},
 '/technical-references':{items:[],total:0,page:1,pages:1},
 '/sets/test':{id:'test',context_id:'course',title:'검증용 · 실행 결과와 저장',language:'javascript',completed:0,total:1,withdrawn:false,exercises:[{id:'exercise',kind,test_mode:'stdio',title:'검증용 · 출력 예상',description:'코드를 읽고 출력을 확인하세요.',requirements:[],starter:'console.log(42);',public_tests:[{id:'test',stdin:'',expected:'42\n'}],hints_count:0,progress:null,passed:false,attempt_count:0}]}
 };
 if(route.request().method()!=='GET'){
  if(path==='/study/visit')return route.fulfill({json:{}});
  if(path==='/exercises/exercise/progress'){saved.push(route.request().postDataJSON());return new Promise(resolve=>setTimeout(()=>resolve(failSave?route.fulfill({status:503,json:{detail:'저장하지 못했습니다. 다시 시도해주세요.'}}):route.fulfill({json:{revision:1}})),500));}
  throw Error('Unexpected write '+path);
 }
 if(!(path in fixtures)){unknown.push(path);return route.fulfill({status:404,json:{detail:'Missing fixture '+path}});}
 return route.fulfill({json:fixtures[path]});
});
try{
 for(const width of [1440,390])for(kind of ['READ','BUILD']){
  await page.setViewportSize({width,height:1000});await page.goto('http://127.0.0.1:5173/practice/test');await page.locator('.editor-header').first().waitFor();
  if(width===390)await page.locator('.mobile-panel-tabs').getByRole('button',{name:'코드',exact:true}).click();
  const save=page.getByRole('button',{name:'저장',exact:true});
  const saveStyle=await save.evaluate(e=>({width:e.getBoundingClientRect().width,padding:getComputedStyle(e).paddingInlineStart,height:e.getBoundingClientRect().height}));
  assert.ok(saveStyle.width>=64);assert.ok(parseFloat(saveStyle.padding)>=12);assert.ok(saveStyle.height>=44);
  await page.locator('.editor-header').first().screenshot({path:`${out}save-${kind}-${width}.png`});
  if(width===390)await page.locator('.mobile-panel-tabs').getByRole('button',{name:kind==='READ'?'결과':'테스트 · 결과',exact:true}).click();
  const tabs=page.locator('.result-tabs'),result=tabs.getByRole('button',{name:'실행 결과',exact:true});
  const style=await result.evaluate(e=>({radius:getComputedStyle(e).borderRadius,bottom:getComputedStyle(e).borderBottomWidth,padding:getComputedStyle(e).paddingInlineStart,height:e.getBoundingClientRect().height}));
  assert.equal(style.radius,'0px');assert.equal(style.bottom,'2px');assert.ok(parseFloat(style.padding)>=12);assert.ok(style.height>=44);
  const normal=await result.evaluate(e=>getComputedStyle(e).backgroundColor);await result.hover();assert.notEqual(await result.evaluate(e=>getComputedStyle(e).backgroundColor),normal);
  if(kind==='BUILD'){
   const input=tabs.getByRole('button',{name:'직접 실행 입력',exact:true});await input.click();assert.equal(await input.getAttribute('aria-pressed'),'true');assert.equal(await result.getAttribute('aria-pressed'),'false');await result.click();
  }
  await tabs.screenshot({path:`${out}tabs-${kind}-${width}.png`});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  checks.push(`${kind}@${width}`);
 }

 kind='BUILD';
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('http://127.0.0.1:5173/practice/test');await page.locator('.editor-header').first().waitFor();
  if(width===390)await page.locator('.mobile-panel-tabs').getByRole('button',{name:'코드',exact:true}).click();
  await page.locator('.cm-content[contenteditable=true]').first().fill('console.log(43);');
  await page.locator('a[href="/technical-references"]:visible').first().click();
  const dialog=page.getByRole('dialog',{name:'연습 화면을 나갈까요?',exact:true});await dialog.waitFor();
  assert.equal(await dialog.evaluate(e=>e.matches(':modal')),true);
  const bounds=await dialog.boundingBox();assert.ok(Math.abs(bounds.x+bounds.width/2-width/2)<2);assert.ok(Math.abs(bounds.y+bounds.height/2-500)<2);
  const actions=await dialog.locator('.practice-leave-actions button').all();const a=await actions[0].boundingBox(),b=await actions[1].boundingBox(),discard=await dialog.getByRole('button',{name:'저장하지 않고 이동',exact:true}).boundingBox();
  assert.ok(Math.abs(a.width-b.width)<1);assert.ok(discard.y>=a.y+a.height+12);assert.ok(Math.abs(discard.width-(a.width+b.width+12))<1);
  assert.equal(await dialog.getByRole('button',{name:'계속 작성',exact:true}).evaluate(e=>document.activeElement===e),true);
  for(let i=0;i<4;i++){await page.keyboard.press('Tab');assert.equal(await dialog.evaluate(e=>e.contains(document.activeElement)||document.activeElement===document.body),true);}
  await page.screenshot({path:`${out}leave-${width}.png`});
  await page.keyboard.press('Escape');await dialog.waitFor({state:'detached'});assert.ok((await page.locator('.cm-content').first().innerText()).includes('43'));
  await page.locator('a[href="/technical-references"]:visible').first().click();await dialog.getByRole('button',{name:'계속 작성',exact:true}).click();await dialog.waitFor({state:'detached'});
  await page.locator('a[href="/technical-references"]:visible').first().click();failSave=true;await dialog.getByRole('button',{name:'저장 후 이동',exact:true}).click();await dialog.locator('button[aria-busy=true] .button-spinner').waitFor();await page.keyboard.press('Escape');assert.equal(await dialog.isVisible(),true);
  await dialog.getByRole('alert').waitFor();assert.ok(page.url().includes('/practice/test'));
  failSave=false;await dialog.getByRole('button',{name:'저장 후 이동',exact:true}).click();await page.waitForURL('**/technical-references');assert.equal(saved.at(-1).code,'console.log(43);');
  await page.goto('http://127.0.0.1:5173/practice/test');await page.locator('.editor-header').first().waitFor();if(width===390)await page.locator('.mobile-panel-tabs').getByRole('button',{name:'코드',exact:true}).click();await page.locator('.cm-content[contenteditable=true]').first().fill('console.log(44);');
  await page.locator('a[href="/technical-references"]:visible').first().click();const count=saved.length;await dialog.getByRole('button',{name:'저장하지 않고 이동',exact:true}).click();await page.waitForURL('**/technical-references');assert.equal(saved.length,count);
  checks.push(`leave-dialog@${width}`);
 }
 assert.deepEqual(errors,[]);assert.deepEqual(unknown,[]);await writeFile(out+'checks.json',JSON.stringify({checks,errors,unknown},null,2));console.log('Passed practice buttons and native leave dialog layout/focus/Escape/save failure/retry/discard checks.');
}finally{await browser.close();}
