"""Editable Skill packages; document lifecycle is independent of generation jobs."""
import io
import json
import posixpath
import re
import zipfile
from typing import Literal
from pydantic import Field
from .schema import Model
from . import db, service, learning_links, technical_references as refs


class ApplyJob(Model):
    revision: int = Field(ge=0)
    job_id: str = Field(pattern=r'^[a-f0-9]{32}$')


class Edit(Model):
    revision: int = Field(ge=0)
    files: dict[str, str]
    status: Literal['backlog', 'active', 'merged']
    destination: str = Field(default='', max_length=1000)


def initialize(c):
    c.executescript('''
      CREATE TABLE IF NOT EXISTS reference_packages (
        reference_id TEXT PRIMARY KEY REFERENCES technical_references(id), owner TEXT NOT NULL REFERENCES users(id),
        revision INTEGER NOT NULL, status TEXT NOT NULL, files TEXT NOT NULL, destination TEXT NOT NULL,
        job_id TEXT NOT NULL, updated_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS reference_package_versions (
        owner TEXT NOT NULL, reference_id TEXT NOT NULL REFERENCES technical_references(id), revision INTEGER NOT NULL,
        data TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(owner,reference_id,revision));
    ''')
    # Existing completed Skill jobs are real AI drafts, never implicit approvals.
    rows=c.execute("""SELECT j.* FROM technical_reference_jobs j WHERE j.kind='skill' AND j.state='ready'
        AND NOT EXISTS (SELECT 1 FROM reference_packages p WHERE p.reference_id=j.reference_id)
        AND j.rowid=(SELECT MAX(k.rowid) FROM technical_reference_jobs k WHERE k.reference_id=j.reference_id AND k.kind='skill' AND k.state='ready')""").fetchall()
    for row in rows:
        try:
            files=generated_files(dict(row),refs.SkillDraft.model_validate_json(row['data']))
        except (ValueError,service.Error):
            continue
        persist(c,row['owner'],row['reference_id'],1,files,'backlog','',row['id'])


