import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright');
const out=fileURLToPath(new URL('./',import.meta.url));
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({reducedMotion:'reduce'});
page.setDefaultTimeout(10000);page.on('dialog',d=>d.accept());
const errors=[],unknown=[],writes=[],checks=[];
page.on('pageerror',e=>errors.push(e.message));
const date='2026-11-18T01:00:00Z';
let id='a'.repeat(32), failed=false, state='ready', empty=false;
let ref={id,title:'검증용 · 상태 경계 검증',user_body:'',revision:1,targets:[{kind:'question',id:'b'.repeat(32),unit_id:'',title:'검증용 · 상태는 어디에 두나요?',href:'/questions/'+'b'.repeat(32),revision:1}],updated_at:date};
let pkg={revision:1,status:'backlog',files:{'SKILL.md':'---\nname: "state-check"\ndescription: "상태 변경을 검증할 때 사용합니다."\n---\n# 상태 경계 검증\n\n## 작업 절차\n\n상태의 소유자를 정하고 변경 경로를 확인합니다.\n\n[참고 자료](references/REFERENCE.md)','references/REFERENCE.md':'# 참고 자료\n\n선택한 질문에서 출발한 검증용 문서입니다.','scripts/check.py':'print(42)\n'},destination:'',job_id:'c'.repeat(32),updated_at:date,stale:false,history:[{revision:1,created_at:date}],sources:[]};
await page.route('**/api/**',async route=>{
 const req=route.request(),url=new URL(req.url()),path=url.pathname.slice(4);
 const ok=json=>route.fulfill({json});
 if(req.method()!=='GET'){
  const body=req.postDataJSON();writes.push({path,body});
  if(path==='/study/visit')return ok({});
  if(path==='/technical-references'){id=body.id;ref={...ref,...body,revision:1,targets:ref.targets};empty=true;return ok(ref);}
  if(path.endsWith('/skills')){state='running';return ok({id:'c'.repeat(32),state});}
  if(path.endsWith('/package')){
   if(failed)return route.fulfill({status:409,json:{detail:'다른 탭에서 수정되었습니다. 초안을 보존합니다.'}});
   pkg={...pkg,...body,revision:pkg.revision+1,history:[{revision:pkg.revision+1,created_at:date},...pkg.history]};return ok(pkg);
  }
  throw Error('Unexpected write '+path);
 }
 if(path==='/session')return ok({user:{id:'fixture',username:'preview',admin:1},setup_required:false,auth_mode:'preview'});
 if(path==='/health')return ok({ai:true,sandbox:true,languages:[]});
 if(path==='/learning-target')return ok({target:null});
 if(path==='/related-questions')return ok({items:[]});
 if(path==='/technical-reference-sources')return ok({items:[{...ref.targets[0],recommended:true,reason:'남겨둔 질문'},{kind:'resource',id:'d'.repeat(32),unit_id:'',title:'검증용 · 입력 검증 자료',href:'/library/'+'d'.repeat(32),revision:1,recommended:false,reason:''}]});
 if(path==='/technical-references')return ok({items:[{...ref,status:pkg.status}],page:1,pages:1,total:1});
 if(path.endsWith('/package'))return ok({package:empty?null:pkg});
 if(path.includes('/package/versions/'))return ok(pkg);
 if(path.startsWith('/technical-references/'))return ok({...ref,jobs:[{id:'c'.repeat(32),kind:'skill',state,error:state==='failed'?'생성 실패. 이전 파일을 유지합니다.':'',created_at:date}]});
 unknown.push(path);return route.fulfill({status:404,json:{detail:'Missing fixture '+path}});
});
try{
 for(const width of [1440,768,390]){
  await page.setViewportSize({width,height:1000});
  for(const [name,path,selector] of [['list','/technical-references','.reference-list'],['create','/technical-references/new','.reference-source-row'],['detail','/technical-references/'+id,'.reference-file-content']]){
   await page.goto('http://127.0.0.1:5173'+path);await page.locator(selector).first().waitFor();
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,name+'@'+width);
   if(width!==768)await page.screenshot({path:out+name+'-'+width+'.png',fullPage:true});
   checks.push(name+'@'+width);
  }
 }
 assert.equal(writes.filter(x=>x.path.endsWith('/skills')).length,0,'Browsing never generates AI');
 await page.getByRole('button',{name:'검토 완료 · active 승인',exact:true}).click();await page.getByRole('button',{name:'외부 반영 완료 · merged',exact:true}).waitFor();
 await page.getByLabel('외부 반영 위치',{exact:true}).fill('https://github.com/example/fs');
 await page.getByRole('button',{name:'외부 반영 완료 · merged',exact:true}).click();await page.getByRole('button',{name:'외부 반영 완료 · merged',exact:true}).waitFor({state:'detached'});
 assert.equal(pkg.status,'merged');assert.equal(pkg.destination,'https://github.com/example/fs');
 await page.getByRole('button',{name:'backlog로 되돌리기',exact:true}).click();await page.getByRole('button',{name:'검토 완료 · active 승인',exact:true}).waitFor();assert.equal(ref.id,id);assert.equal(pkg.status,'backlog');
 await page.getByRole('button',{name:'파일 수정',exact:true}).click();
 await page.getByLabel('추가할 파일 경로',{exact:true}).fill('scripts/new.py');await page.getByRole('button',{name:'파일 추가',exact:true}).click();
 await page.getByLabel('scripts/new.py',{exact:true}).fill('print("draft")');failed=true;
 await page.getByRole('button',{name:'파일 저장',exact:true}).click();await page.getByRole('alert').waitFor();assert.equal(await page.getByLabel('scripts/new.py',{exact:true}).inputValue(),'print("draft")');
 await page.reload();await page.getByRole('button',{name:'파일 수정',exact:true}).click();await page.getByRole('button',{name:'scripts/new.py',exact:true}).click();assert.equal(await page.getByLabel('scripts/new.py',{exact:true}).inputValue(),'print("draft")');
 failed=false;await page.getByRole('button',{name:'파일 저장',exact:true}).click();await page.getByRole('button',{name:'파일 수정',exact:true}).waitFor();assert.equal(pkg.files['scripts/new.py'],'print("draft")');assert.equal(pkg.status,'backlog');
 await page.getByRole('button',{name:'파일 수정',exact:true}).click();await page.getByRole('button',{name:'scripts/new.py',exact:true}).click();
 await page.getByLabel('scripts/new.py',{exact:true}).fill('print("discard")');failed=true;await page.getByRole('button',{name:'파일 저장',exact:true}).click();await page.getByRole('alert').waitFor();
 await page.getByRole('button',{name:'최신 파일 불러오기',exact:true}).click();await page.getByRole('alert').waitFor({state:'detached'});assert.equal(await page.getByLabel('scripts/new.py',{exact:true}).inputValue(),'print("draft")');
 failed=false;await page.getByRole('button',{name:'읽기로',exact:true}).click();
 await page.getByRole('button',{name:'scripts/new.py',exact:true}).first().click();
 assert.ok(await page.getByText('생성된 스크립트입니다. 여기에서는 실행하지 않습니다.',{exact:true}).isVisible());
 await page.getByText('수정 '+pkg.revision+' ·',{exact:false}).first().click();await page.locator('.reference-history-content').waitFor();
 await page.screenshot({path:out+'edited-390.png',fullPage:true});
 state='failed';await page.reload();await page.getByRole('alert').waitFor();assert.ok(await page.getByRole('button',{name:'파일 수정',exact:true}).isVisible());
 await page.goto('http://127.0.0.1:5173/technical-references/new');await page.getByRole('button',{name:'추천만 보기',exact:true}).click();assert.equal(await page.locator('.reference-source-row').count(),1);
 await page.locator('.reference-source-row').click();await page.getByLabel('레퍼런스 제목',{exact:true}).fill('검증용 · 새 Skill');
 await page.getByRole('button',{name:'AI로 Skill 만들기',exact:true}).click();await page.getByRole('button',{name:'Skill 생성 중',exact:true}).waitFor();assert.equal(writes.filter(x=>x.path.endsWith('/skills')).length,1);
 assert.ok(await page.locator('button[aria-busy=true] .button-spinner').isVisible());
 empty=false;state='ready';await page.getByRole('button',{name:'파일 수정',exact:true}).waitFor();
 assert.deepEqual(errors,[]);assert.deepEqual(unknown,[]);
 await writeFile(out+'checks.json',JSON.stringify({checks,interactions:['explicit generation only','backlog-active-merged-backlog keeps ID','destination','file add/edit','conflict retains draft','reload recovers draft','explicit conflict recovery loads latest files','script stays text','history read','failure keeps files','recommendation selection','job polling and spinner'],errors,unknown},null,2));
 console.log('Passed '+checks.length+' responsive checks and lifecycle/editor/job interactions.');
}catch(e){await page.screenshot({path:out+'failure.png',fullPage:true});console.log(JSON.stringify({errors,unknown,writePaths:writes.map(x=>x.path),url:page.url(),alerts:await page.getByRole('alert').allTextContents()}));throw e;}finally{await browser.close();}
