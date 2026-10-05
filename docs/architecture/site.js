/* Public documentation only. Source content is escaped before insertion. */
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const $ = id => document.getElementById(id);
let catalog, journeys, functions;
const link = id => `#function=${encodeURIComponent(id)}`;
const pill = id => {
  const [path, name] = id.split('::'), module = path.split('/').at(-1).replace(/\.[^.]+$/, '');
  return `<a class="pill" href="${link(id)}" title="${esc(id)}">${esc(module + '.' + name)}()</a>`;
};
function symbol(r) {
  const resolved = r.calls.filter(c => c.target);
  const rest = r.calls.filter(c => !c.target);
  const callers = functions.filter(f => f.calls.some(c => c.target === r.id));
  const events = journeys.filter(j => j.steps.some(s => s.functions.includes(r.id)));
  return `<details class="symbol" id="symbol-${esc(r.id)}"><summary>${esc(r.name)}()<span class="count">L${r.line} · ${r.calls.length}개 참조</span></summary><div class="symbol-body">
    <a href="${catalog.repository}/blob/${catalog.revision}/${r.path}#L${r.line}-L${r.end}" target="_blank" rel="noopener">구현 코드 L${r.line}–${r.end} ↗</a>
    ${events.length ? `<h4>연결된 사용자·운영 흐름</h4><div class="links">${events.map(j => `<a class="pill" href="#event=${j.id}">${esc(j.title)}</a>`).join('')}</div>` : ''}
    <h4>등록된 이벤트 · HTTP 요청 · 백그라운드 작업</h4>${r.events.length ? `<ul>${r.events.map(e => `<li><code>${esc(e)}</code></li>`).join('')}</ul>` : '<p class="footnote">이 함수에서 직접 등록한 이벤트가 없습니다. 아래 호출 관계를 확인하세요.</p>'}
    <h4>호출하는 저장소 함수</h4><div class="links">${resolved.map(c => pill(c.target)).join('') || '<span class="footnote">직접 해석된 저장소 함수 참조 없음</span>'}</div>
    <h4>이 함수를 참조하는 함수</h4><div class="links">${callers.map(c => pill(c.id)).join('') || '<span class="footnote">프레임워크·이벤트·동적 진입일 수 있습니다.</span>'}</div>
    ${rest.length ? `<details><summary class="footnote">외부·객체 메서드·미해석 참조 ${rest.length}개</summary><p class="unresolved">${rest.map(c => esc(c.name)).join(' · ')}</p></details>` : ''}
  </div></details>`;
}
function tree() {
  const term = $('search').value.trim().toLowerCase(), area = $('area').value;
  const matches = functions.filter(r => r.path.startsWith(area) && [r.path,r.name,...r.events,...r.calls.map(c=>c.name)].join(' ').toLowerCase().includes(term));
  const groups = Map.groupBy(matches, r => r.path);
  $('result-count').textContent = `${groups.size}개 파일 · ${matches.length}개 함수`;
  $('tree').innerHTML = [...groups].map(([path, records]) => `<details class="module" ${term ? 'open' : ''}><summary>${esc(path)}<span class="count">${records.length}개 함수</span></summary><div class="symbols">${records.map(symbol).join('')}</div></details>`).join('') || '<p class="empty">검색 결과가 없습니다. 다른 함수 이름이나 경로로 검색해보세요.</p>';
}
function event(id) {
  const selected = journeys.find(j=>j.id===id) || journeys[0];
  $('event-menu').innerHTML = journeys.map((j,i)=>`<a href="#event=${j.id}" aria-current="${j.id===selected.id}">${String(i+1).padStart(2,'0')} · ${esc(j.title)}</a>`).join('');
  $('event-detail').innerHTML = `<p class="trigger">${esc(selected.trigger)}</p><h2>${esc(selected.title)}</h2><p class="footnote">${esc(selected.note)}</p><ol class="flow">${selected.steps.map((s,i)=>`<li><span class="step-number">${i+1}</span><h3>${esc(s.title)}</h3><p>${esc(s.detail)}</p><div class="links">${s.functions.map(pill).join('')}</div></li>`).join('')}</ol>`;
}
function route() {
  const hash = location.hash.slice(1), isFunction=hash.startsWith('function='), isArea=hash.startsWith('area=');
  const tab = isFunction || isArea || hash==='functions' ? 'functions' : hash==='events' || hash.startsWith('event=') ? 'events' : 'overview';
  for(const id of ['overview','events','functions']) $(id).hidden=id!==tab;
  document.querySelectorAll('[data-tab]').forEach(a=>{if(a.dataset.tab===tab)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  if(tab==='events') event(hash.split('=')[1]);
  if(tab==='functions') {
    if(isArea){$('search').value='';$('area').value=decodeURIComponent(hash.slice(5));}
    if(isFunction){$('search').value='';$('area').value='';}
    tree();
    if(isFunction){let id;try{id=decodeURIComponent(hash.slice(9));}catch{return;}
      const el=$('symbol-'+id);if(el){el.open=true;el.closest('.module').open=true;el.scrollIntoView({block:'start'});}else $('result-count').textContent='해당 함수가 현재 소스에 없습니다.';}
  }
}
async function start(){
  try{
    [catalog,journeys]=await Promise.all(['catalog.json','journeys.json'].map(async p=>{const r=await fetch(p);if(!r.ok)throw Error(`${p}: ${r.status}`);return r.json();}));
    functions=catalog.functions;
    $('revision').innerHTML=`${catalog.files}개 파일 · ${functions.length}개 함수 · 소스 <a href="${catalog.repository}/tree/${catalog.revision}">${catalog.revision.slice(0,7)}</a>`;
    $('catalog-note').textContent=catalog.scope+' '+catalog.limitation;
    $('layers').innerHTML=[['frontend/','화면과 사용자 이벤트','React 화면 · API 클라이언트'],['backend/','학습·저장·실행','FastAPI · SQLite · AI · 브로커'],['deploy/','배포와 운영','Worker · Mac 감시 · release'],['scripts/','검증과 백업','실행 환경 검사 · SQLite 사본']].map(([area,title,sub])=>`<a class="layer" href="#area=${encodeURIComponent(area)}"><strong>${title} ↗</strong><span>${sub}</span></a>`).join('');
    $('search').addEventListener('input',tree);$('area').addEventListener('change',tree);window.addEventListener('hashchange',route);route();
  }catch(e){$('revision').textContent='문서 데이터를 읽지 못했습니다. 새로고침해주세요.';console.error(e);}
}
start();
