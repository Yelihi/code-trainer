"""Shared concept identity, typed assertions and versioned provenance."""
import hashlib
import json
from . import db, service
from .note_schema import KnowledgeProposal

RELATIONS = {'CLAIM': '주장', 'PREREQUISITE_OF': '선행 개념', 'BROADER_THAN': '상위 개념',
             'USED_IN': '활용되는 개념', 'RELATED_TO': '연관 개념'}


def initialize(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS reference_notes (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id), title TEXT NOT NULL,
      body TEXT NOT NULL, metadata TEXT NOT NULL, revision INTEGER NOT NULL,
      archived INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      UNIQUE(owner,id));
    CREATE TABLE IF NOT EXISTS reference_note_versions (
      owner TEXT NOT NULL, note_id TEXT NOT NULL, revision INTEGER NOT NULL,
      data TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(owner,note_id,revision),
      FOREIGN KEY(owner,note_id) REFERENCES reference_notes(owner,id));
    CREATE TABLE IF NOT EXISTS reference_images (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id), name TEXT NOT NULL,
      content BLOB NOT NULL, digest TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(owner,digest));
    CREATE TABLE IF NOT EXISTS knowledge_sources (
      owner TEXT NOT NULL REFERENCES users(id), id TEXT NOT NULL, kind TEXT NOT NULL,
      origin_id TEXT NOT NULL, version INTEGER NOT NULL, title TEXT NOT NULL,
      body TEXT NOT NULL, metadata TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'active',
      created_at TEXT NOT NULL, PRIMARY KEY(owner,id), UNIQUE(owner,kind,origin_id,version));
    CREATE TABLE IF NOT EXISTS knowledge_concepts (
      owner TEXT NOT NULL REFERENCES users(id), id TEXT NOT NULL, pref_label TEXT NOT NULL,
      definition TEXT NOT NULL, scope TEXT NOT NULL, status TEXT NOT NULL,
      legacy_key TEXT, created_at TEXT NOT NULL, PRIMARY KEY(owner,id), UNIQUE(owner,legacy_key));
    CREATE TABLE IF NOT EXISTS knowledge_aliases (
      owner TEXT NOT NULL, concept_id TEXT NOT NULL, label TEXT NOT NULL, language TEXT NOT NULL,
      PRIMARY KEY(owner,concept_id,label,language),
      FOREIGN KEY(owner,concept_id) REFERENCES knowledge_concepts(owner,id));
    CREATE TABLE IF NOT EXISTS knowledge_assertions (
      owner TEXT NOT NULL, id TEXT NOT NULL, subject TEXT NOT NULL, kind TEXT NOT NULL,
      object TEXT, text TEXT NOT NULL, scope TEXT NOT NULL, signature TEXT NOT NULL,
      created_at TEXT NOT NULL, PRIMARY KEY(owner,id), UNIQUE(owner,signature),
      CHECK(kind IN ('CLAIM','PREREQUISITE_OF','BROADER_THAN','USED_IN','RELATED_TO')),
      CHECK((kind='CLAIM' AND object IS NULL) OR (kind!='CLAIM' AND object IS NOT NULL AND subject!=object)),
      FOREIGN KEY(owner,subject) REFERENCES knowledge_concepts(owner,id),
      FOREIGN KEY(owner,object) REFERENCES knowledge_concepts(owner,id));
    CREATE TABLE IF NOT EXISTS knowledge_evidence (
      owner TEXT NOT NULL, id TEXT NOT NULL, concept_id TEXT, assertion_id TEXT,
      source_id TEXT NOT NULL, quote TEXT NOT NULL, location TEXT NOT NULL,
      basis TEXT NOT NULL, disposition TEXT NOT NULL DEFAULT 'supports',
      PRIMARY KEY(owner,id), CHECK((concept_id IS NULL)!=(assertion_id IS NULL)),
      FOREIGN KEY(owner,concept_id) REFERENCES knowledge_concepts(owner,id),
      FOREIGN KEY(owner,assertion_id) REFERENCES knowledge_assertions(owner,id),
      FOREIGN KEY(owner,source_id) REFERENCES knowledge_sources(owner,id));
    CREATE INDEX IF NOT EXISTS evidence_source ON knowledge_evidence(owner,source_id);
    CREATE TABLE IF NOT EXISTS knowledge_proposals (
      owner TEXT NOT NULL REFERENCES users(id), id TEXT NOT NULL, note_id TEXT NOT NULL,
      revision INTEGER NOT NULL, state TEXT NOT NULL, data TEXT, error TEXT NOT NULL DEFAULT '',
      model TEXT NOT NULL, prompt_version TEXT NOT NULL, created_at TEXT NOT NULL,
      PRIMARY KEY(owner,id), FOREIGN KEY(owner,note_id) REFERENCES reference_notes(owner,id));
    CREATE UNIQUE INDEX IF NOT EXISTS proposal_running ON knowledge_proposals(owner,note_id) WHERE state='running';
    CREATE TABLE IF NOT EXISTS knowledge_registrations (
      owner TEXT NOT NULL, request_id TEXT NOT NULL, source_id TEXT NOT NULL,
      payload TEXT NOT NULL, provenance TEXT NOT NULL, created_at TEXT NOT NULL,
      PRIMARY KEY(owner,request_id), UNIQUE(owner,source_id),
      FOREIGN KEY(owner,source_id) REFERENCES knowledge_sources(owner,id));
    CREATE TABLE IF NOT EXISTS reference_reviews (
      owner TEXT NOT NULL REFERENCES users(id), id TEXT NOT NULL, request_id TEXT NOT NULL,
      note_id TEXT NOT NULL, sources TEXT NOT NULL, concept_ids TEXT NOT NULL,
      turns TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL,
      error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
      PRIMARY KEY(owner,id), UNIQUE(owner,request_id),
      FOREIGN KEY(owner,note_id) REFERENCES reference_notes(owner,id));
    CREATE TABLE IF NOT EXISTS learning_observations (
      owner TEXT NOT NULL, id TEXT NOT NULL, concept_id TEXT NOT NULL, review_id TEXT,
      kind TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL,
      PRIMARY KEY(owner,id), FOREIGN KEY(owner,concept_id) REFERENCES knowledge_concepts(owner,id),
      FOREIGN KEY(owner,review_id) REFERENCES reference_reviews(owner,id));
    ''')


def concepts(owner, query=''):
    rows = db.all('''SELECT c.* FROM knowledge_concepts c WHERE c.owner=? AND
        (?='' OR c.pref_label LIKE ? OR c.definition LIKE ? OR EXISTS(
        SELECT 1 FROM knowledge_aliases a WHERE a.owner=c.owner AND a.concept_id=c.id AND a.label LIKE ?))
        ORDER BY c.pref_label,c.id LIMIT 200''', (owner, query, *(['%' + query + '%'] * 3)))
    aliases = db.all('SELECT * FROM knowledge_aliases WHERE owner=?', (owner,))
    return [{**r, 'aliases': [a['label'] for a in aliases if a['concept_id'] == r['id']]} for r in rows]


def evidence(c, owner, source, body, quote, basis, concept_id=None, assertion_id=None, disposition='supports'):
    start = body.find(quote)
    if start < 0:
        raise service.Error('근거 문장이 저장된 노트 본문에 없습니다. 원문에서 다시 선택해주세요.', 422)
    key = hashlib.sha256(service.dump([source, concept_id, assertion_id, quote, basis, disposition]).encode()).hexdigest()
    location = service.dump({'start': start, 'end': start + len(quote)})
    c.execute('INSERT OR IGNORE INTO knowledge_evidence VALUES (?,?,?,?,?,?,?,?,?)',
              (owner, key, concept_id, assertion_id, source, quote, location, basis, disposition))


def validate_proposal(owner, data, body):
    keys = [item.key for item in data.concepts]
    if len(keys) != len(set(keys)):
        raise service.Error('개념의 임시 식별자가 중복되었습니다.', 422)
    existing = {r['id'] for r in db.all('SELECT id FROM knowledge_concepts WHERE owner=?', (owner,))}
    for item in data.concepts:
        if item.existing_id and item.existing_id not in existing:
            raise service.Error('연결할 기존 개념을 찾을 수 없습니다.', 422)
    for item in [*data.concepts, *data.assertions]:
        if item.quote not in body:
            raise service.Error('근거 문장이 저장된 노트 본문과 일치하지 않습니다.', 422)
    for item in data.assertions:
        if item.subject not in keys or (item.kind != 'CLAIM' and item.object not in keys):
            raise service.Error('관계 양 끝의 개념을 먼저 선택해주세요.', 422)
        if item.kind == 'CLAIM' and item.object:
            raise service.Error('주장의 목적 개념은 비워주세요.', 422)


def register(c, owner, source, body, data: KnowledgeProposal):
    mapped = {}
    for item in data.concepts:
        key = item.existing_id or service.uid()
        if item.existing_id:
            existing = c.execute('SELECT * FROM knowledge_concepts WHERE owner=? AND id=?', (owner, key)).fetchone()
            if not existing:
                raise service.Error('연결할 개념을 찾을 수 없습니다.', 404)
            if existing['status'] == 'provisional' and item.definition != existing['definition']:
                c.execute("UPDATE knowledge_concepts SET definition=?,scope=?,status='confirmed' WHERE owner=? AND id=?",
                          (item.definition, item.scope, owner, key))
        else:
            c.execute('INSERT INTO knowledge_concepts VALUES (?,?,?,?,?,?,?,?)',
                      (owner, key, item.pref_label, item.definition, item.scope, 'confirmed', None, service.now()))
        mapped[item.key] = key
        for label in item.aliases:
            c.execute('INSERT OR IGNORE INTO knowledge_aliases VALUES (?,?,?,?)', (owner, key, label, 'und'))
        evidence(c, owner, source, body, item.quote, item.basis, concept_id=key)
    for item in data.assertions:
        subject, target = mapped[item.subject], mapped.get(item.object)
        if item.kind != 'CLAIM' and subject == target:
            raise service.Error('자기 자신을 가리키는 관계는 추가할 수 없습니다.', 422)
        if item.kind == 'RELATED_TO' and subject > target:
            subject, target = target, subject
        if item.kind in ('BROADER_THAN', 'PREREQUISITE_OF') and item.disposition == 'supports' and item.basis != 'question':
            cycle = c.execute('''WITH RECURSIVE reach(id) AS (
                SELECT ? UNION SELECT a.object FROM knowledge_assertions a JOIN reach r ON a.subject=r.id
                JOIN knowledge_evidence e ON e.owner=a.owner AND e.assertion_id=a.id
                JOIN knowledge_sources s ON s.owner=e.owner AND s.id=e.source_id
                WHERE a.owner=? AND a.kind=? AND s.state='active' AND e.basis!='question' AND e.disposition='supports')
                SELECT 1 FROM reach WHERE id=?''', (target, owner, item.kind, subject)).fetchone()
            if cycle:
                raise service.Error('상하 또는 선행 관계에 순환이 생깁니다. 관계 방향을 확인해주세요.', 422)
        signature = hashlib.sha256(service.dump([subject, item.kind, target, item.scope,
                                               item.text if item.kind == 'CLAIM' else '']).encode()).hexdigest()
        key = service.uid()
        c.execute('INSERT OR IGNORE INTO knowledge_assertions VALUES (?,?,?,?,?,?,?,?,?)',
                  (owner, key, subject, item.kind, target, item.text, item.scope, signature, service.now()))
        key = c.execute('SELECT id FROM knowledge_assertions WHERE owner=? AND signature=?', (owner, signature)).fetchone()['id']
        evidence(c, owner, source, body, item.quote, item.basis, assertion_id=key, disposition=item.disposition)
    return list(dict.fromkeys(mapped.values()))


def save_entry(c, owner, key, data, created_at):
    """Migrate explicit unit registrations without inventing cross-source synonym matches."""
    if c.execute('SELECT id FROM knowledge_sources WHERE owner=? AND kind=? AND origin_id=?',
                 (owner, 'learning', key)).fetchone():
        return
    source = service.uid()
    labels = data['concepts'] or ([data['title']] if key.startswith('foundation:') else [])
    body = '\n\n'.join(data['descriptions']) + '\n\n다루는 개념: ' + ', '.join(labels)
    c.execute('INSERT INTO knowledge_sources VALUES (?,?,?,?,?,?,?,?,?,?)',
              (owner, source, 'learning', key, data.get('unit', {}).get('version', 1),
               data['title'], body, service.dump(data), 'active', created_at))
    from .knowledge import node_id
    for label in dict.fromkeys(labels):
        old_key = node_id('topic', key, label.strip().casefold())
        concept = service.uid()
        c.execute('INSERT INTO knowledge_concepts VALUES (?,?,?,?,?,?,?,?)',
                  (owner, concept, label, '등록한 학습 단원에서 다루는 개념입니다. 연결 전에 범위를 확인해주세요.',
                   data['scope'], 'provisional', old_key, created_at))
        # A curriculum label is provenance for coverage, not an asserted definition.
        evidence(c, owner, source, body, label, 'source', concept_id=concept)


def migrate():
    from .foundations import CATALOG
    with db.connect(write=True) as c:
        for row in c.execute('SELECT * FROM knowledge_entries').fetchall():
            save_entry(c, row['owner'], row['node_id'], json.loads(row['data']), row['created_at'])
            available = (c.execute('SELECT id FROM contexts WHERE owner=? AND id=?', (row['owner'], row['context_id'])).fetchone()
                         if row['context_id'] else CATALOG.get(row['unit_id'], {}).get('version') == row['version'])
            if not available:
                c.execute("UPDATE knowledge_sources SET state='deleted' WHERE owner=? AND kind='learning' AND origin_id=?", (row['owner'], row['node_id']))


def extend_graph(owner, graph):
    sources = {r['id']: r for r in db.all('SELECT * FROM knowledge_sources WHERE owner=?', (owner,))}
    notes = {r['id']: r for r in db.all('SELECT id,revision,archived FROM reference_notes WHERE owner=?', (owner,))}
    all_concepts = db.all('SELECT * FROM knowledge_concepts WHERE owner=?', (owner,))
    evidence_rows = db.all('SELECT * FROM knowledge_evidence WHERE owner=?', (owner,))
    active = [e for e in evidence_rows if sources[e['source_id']]['state'] == 'active' and e['basis'] != 'question']
    live_nodes = {n['id']: n for n in graph['nodes']}
    remap = {c['legacy_key']: c['id'] for c in all_concepts if c['legacy_key']}
    for old, new in remap.items():
        if old in live_nodes:
            live_nodes[new] = {**live_nodes.pop(old), 'id': new}
    for edge in graph['edges']:
        edge['source'] = remap.get(edge['source'], edge['source'])
        edge['target'] = remap.get(edge['target'], edge['target'])
    aliases = db.all('SELECT * FROM knowledge_aliases WHERE owner=?', (owner,))
    assertions = db.all('SELECT * FROM knowledge_assertions WHERE owner=?', (owner,))
    def source_view(s):
        return {'id': s['id'], 'title': s['title'], 'version': s['version'], 'state': s['state'],
                'note_id': s['origin_id'] if s['kind'] == 'note' else None,
                'metadata': json.loads(s['metadata']) if s['kind'] == 'note' else {}}
    for concept in all_concepts:
        proofs = [e for e in evidence_rows if e['concept_id'] == concept['id']]
        if not proofs:
            continue
        node = live_nodes.setdefault(concept['id'], {'id': concept['id'], 'kind': 'concept', 'exercise_ids': []})
        node.update(label=concept['pref_label'], scope=concept['scope'], descriptions=[concept['definition']],
                    ontology_status=concept['status'], aliases=[a['label'] for a in aliases if a['concept_id'] == concept['id']],
                    sources=[{**source_view(sources[e['source_id']]), 'quote': e['quote'], 'basis': e['basis']} for e in proofs],
                    claims=[{'text': a['text'], 'scope': a['scope'],
                             'contested': any(e['assertion_id'] == a['id'] and e['disposition'] == 'refutes' for e in active),
                             'sources': [{**source_view(sources[e['source_id']]), 'quote': e['quote'], 'basis': e['basis'], 'disposition': e['disposition']}
                                         for e in active if e['assertion_id'] == a['id']]}
                            for a in assertions if a['subject'] == concept['id'] and a['kind'] == 'CLAIM'
                            and any(e['assertion_id'] == a['id'] for e in active)])
    for source in sources.values():
        if source['kind'] == 'learning' and source['origin_id'] in live_nodes:
            for proof in evidence_rows:
                if proof['source_id'] == source['id'] and proof['concept_id'] in live_nodes:
                    source_node = live_nodes[source['origin_id']]
                    concept_node = live_nodes[proof['concept_id']]
                    concept_node['exercise_ids'] = sorted(set(concept_node['exercise_ids']) | set(source_node['exercise_ids']))
                    if not any(e['source'] == source_node['id'] and e['target'] == concept_node['id'] for e in graph['edges']):
                        graph['edges'].append({'id': proof['id'], 'source': source_node['id'], 'target': concept_node['id'],
                            'kind': 'coverage', 'label': '다루는 개념', 'description': '사용자가 등록한 학습 단원의 개념 목록입니다.',
                            'exercise_ids': []})
        if source['kind'] != 'note' or source['state'] == 'deleted':
            continue
        note = notes.get(source['origin_id'])
        if not note or note['archived']:
            continue
        # Only the latest explicitly registered snapshot is visible as a note node.
        newer = any(s['kind'] == 'note' and s['origin_id'] == source['origin_id'] and s['version'] > source['version'] for s in sources.values())
        if newer:
            continue
        key = 'note:' + source['origin_id']
        live_nodes[key] = {'id': key, 'kind': 'note', 'label': source['title'], 'scope': '레퍼런스 노트',
                           'note_id': source['origin_id'], 'descriptions': [source['body'][:600]],
                           'exercise_ids': [], 'added_at': source['created_at'], 'needs_review': source['state'] != 'active'}
        for proof in evidence_rows:
            if proof['source_id'] == source['id'] and proof['concept_id'] in live_nodes:
                graph['edges'].append({'id': proof['id'], 'source': key, 'target': proof['concept_id'],
                    'kind': 'coverage', 'label': '다루는 개념' if source['state'] == 'active' else '재검토할 근거',
                    'description': proof['quote'], 'exercise_ids': []})
    for assertion in assertions:
        proofs = [e for e in active if e['assertion_id'] == assertion['id']]
        if assertion['kind'] != 'CLAIM' and proofs and assertion['subject'] in live_nodes and assertion['object'] in live_nodes:
            graph['edges'].append({'id': assertion['id'], 'source': assertion['subject'], 'target': assertion['object'],
                'kind': assertion['kind'], 'label': RELATIONS[assertion['kind']] + (' · 반박 근거 있음' if any(e['disposition'] == 'refutes' for e in proofs) else ''),
                'description': assertion['text'],
                'exercise_ids': [], 'sources': [{**source_view(sources[e['source_id']]), 'quote': e['quote'], 'disposition': e['disposition']} for e in proofs]})
    graph['nodes'] = list(live_nodes.values())
    return graph