def validate_files(files):
    if not 1 <= len(files) <= 30 or sum(len(v) for v in files.values()) > 400000:
        raise service.Error('패키지는 최대 30개 파일, 총 400,000자까지 저장할 수 있습니다.',422)
    for path,content in files.items():
        if (len(path)>180 or not re.fullmatch(r'(?:SKILL\.md|(?:references|scripts)/(?:[A-Za-z0-9_-][A-Za-z0-9_.-]*/)*[A-Za-z0-9_-][A-Za-z0-9_.-]*)',path)
                or path=='references/provenance.json' or len(content)>60000 or '\x00' in content):
            raise service.Error('파일 경로나 내용이 올바르지 않습니다. SKILL.md, references/, scripts/만 사용할 수 있습니다.',422)
    markdown=files.get('SKILL.md','')
    match=re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)',markdown,re.S)
    fields={}
    if match:
        # shortcut: headers accept single-line scalars; use a YAML parser if multiline metadata is added.
        for line in match[1].splitlines():
            if ':' not in line: raise service.Error('Skill 헤더는 name과 한 줄 description으로 작성해주세요.',422)
            key,value=line.split(':',1); value=value.strip()
            if value.startswith('"'):
                try: value=json.loads(value)
                except ValueError: raise service.Error('Skill 헤더의 문자열을 확인해주세요.',422)
            elif value.startswith("'") and value.endswith("'"): value=value[1:-1].replace("''", "'")
            elif (not value or value[0] in '|>&*![{#@`' or ': ' in value or ' #' in value
                  or value.lower() in ('true','false','null','yes','no','on','off','~') or re.fullmatch(r'[0-9.+-]+',value)):
                raise service.Error('Skill 헤더의 name과 description을 큰따옴표로 감싸주세요.',422)
            if key in fields: raise service.Error('Skill 헤더가 중복되었습니다.',422)
            fields[key]=value
    if set(fields)!={'name','description'}: raise service.Error('Skill 헤더에는 name과 description을 입력해주세요.',422)
    name=fields.get('name',''); description=fields.get('description','')
    if (not isinstance(name,str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',name) or len(name)>64
            or not isinstance(description,str) or not description.strip() or len(description)>1024):
        raise service.Error('SKILL.md 헤더에 소문자 영문 name과 한 줄 description을 입력해주세요.',422)
    available=set(files)|{'references/provenance.json'}
    for path,content in files.items():
        if not path.endswith('.md'): continue
        for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',content):
            if link.startswith(('https://','http://','#')): continue
            target=posixpath.normpath(posixpath.join(posixpath.dirname(path),link.split('#')[0]))
            if target not in available:
                raise service.Error('패키지에 없는 내부 링크가 있습니다: '+link[:160],422)
    return name


def generated_files(row,skill):
    value=json.loads(row['snapshot'])
    reference='# '+value['title']+'\n\n'
    excerpt_limit=40000//max(1,len(value['sources']))
    for source in value['sources']:
        excerpt=source.get('excerpt','')[:excerpt_limit]
        fence='`'*max(3,max((len(m[0]) for m in re.finditer(r'`+',excerpt)),default=0)+1)
        reference+=f"## {source['title']}\n\n근거: {source['basis']} / 버전: {source.get('revision')}\n\n{fence}text\n{excerpt}\n{fence}\n\n"
    reference+='원자료 본문은 발췌입니다. 생성 시점의 전체 근거 스냅샷은 provenance.json에서 확인할 수 있습니다.\n'
    files={'SKILL.md':refs.skill_markdown(skill),'references/REFERENCE.md':reference}
    for file in skill.files:
        if file.path in files: raise service.Error('생성된 파일 경로가 중복되었습니다.',422)
        files[file.path]=file.content
    validate_files(files)
    return files


def persist(c,owner,identifier,revision,files,status,destination,job_id):
    value={'revision':revision,'files':files,'status':status,'destination':destination,'job_id':job_id,'updated_at':service.now()}
    c.execute('''INSERT INTO reference_packages VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(reference_id) DO UPDATE SET
        revision=excluded.revision,status=excluded.status,files=excluded.files,destination=excluded.destination,
        job_id=excluded.job_id,updated_at=excluded.updated_at''',
        (identifier,owner,revision,status,service.dump(files),destination,job_id,value['updated_at']))
    c.execute('INSERT INTO reference_package_versions VALUES (?,?,?,?,?)',(owner,identifier,revision,service.dump(value),value['updated_at']))


def apply_generated(row,skill,expected_revision,check_source=True):
    files=generated_files(row,skill)
    with db.connect(write=True) as c:
        if check_source and refs.owned(row['owner'],row['reference_id'],c)['revision']!=row['revision']: return False
        current=c.execute('SELECT * FROM reference_packages WHERE owner=? AND reference_id=?',(row['owner'],row['reference_id'])).fetchone()
        if (current['revision'] if current else 0)!=expected_revision: return False
        persist(c,row['owner'],row['reference_id'],expected_revision+1,files,current['status'] if current else 'backlog',
                current['destination'] if current else '',row['id'])
    return True


def read(owner,identifier):
    refs.owned(owner,identifier)
    row=db.one('SELECT * FROM reference_packages WHERE owner=? AND reference_id=?',(owner,identifier))
    if not row: return None
    result={k:v for k,v in row.items() if k not in ('owner','reference_id')}
    result['files']=json.loads(result['files'])
    result['history']=db.all('SELECT revision,created_at FROM reference_package_versions WHERE owner=? AND reference_id=? ORDER BY revision DESC',(owner,identifier))
    job=db.one('SELECT snapshot,fingerprint,revision FROM technical_reference_jobs WHERE owner=? AND id=?',(owner,row['job_id']))
    result['sources']=json.loads(job['snapshot'])['sources'] if job else []
    try: result['stale']=not job or job['fingerprint']!=refs.digest(refs.skill_snapshot(owner,identifier))
    except service.Error: result['stale']=True
    return result


def save(owner,identifier,body):
    refs.owned(owner,identifier)
    validate_files(body.files)
    with db.connect(write=True) as c:
        current=c.execute('SELECT * FROM reference_packages WHERE owner=? AND reference_id=?',(owner,identifier)).fetchone()
        if not current: raise service.Error('먼저 Skill을 생성해주세요.',409)
        if current['revision']!=body.revision: raise service.Error('다른 곳에서 수정되었습니다. 초안을 복사한 뒤 최신 내용을 불러와주세요.',409)
        persist(c,owner,identifier,body.revision+1,body.files,body.status,body.destination.strip(),current['job_id'])
    return read(owner,identifier)


def version(owner,identifier,revision):
    refs.owned(owner,identifier)
    row=db.one('SELECT data FROM reference_package_versions WHERE owner=? AND reference_id=? AND revision=?',(owner,identifier,revision))
    if not row: raise service.Error('패키지 변경 이력을 찾을 수 없습니다.',404)
    return json.loads(row['data'])


def download(owner,identifier):
    value=read(owner,identifier)
    if not value: raise service.Error('먼저 Skill을 생성해주세요.',409)
    name=validate_files(value['files']); buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
        for path,content in value['files'].items(): archive.writestr(name+'/'+path,content)
        archive.writestr(name+'/references/provenance.json',service.dump({
            'reference_id':identifier,'revision':value['revision'],'job_id':value['job_id'],'sources':value['sources'],
            'validation':'Package paths and links checked; scripts are not executed by generation, approval or export.'}))
    return buffer.getvalue()


def sources(owner,query):
    candidates=learning_links.listing(owner,query)
    activity={}
    for row in db.all('SELECT target FROM study_locations WHERE owner=? ORDER BY updated_at DESC LIMIT 50',(owner,)):
        target=json.loads(row['target'])
        if target['kind'] in ('problem','worksheet','reference'): continue
        key=(target['kind'],target['id'],target.get('unit_id',''))
        activity[key]='최근 방문한 학습'
        try:
            resolved=learning_links.resolve(owner,learning_links.Target(**{k:target.get(k,'') for k in ('kind','id','unit_id')}))
            if query.casefold() in resolved['title'].casefold(): candidates.append(resolved)
        except service.Error: pass
    for row in db.all('SELECT lesson_id FROM foundation_attempts WHERE owner=? GROUP BY lesson_id ORDER BY MAX(created_at) DESC LIMIT 20',(owner,)):
        try:
            resolved=learning_links.resolve(owner,learning_links.Target(kind='foundation',id=row['lesson_id']))
            if query.casefold() in resolved['title'].casefold(): candidates.append(resolved)
            activity[('foundation',row['lesson_id'],'')]='실습 제출 기록이 있는 학습'
        except service.Error: pass
    result={}
    for target in candidates:
        if target['kind']=='reference': continue
        key=(target['kind'],target['id'],target['unit_id'])
        reason=activity.get(key,'남겨둔 질문' if target['kind']=='question' else '')
        result[key]={**target,'recommended':bool(reason),'reason':reason}
    return {'items':sorted(result.values(),key=lambda x:not x['recommended'])}


def apply_job(owner,identifier,body):
    refs.owned(owner,identifier)
    row=db.one("SELECT * FROM technical_reference_jobs WHERE owner=? AND reference_id=? AND id=? AND kind='skill' AND state='ready'",(owner,identifier,body.job_id))
    if not row: raise service.Error('완료한 Skill 생성 결과를 찾을 수 없습니다.',404)
    if not apply_generated(row,refs.SkillDraft.model_validate_json(row['data']),body.revision,check_source=False):
        raise service.Error('패키지가 변경되었습니다. 최신 내용을 확인해주세요.',409)
    return read(owner,identifier)
