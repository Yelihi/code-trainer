import { LoadingState } from './LoadingState';
import { useEffect, useRef, useState } from 'react';
import { Link, useBlocker, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Check, FileCode2, FileText, Plus, ArrowRight, History, FolderOpen } from 'lucide-react';
import { api, errorMessage, timestamp } from './api';
import { ErrorNotice, useApp, useResource } from './App';
import { Badge } from './components/ui/badge';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Textarea } from './components/ui/textarea';
import { Label } from './components/ui/label';
import { EmptyState, PageHeading } from './WorkspaceUI';
import { Markdown } from './Markdown';
import { LoadingSkeleton } from './LoadingSkeleton';
import { targetInput, type LearningTarget } from './LearningTargets';
import { libraryPage } from './libraryTypes';
import { TechnicalReferenceRoute as LegacyReferenceRoute } from './TechnicalReferences';
import './referenceWorkspace.css';

type Status = 'backlog' | 'active' | 'merged';
type Package = { revision: number; status: Status; files: Record<string,string>; destination: string; job_id: string; updated_at: string; stale: boolean; history: {revision:number;created_at:string}[]; sources: (LearningTarget & {key:string;basis:string})[] };
type Ref = { id:string;title:string;user_body:string;revision:number;status:Status|null;updated_at:string;targets:LearningTarget[];jobs:{id:string;kind:string;state:string;error:string;created_at:string}[] };
const statuses: Status[] = ['backlog','active','merged'];
const statusLabels = {backlog:'검토 대기',active:'승인됨',merged:'외부 반영'};
const sourceNames: Record<string,string> = {resource:'원자료',question:'질문',course:'자료 기반 실습',exercise:'실습 문제',foundation:'사전 생성 문제',interpretation:'해석 자료',review:'복습',material_review:'자료 복습'};
const badge = (status:Status|null) => <Badge variant="secondary" className={'reference-status '+(status ?? '')}>{status ? status+' · '+statusLabels[status] : 'Skill 미생성'}</Badge>;

export function TechnicalReferences() {
  const [params,setParams]=useSearchParams();
  const query=(params.get('q')??'').slice(0,160), status=statuses.includes(params.get('status') as Status)?params.get('status')!:'', page=libraryPage(params.get('page'));
  const {data,error,reload}=useResource<{items:Ref[];page:number;pages:number;total:number}>(`/technical-references?q=${encodeURIComponent(query)}&status=${status}&page=${page}`);
  return <main className="page reference-workspace"><PageHeading title="레퍼런스" description="학습한 내용을 AI가 사용할 Skill로 만드세요." actions={<Link className="button primary" to="/technical-references/new"><Plus size={18} aria-hidden="true"/>학습에서 만들기</Link>}/>
    <nav className="reference-filters" aria-label="레퍼런스 상태">{['',...statuses].map(s=><Button key={s} aria-pressed={status===s} onClick={()=>setParams({q:query,status:s})}>{s ? s : '전체'}</Button>)}</nav>
    <form className="reference-search" role="search" key={query} onSubmit={e=>{e.preventDefault();setParams({q:String(new FormData(e.currentTarget).get('q')??''),status});}}><Label className="sr-only" htmlFor="skill-search">레퍼런스 검색</Label><Input id="skill-search" name="q" type="search" defaultValue={query} maxLength={160} placeholder="레퍼런스 찾기"/><Button>검색</Button></form>
    <ErrorNotice error={error}/>{error&&<Button onClick={reload}>다시 불러오기</Button>}{!data&&!error&&<LoadingSkeleton layout="list" label="레퍼런스를 불러오는 중…"/>}
    {data?.items.length ? <div className="reference-list">{data.items.map(item=><Link className="reference-list-row" key={item.id} to={'/technical-references/'+item.id}><FileText size={22} aria-hidden="true"/><div><h2>{item.title}</h2><div className="reference-row-meta">{badge(item.status)}<time>{timestamp(item.updated_at)}</time></div></div><ArrowRight size={18} aria-hidden="true"/></Link>)}</div> : data&&!error&&<EmptyState icon={FolderOpen} title={status?'이 상태의 레퍼런스가 없습니다':'학습 기록을 Skill로 연결하세요'} action={<Link className="button" to="/technical-references/new">학습 선택하기</Link>}/>}
    {data&&data.pages>1&&<nav className="pagination" aria-label="레퍼런스 페이지"><Button disabled={data.page<=1} onClick={()=>setParams({q:query,status,page:String(data.page-1)})}>이전</Button><span>{data.page} / {data.pages}</span><Button disabled={data.page>=data.pages} onClick={()=>setParams({q:query,status,page:String(data.page+1)})}>다음</Button></nav>}
  </main>;
}

