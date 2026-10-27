"""Existing ontology extraction over explicitly reviewed, versioned learning material."""
import json
from . import ai, ai_settings, db, materials, reference_notes, service, usage


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS material_proposals (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id),
        review_id TEXT NOT NULL REFERENCES material_reviews(id),
        state TEXT NOT NULL CHECK(state IN ('queued','running','ready','failed','stale','interrupted')),
        data TEXT, error TEXT NOT NULL DEFAULT '', model TEXT NOT NULL,
        prompt_version TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(owner,id))''')
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS material_proposal_pending ON material_proposals(owner,review_id) WHERE state IN ('queued','running')")
    c.execute('''CREATE TABLE IF NOT EXISTS material_proposal_requests (
        owner TEXT NOT NULL, request_id TEXT NOT NULL, proposal_id TEXT NOT NULL,
        PRIMARY KEY(owner,request_id), FOREIGN KEY(owner,proposal_id) REFERENCES material_proposals(owner,id))''')


def view(owner, identifier):
    row = db.one('SELECT * FROM material_proposals WHERE owner=? AND id=?', (owner, identifier))
    if not row: raise service.Error('추출 후보를 찾을 수 없습니다.', 404)
    row['data'] = json.loads(row['data']) if row['data'] else None
    row['matches'] = []
    for match in (row['data'] or {}).get('matches', []):
        concept = db.one('SELECT * FROM knowledge_concepts WHERE owner=? AND id=?', (owner, match['existing_id']))
        if concept:
            concept['aliases'] = [a['label'] for a in db.all('SELECT label FROM knowledge_aliases WHERE owner=? AND concept_id=?', (owner, concept['id']))]
            row['matches'].append({**concept, 'key': match['key'], 'reason': match['reason'], 'concept': concept})
    material = materials.detail(owner, row['review_id'])
    material.pop('body')
    row['material'] = material
    if row['state'] == 'ready' and material['state'] != 'eligible':
        row.update(state='stale', error=material['reason'])
    row.pop('owner')
    return row


def listing(owner, review_id):
    materials.detail(owner, review_id)
    return [view(owner, r['id']) for r in db.all('SELECT id FROM material_proposals WHERE owner=? AND review_id=? ORDER BY created_at DESC,id DESC LIMIT 20', (owner, review_id))]


def begin(owner, review_id, data):
    with db.connect(write=True) as c:
        replay = c.execute('''SELECT p.id,p.review_id FROM material_proposal_requests r JOIN material_proposals p
            ON p.owner=r.owner AND p.id=r.proposal_id WHERE r.owner=? AND r.request_id=?''', (owner, data.request_id)).fetchone()
        if replay:
            if replay['review_id'] != review_id: raise service.Error('같은 요청 ID의 검토 자료가 다릅니다.', 409)
            identifier, fresh = replay['id'], False
        else:
            material = materials.detail(owner, review_id)
            if material['state'] != 'eligible': raise service.Error(material['reason'], 409)
            pending = c.execute("SELECT id FROM material_proposals WHERE owner=? AND review_id=? AND state IN ('queued','running')", (owner, review_id)).fetchone()
            if pending:
                identifier, fresh = pending['id'], False
            else:
                if not ai.available(owner): raise service.Error('설정에서 AI를 연결한 뒤 후보를 생성해주세요.', 503)
                service.rate('material-proposal:' + owner, 5, 3600)
                identifier, fresh = service.uid(), True
                c.execute('INSERT INTO material_proposals VALUES (?,?,?,\'queued\',NULL,\'\',?,?,?)',
                          (identifier, owner, review_id, ai_settings.model_name(owner), 'reviewed-material-v1', service.now()))
            c.execute('INSERT INTO material_proposal_requests VALUES (?,?,?)', (owner, data.request_id, identifier))
    return view(owner, identifier), fresh


def generate(identifier):
    with db.connect(write=True) as c:
        if not c.execute("UPDATE material_proposals SET state='running' WHERE id=? AND state='queued'", (identifier,)).rowcount: return
        row = dict(c.execute('SELECT * FROM material_proposals WHERE id=?', (identifier,)).fetchone())
    owner = row['owner']
    token = usage.scope.set((owner, identifier))
    try:
        material = materials.detail(owner, row['review_id'])
        if material['state'] != 'eligible':
            db.execute("UPDATE material_proposals SET state='stale',error=? WHERE id=? AND state='running'", (material['reason'], identifier))
            return
        note = {k: material[k] for k in ('title','body','authorship','kind','origin_id','revision','raw_revision','resource_id')}
        data = reference_notes.extract(owner, note)
        with db.connect(write=True) as c:
            current = materials.detail(owner, row['review_id'])
            state = 'ready' if current['state'] == 'eligible' else 'stale'
            c.execute("UPDATE material_proposals SET state=?,data=?,error=? WHERE id=? AND state='running'",
                      (state, data.model_dump_json(), current['reason'], identifier))
    except (ai.AIError, service.Error) as error:
        db.execute("UPDATE material_proposals SET state='failed',error=? WHERE id=? AND state='running'", (str(error), identifier))
    except Exception:
        db.execute("UPDATE material_proposals SET state='failed',error='후보를 준비하지 못했습니다. 검토한 자료는 보존되어 있습니다.' WHERE id=? AND state='running'", (identifier,))
    finally:
        usage.scope.reset(token)
