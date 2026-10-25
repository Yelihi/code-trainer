"""Explicit choices preserve adopted guides and keep rejected bodies temporary."""
import json
from datetime import datetime,timedelta
from . import db,service,insight_context


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS explorations (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id), bundle_id TEXT NOT NULL,
        item_index INTEGER NOT NULL, data TEXT NOT NULL, context TEXT NOT NULL, model TEXT NOT NULL,
        notes TEXT NOT NULL DEFAULT '', revision INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(owner,bundle_id,item_index))''')
    c.execute('''CREATE TABLE IF NOT EXISTS insight_skips (
        owner TEXT NOT NULL REFERENCES users(id), bundle_id TEXT NOT NULL, item_index INTEGER NOT NULL,
        fingerprint TEXT NOT NULL, expires_at TEXT NOT NULL, PRIMARY KEY(owner,bundle_id,item_index))''')


def item_fingerprint(item):
    return insight_context.fingerprint([sorted(set(item.concept_ids)),sorted(set(item.assertion_ids))])


def filter_skipped(owner,items,connection=None):
    if connection is None:
        with db.connect(write=True) as c:return filter_skipped(owner,items,c)
    connection.execute('DELETE FROM insight_skips WHERE owner=? AND expires_at<=?',(owner,service.now()))
    skipped={x['fingerprint'] for x in connection.execute('SELECT fingerprint FROM insight_skips WHERE owner=?',(owner,))}
    return [item for item in items if item_fingerprint(item) not in skipped]


def choices(owner,bundle):
    selected={str(r['item_index']):dict(action='adopt',id=r['id']) for r in db.all('SELECT id,item_index FROM explorations WHERE owner=? AND bundle_id=?',(owner,bundle))}
    selected.update({str(r['item_index']):dict(action='skip') for r in db.all('SELECT item_index FROM insight_skips WHERE owner=? AND bundle_id=? AND expires_at>?',(owner,bundle,service.now()))})
    return selected


def choose(owner,bundle,index,action):
    from .insight_schema import Insight
    with db.connect(write=True) as c:
        adopted=c.execute('SELECT id FROM explorations WHERE owner=? AND bundle_id=? AND item_index=?',(owner,bundle,index)).fetchone()
        skipped=c.execute('SELECT 1 FROM insight_skips WHERE owner=? AND bundle_id=? AND item_index=? AND expires_at>?',(owner,bundle,index,service.now())).fetchone()
        if adopted or skipped:
            if (adopted and action!='adopt') or (skipped and action!='skip'):raise service.Error('이미 선택한 제안입니다.',409)
            return dict(action='adopt',id=adopted['id']) if adopted else dict(action='skip')
        row=c.execute('SELECT * FROM insight_bundles WHERE owner=? AND id=? AND expires_at>?',(owner,bundle,service.now())).fetchone()
        if not row:raise service.Error('현재 제안 묶음을 다시 확인해주세요.',409)
        context=json.loads(row['context']);items=json.loads(row['data'])['suggestions']
        if not 0<=index<len(items):raise service.Error('제안을 찾을 수 없습니다.',404)
        if not insight_context.valid(owner,context):raise service.Error('근거가 변경되었습니다. 새 제안을 받아주세요.',409)
        item=Insight.model_validate(items[index]);clock=service.now()
        if action=='skip':
            expires=(datetime.fromisoformat(clock)+timedelta(days=30)).isoformat()
            c.execute('INSERT INTO insight_skips VALUES (?,?,?,?,?)',(owner,bundle,index,item_fingerprint(item),expires))
            return dict(action='skip')
        if action!='adopt':raise service.Error('올바른 선택이 아닙니다.',422)
        identifier=service.uid()
        c.execute('INSERT INTO explorations (id,owner,bundle_id,item_index,data,context,model,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)',(identifier,owner,bundle,index,item.model_dump_json(),row['context'],row['model'],clock,clock))
        return dict(action='adopt',id=identifier)


def read(owner,identifier):
    row=db.one('SELECT * FROM explorations WHERE owner=? AND id=?',(owner,identifier))
    if not row:raise service.Error('탐구 기록을 찾을 수 없습니다.',404)
    row.pop('owner');row['data']=json.loads(row['data']);row['context']=json.loads(row['context'])
    row['state']='current' if insight_context.valid(owner,row['context']) else 'stale'
    return row


def listing(owner,page):
    rows=db.all('SELECT id,data,created_at,updated_at,revision FROM explorations WHERE owner=? ORDER BY updated_at DESC,id LIMIT 30 OFFSET ?',(owner,(page-1)*30))
    return dict(items=[dict(id=r['id'],title=json.loads(r['data'])['title'],created_at=r['created_at'],updated_at=r['updated_at'],revision=r['revision']) for r in rows],total=db.one('SELECT COUNT(*) n FROM explorations WHERE owner=?',(owner,))['n'])


def save(owner,identifier,request):
    with db.connect(write=True) as c:
        row=c.execute('SELECT notes,revision FROM explorations WHERE owner=? AND id=?',(owner,identifier)).fetchone()
        if not row:raise service.Error('탐구 기록을 찾을 수 없습니다.',404)
        # Identical content also acknowledges a lost save response without another revision.
        if row['notes']!=request.notes:
            if row['revision']!=request.revision:raise service.Error('다른 화면에서 기록이 바뀌었습니다. 내 작성분을 유지하고 최신본과 비교해주세요.',409)
            c.execute('UPDATE explorations SET notes=?,revision=revision+1,updated_at=? WHERE owner=? AND id=?',(request.notes,service.now(),owner,identifier))
    return read(owner,identifier)