export function TechnicalReferenceRoute() {
  const {id}=useParams(); const location=useLocation();
  if(location.pathname.endsWith('/legacy')) return <LegacyReferenceRoute/>;
  return id ? <ReferenceDetail key={id} id={id}/> : <CreateReference/>;
}
function CreateReference() {
  const navigate=useNavigate(), [query,setQuery]=useState(''),[recommended,setRecommended]=useState(false),[selected,setSelected]=useState<LearningTarget[]>([]),[title,setTitle]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const {data,error:loadError,reload}=useResource<{items:(LearningTarget&{recommended:boolean;reason:string})[]}>('/technical-reference-sources?q='+encodeURIComponent(query));
  const identity=useRef({id:crypto.randomUUID().replaceAll('-',''),request_id:crypto.randomUUID()});
  const dirty=!!title.trim()||selected.length>0;
  const blocker=useBlocker(dirty&&!busy);
  useEffect(()=>{if(blocker.state==='blocked'){if(window.confirm('선택한 학습과 제목을 버리고 이동할까요?'))blocker.proceed();else blocker.reset();}},[blocker]);
  useEffect(()=>{if(!dirty||busy)return;const handler=(event:BeforeUnloadEvent)=>event.preventDefault();window.addEventListener('beforeunload',handler);return()=>window.removeEventListener('beforeunload',handler);},[dirty,busy]);
  async function create() {
    setBusy(true);setError('');
    try {
      const ref=await api<Ref>('/technical-references','POST',{...identity.current,revision:0,title:title.trim(),user_body:'',targets:selected.map(targetInput)});
      let generationError='';
      try {await api(`/technical-references/${ref.id}/skills`,'POST',{revision:ref.revision,request_id:crypto.randomUUID()});} catch(cause) {generationError=errorMessage(cause);}
      await navigate('/technical-references/'+ref.id,{state:{generationError}});
    } catch(cause) {setError(errorMessage(cause));} finally {setBusy(false);}
  }
  const items=data?.items.filter(item=>!recommended||item.recommended);
  return <main className="page reference-workspace"><Link className="text-link" to="/technical-references">레퍼런스</Link><PageHeading title="학습에서 레퍼런스 만들기" description="질문·자료·실습 기록을 골라 하나의 Skill로 정리하세요."/>
    <div className="reference-create-layout"><section className="reference-source-panel"><div className="reference-source-toolbar"><Label className="sr-only" htmlFor="source-search">학습 기록 검색</Label><Input id="source-search" type="search" value={query} maxLength={160} placeholder="학습 기록 검색" onChange={e=>setQuery(e.target.value)}/><Button aria-pressed={recommended} onClick={()=>setRecommended(!recommended)}>추천만 보기</Button></div>
    <ErrorNotice error={loadError}/>{loadError&&<Button onClick={reload}>다시 불러오기</Button>}{!data&&!loadError&&<LoadingSkeleton layout="list" label="학습 기록을 불러오는 중…"/>}
    <div className="reference-source-list">{items?.map(item=>{const picked=selected.some(s=>s.kind===item.kind&&s.id===item.id&&s.unit_id===item.unit_id);return <button type="button" className="reference-source-row" aria-pressed={picked} disabled={busy||(!picked&&selected.length>=10)} key={item.kind+item.id+item.unit_id} onClick={()=>setSelected(picked?selected.filter(s=>!(s.kind===item.kind&&s.id===item.id&&s.unit_id===item.unit_id)):[...selected,item])}><span className="reference-source-check">{picked&&<Check size={16} aria-hidden="true"/>}</span><span><small>{sourceNames[item.kind]??'학습'}{item.reason?' · '+item.reason:''}</small><strong>{item.title}</strong></span></button>;})}</div>
    {data&&!items?.length&&<EmptyState icon={FileText} title={recommended?'추천할 기록이 없습니다':'선택할 학습 기록이 없습니다'} action={<Link className="button" to="/library">원자료 열기</Link>}/>}</section>
    <form className="reference-selection" onSubmit={e=>{e.preventDefault();void create();}}><h2>선택한 학습 <span>{selected.length} / 10</span></h2>{selected.length?<ul>{selected.map(item=><li key={item.kind+item.id+item.unit_id}><Link className="text-link" to={item.href} target="_blank" rel="noreferrer">{item.title}</Link><Button type="button" size="sm" disabled={busy} onClick={()=>setSelected(selected.filter(s=>s!==item))}>해제</Button></li>)}</ul>:<p className="muted">학습 목록에서 근거를 선택하세요.</p>}
    <Label htmlFor="skill-title">레퍼런스 제목</Label><Input id="skill-title" value={title} required maxLength={200} disabled={busy} onChange={e=>setTitle(e.target.value)} placeholder="예: 상태 경계 검증"/>
    <ErrorNotice error={error}/><Button className="primary" loading={busy} disabled={busy||!selected.length||!title.trim()}>AI로 Skill 만들기</Button><small className="muted">요청 시 AI를 사용합니다. 생성 결과는 backlog에 저장됩니다.</small></form></div></main>;
}
function ReferenceDetail({id}:{id:string}) {
  const {data:ref,error,reload}=useResource<Ref>('/technical-references/'+id,{preserveData:true});
  const {data:packageData,error:packageError,loading:packageLoading,reload:reloadPackage,update}=useResource<{package:Package|null}>('/technical-references/'+id+'/package',{preserveData:true});
  const pkg=packageData?.package;
  const location=useLocation();
  const [actionError,setError]=useState(String(location.state?.generationError??'')),[busy,setBusy]=useState(false),[editing,setEditing]=useState(false),[destination,setDestination]=useState<string|null>(null);
  const request=useRef({revision:0,id:''});
  const jobs=ref?.jobs.filter(j=>j.kind==='skill')??[], pending=jobs.some(j=>j.state==='queued'||j.state==='running');
  useEffect(()=>{if(!pending)return;const timer=setInterval(()=>{reload();reloadPackage();},2000);return()=>clearInterval(timer);},[pending,reload,reloadPackage]);
  async function generate() {if(!ref)return;setBusy(true);setError('');if(request.current.revision!==ref.revision)request.current={revision:ref.revision,id:crypto.randomUUID()};try{await api(`/technical-references/${id}/skills`,'POST',{revision:ref.revision,request_id:request.current.id,refresh:!!pkg});request.current.revision=0;reload();reloadPackage();}catch(cause){setError(errorMessage(cause));}finally{setBusy(false);}}
  async function changeStatus(status:Status) {if(!pkg)return;setBusy(true);setError('');try{const result=await api<Package>(`/technical-references/${id}/package`,'PUT',{revision:pkg.revision,files:pkg.files,status,destination:destination??pkg.destination});update({package:result});setDestination(null);}catch(cause){setError(errorMessage(cause));}finally{setBusy(false);}}
  async function apply(jobId:string) {if(!window.confirm('현재 파일을 이 생성 결과로 바꿀까요? 현재 내용은 변경 이력에 남습니다.'))return;setBusy(true);setError('');try{const result=await api<Package>(`/technical-references/${id}/package/from-job`,'POST',{revision:pkg?.revision??0,job_id:jobId});update({package:result});}catch(cause){setError(errorMessage(cause));}finally{setBusy(false);}}
  return <main className="page reference-workspace"><Link className="text-link" to="/technical-references">레퍼런스</Link><ErrorNotice error={error||packageError}/>{(error||packageError)&&<Button onClick={()=>{reload();reloadPackage();}}>다시 불러오기</Button>}{!ref&&!error&&<LoadingSkeleton layout="article" label="레퍼런스를 불러오는 중…"/>}
  {ref&&<><PageHeading title={ref.title} meta={badge(pkg?.status??null)} actions={<><Link className="button" to={'/technical-references/'+id+'/legacy'}>근거·이전 설명</Link><Button loading={busy||pending} disabled={busy||pending||editing} onClick={()=>void generate()}>{pending?'Skill 생성 중':'Skill '+(pkg?'다시 생성':'생성')}</Button></>}/><ErrorNotice error={actionError}/>
  {pending&&<LoadingState compact={!!pkg} status="Skill 생성 중" title="선택한 학습을 Skill로 정리하고 있어요" description="완료된 파일은 이곳에서 검토할 수 있어요." />}
  {!pkg&&!packageLoading&&!packageError&&!pending&&<EmptyState icon={FileCode2} title="아직 생성된 Skill이 없습니다" action={<Button className="primary" loading={busy} disabled={busy} onClick={()=>void generate()}>Skill 생성하기</Button>}/>}
  {pkg&&<>{pkg.stale&&<p className="notice" role="status">생성에 사용한 근거가 변경됐습니다. 현재 파일을 검토해주세요.</p>}
  <div className="reference-detail-layout"><section className="reference-package-panel">{editing?<PackageEditor key={id} id={id} pkg={pkg} onRefresh={value=>update({package:value})} onSaved={value=>{update({package:value});setEditing(false);}} onCancel={()=>setEditing(false)}/>:<><div className="reference-file-toolbar"><h2>Skill 파일</h2><Button disabled={busy||pending} onClick={()=>setEditing(true)}>파일 수정</Button></div><PackageFiles files={pkg.files}/></>}</section>
  <aside className="reference-management"><h2>상태 관리</h2><p className="reference-current-state">{badge(pkg.status)}</p><div className="reference-status-actions">{pkg.status!=='backlog'&&<Button disabled={busy||editing||pending} onClick={()=>void changeStatus('backlog')}>backlog로 되돌리기</Button>}{pkg.status==='backlog'&&<Button className="primary" disabled={busy||editing||pending} onClick={()=>void changeStatus('active')}>검토 완료 · active 승인</Button>}</div>
  <Label htmlFor="reference-destination">외부 반영 위치</Label><Input id="reference-destination" value={destination??pkg.destination} maxLength={1000} placeholder="저장소 URL 또는 경로" disabled={busy||editing} onChange={e=>setDestination(e.target.value)}/>
  {pkg.status==='active'&&<Button disabled={busy||editing||pending} onClick={()=>void changeStatus('merged')}>외부 반영 완료 · merged</Button>}{destination!==null&&<Button disabled={busy||editing} onClick={()=>void changeStatus(pkg.status)}>위치 저장</Button>}
  <small className="muted">외부 전송 후 직접 표시하세요. ZIP 다운로드로 상태가 바뀌지 않습니다.</small><a className="button" href={`/api/technical-references/${id}/package/download`} download>Skill ZIP 다운로드</a>
  <div className="reference-management-section"><h3>연결된 학습</h3>{ref.targets.map(t=><Link className="text-link" key={t.kind+t.id+t.unit_id} to={t.href}>{t.title}</Link>)}</div>
  <div className="reference-management-section"><h3><History size={16} aria-hidden="true"/>변경 이력</h3>{pkg.history.map(v=><PackageHistory key={v.revision} id={id} revision={v.revision} createdAt={v.created_at}/>)}</div></aside></div></>}
  <section className="reference-jobs"><h2>생성 작업</h2>{jobs.map(job=><div className="reference-job-row" key={job.id}><div><Badge variant="secondary">{{queued:'생성 대기',running:'생성 중',ready:'생성 완료',failed:'생성 실패',interrupted:'중단됨'}[job.state]??job.state}</Badge><small>{timestamp(job.created_at)}</small>{job.error&&<p role="alert">{job.error}</p>}</div>{job.state==='ready'&&pkg?.job_id!==job.id&&<div className="reference-unapplied-job"><GeneratedResult id={id} jobId={job.id}/><Button disabled={busy||editing||pending} onClick={()=>void apply(job.id)}>이 결과 적용</Button></div>}</div>)}{!jobs.length&&<p className="muted">생성 작업이 없습니다.</p>}</section></>}
  </main>;
}
function PackageFiles({files}:{files:Record<string,string>}) {
  const [selected,setSelected]=useState('SKILL.md');const path=selected in files?selected:Object.keys(files)[0];
  const header=path==='SKILL.md'?/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(files[path]):null;
  return <><div className="reference-file-tabs" role="group" aria-label="패키지 파일">{Object.keys(files).map(name=><Button aria-pressed={path===name} key={name} onClick={()=>setSelected(name)}>{name}</Button>)}</div><div className="reference-file-content">{path.endsWith('.md')?<>{header&&<pre className="reference-skill-metadata"><code>{header[1]}</code></pre>}<Markdown language="text">{header?files[path].slice(header[0].length):files[path]}</Markdown></>:<pre><code>{files[path]}</code></pre>}</div>{path.startsWith('scripts/')&&<p className="reference-file-note">생성된 스크립트입니다. 여기에서는 실행하지 않습니다.</p>}</>;
}
function PackageEditor({id,pkg,onRefresh,onSaved,onCancel}:{id:string;pkg:Package;onRefresh:(value:Package)=>void;onSaved:(value:Package)=>void;onCancel:()=>void}) {
  const {userId}=useApp(), key='reference-package:'+userId+':'+id;
  const [draft,setDraft]=useState<{revision:number;files:Record<string,string>}>(()=>{try{const raw=sessionStorage.getItem(key);if(raw){const value=JSON.parse(raw);if(Number.isInteger(value.revision)&&value.files&&typeof value.files==='object'&&Object.values(value.files).every(x=>typeof x==='string'))return value;}}catch{/* Keep the server copy available if browser storage is unavailable. */}return {revision:pkg.revision,files:{...pkg.files}};});
  const [selected,setSelected]=useState('SKILL.md'),[newPath,setNewPath]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[storageError,setStorageError]=useState('');
  const dirty=JSON.stringify(draft.files)!==JSON.stringify(pkg.files)||draft.revision!==pkg.revision;
  const blocker=useBlocker(dirty&&!busy);
  useEffect(()=>{if(blocker.state==='blocked'){if(window.confirm('수정 중인 파일을 임시 보관하고 이동할까요?'))blocker.proceed();else blocker.reset();}},[blocker]);
  useEffect(()=>{if(!dirty)return;const handler=(event:BeforeUnloadEvent)=>event.preventDefault();window.addEventListener('beforeunload',handler);return()=>window.removeEventListener('beforeunload',handler);},[dirty]);
  function change(files:Record<string,string>) {const value={...draft,files};setDraft(value);try{sessionStorage.setItem(key,JSON.stringify(value));setStorageError('');}catch{setStorageError('브라우저에 초안을 보관하지 못했습니다. 파일 내용을 복사해두세요.');}}
  async function save(){setBusy(true);setError('');try{const result=await api<Package>(`/technical-references/${id}/package`,'PUT',{...draft,status:pkg.status,destination:pkg.destination});try{sessionStorage.removeItem(key);}catch{/* Saved server copy is authoritative. */}onSaved(result);}catch(cause){setError(errorMessage(cause));}finally{setBusy(false);}}
  async function refresh(){if(dirty&&!window.confirm('현재 초안을 지우고 최신 서버 파일을 불러올까요? 먼저 필요한 내용을 복사해주세요.'))return;setBusy(true);try{const result=await api<{package:Package|null}>(`/technical-references/${id}/package`);if(result.package){setDraft({revision:result.package.revision,files:{...result.package.files}});onRefresh(result.package);try{sessionStorage.removeItem(key);}catch{/* Server files are already loaded. */}setError('');setStorageError('');}}catch(cause){setError(errorMessage(cause));}finally{setBusy(false);}}
  const path=selected in draft.files?selected:Object.keys(draft.files)[0];
  return <div className="reference-package-editor"><div className="reference-file-toolbar"><h2>파일 수정</h2><Button disabled={busy} onClick={()=>{if(!dirty||window.confirm('초안을 보관하고 읽기로 돌아갈까요?'))onCancel();}}>읽기로</Button></div><div className="reference-file-tabs">{Object.keys(draft.files).map(name=><Button key={name} disabled={busy} aria-pressed={path===name} onClick={()=>setSelected(name)}>{name}</Button>)}</div>
  <Label htmlFor="package-file">{path}</Label><Textarea id="package-file" className="reference-code-input" value={draft.files[path]} rows={26} maxLength={60000} disabled={busy} onChange={e=>change({...draft.files,[path]:e.target.value})}/>
  {path!=='SKILL.md'&&<Button disabled={busy} onClick={()=>{if(window.confirm('이 파일을 삭제할까요? 기존 내용은 저장 후 변경 이력에 남습니다.')){const files={...draft.files};delete files[path];change(files);setSelected('SKILL.md');}}}>이 파일 삭제</Button>}
  <div className="reference-add-file"><Label className="sr-only" htmlFor="package-new-file">추가할 파일 경로</Label><Input id="package-new-file" placeholder="scripts/check.py 또는 references/guide.md" value={newPath} maxLength={180} disabled={busy} onChange={e=>setNewPath(e.target.value)}/><Button disabled={busy||!newPath||Object.keys(draft.files).length>=30} onClick={()=>{if(!/^(references|scripts)\/[A-Za-z0-9_./-]+$/.test(newPath)||newPath.split('/').some(s=>!s||s==='.'||s==='..')||newPath==='references/provenance.json'){setError('references/ 또는 scripts/ 아래의 파일 경로를 입력해주세요.');return;}if(newPath in draft.files){setError('이미 있는 파일입니다.');return;}change({...draft.files,[newPath]:''});setSelected(newPath);setNewPath('');setError('');}}>파일 추가</Button></div>
  <ErrorNotice error={error||storageError}/>{error&&<Button disabled={busy} onClick={()=>void refresh()}>최신 파일 불러오기</Button>}{draft.revision!==pkg.revision&&<p role="alert">초안의 기준과 현재 저장 버전이 다릅니다. 내용을 복사한 뒤 최신 파일을 확인해주세요.</p>}<Button className="primary" loading={busy} disabled={busy||!dirty} onClick={()=>void save()}>파일 저장</Button></div>;
}
function PackageHistory({id,revision,createdAt}:{id:string;revision:number;createdAt:string}) {const [open,setOpen]=useState(false);return <details onToggle={e=>setOpen(e.currentTarget.open)}><summary>수정 {revision} · {timestamp(createdAt)}</summary>{open&&<HistoryFiles id={id} revision={revision}/>}</details>;}
function HistoryFiles({id,revision}:{id:string;revision:number}) {const {data,error}=useResource<Package>(`/technical-references/${id}/package/versions/${revision}`);return <div className="reference-history-content"><ErrorNotice error={error}/>{!data&&!error&&<LoadingSkeleton layout="article" label="변경 이력을 불러오는 중…"/>}{data&&<>{badge(data.status)}<PackageFiles files={data.files}/></>}</div>;}

function GeneratedResult({id,jobId}:{id:string;jobId:string}) {const [open,setOpen]=useState(false);return <details onToggle={e=>setOpen(e.currentTarget.open)}><summary>생성 결과 보기</summary>{open&&<GeneratedFiles id={id} jobId={jobId}/>}</details>;}
function GeneratedFiles({id,jobId}:{id:string;jobId:string}) {const {data,error}=useResource<{files:Record<string,string>}>(`/technical-references/${id}/skills/${jobId}`);return <div className="reference-generated-files"><ErrorNotice error={error}/>{!data&&!error&&<LoadingSkeleton layout="article" label="생성된 파일을 불러오는 중…"/>}{data?.files&&<PackageFiles files={data.files}/>}</div>;}
