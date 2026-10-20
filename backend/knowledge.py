"""Explicitly saved learning snapshots and their separate problem-solving evidence."""
import hashlib
import json
from . import db, learning, service, ontology
from .foundations import CATALOG


def node_id(kind, *parts):
    return kind + ':' + hashlib.sha256(service.dump(parts).encode()).hexdigest()[:24]


def add_unit(owner, context_id, unit_id):
    with db.connect(write=True) as c:
        row = c.execute('SELECT data,source_url FROM contexts WHERE owner=? AND id=?', (owner, context_id)).fetchone()
        if not row:
            raise service.Error('학습 자료를 찾을 수 없습니다.', 404)
        context = json.loads(row['data'])
        unit = next((u for u in context.get('units', []) if u['id'] == unit_id), None)
        if not unit or not unit.get('lesson'):
            raise service.Error('생성된 학습 단원을 찾을 수 없습니다.', 404)
        key = node_id('unit', context_id, unit_id)
        data = {'title': unit['title'], 'scope': context.get('framework') or context['language'],
                'descriptions': [unit['objective']] + [s['body'] for s in unit['lesson'] if s.get('body')],
                'concepts': unit['concepts'], 'prerequisites': unit['prerequisites'],
                'source_url': row['source_url'], 'unit': unit}
        return save(c, owner, key, context_id, unit_id, None, data)


def add_foundation(owner, lesson_id, version):
    from .foundations import lesson, public
    item = lesson(lesson_id, version)
    key = node_id('foundation', lesson_id, item['version'])
    data = {'title': item['title'], 'scope': 'typescript',
            'descriptions': [item['summary'], item['concept']], 'concepts': [],
            'prerequisites': item['prerequisites'], 'unit': public(item)}
    with db.connect(write=True) as c:
        return save(c, owner, key, None, lesson_id, item['version'], data)


def save(c, owner, key, context_id, unit_id, version, data):
    # Keep the original snapshot even if the source is edited or deleted later.
    c.execute('INSERT OR IGNORE INTO knowledge_entries VALUES (?,?,?,?,?,?,?)',
              (owner, key, context_id, unit_id, version, service.dump(data), service.now()))
    row = c.execute('SELECT created_at FROM knowledge_entries WHERE owner=? AND node_id=?', (owner, key)).fetchone()
    ontology.save_entry(c, owner, key, data, row['created_at'])
    return {'node_id': key, 'knowledge_added_at': row['created_at']}


def exercise_node(exercise, detail):
    if exercise['kind'] == 'FOUNDATION':
        return node_id('foundation', exercise.get('unit_id'), detail.get('content_version'))
    return node_id('unit', exercise.get('context_id'),
                   exercise.get('unit_id') or exercise.get('set_id') or exercise['id'])


def build(saved, current, historical=False, entries=None):
    live = {item['id']: item for item in current}
    exercises = {item['id']: dict(item) for item in saved['exercises']}
    if not historical:
        for item in learning.public_evidence(current):
            exercises.setdefault(item['id'], {**item, 'deleted': False})
    nodes, edges, units, foundation_units = {}, {}, {}, {}
    for entry in entries or []:
        data, key = json.loads(entry['data']), entry['node_id']
        foundation = entry['context_id'] is None
        nodes[key] = {'id': key, 'kind': 'foundation' if foundation else 'unit',
                      'label': data['title'], 'scope': data['scope'], 'descriptions': data['descriptions'],
                      'exercise_ids': [], 'added_at': entry['created_at'],
                      'context_id': entry['context_id'], 'unit_id': entry['unit_id'],
                      'source_available': entry['source_available']}
        if foundation and entry['source_available']:
            foundation_units[entry['unit_id']] = key
        for label in dict.fromkeys(data['concepts']):
            # shortcut: source-scoped topics avoid claiming synonyms; canonical concept review comes later.
            topic = node_id('topic', key, label.strip().casefold())
            nodes[topic] = {'id': topic, 'kind': 'concept', 'label': label, 'scope': data['scope'],
                            'descriptions': ['직접 추가한 학습 단원에서 다루는 개념입니다. 연결된 단원에서 설명을 확인하세요.'],
                            'exercise_ids': []}
            edge_id = node_id('edge', key, topic, 'coverage')
            edges[edge_id] = {'id': edge_id, 'source': key, 'target': topic, 'kind': 'coverage',
                             'label': '다루는 개념', 'exercise_ids': [],
                             'description': '사용자가 추가한 단원의 개념 목록입니다. 문제 통과나 숙달을 뜻하지 않습니다.'}
    for exercise in exercises.values():
        detail = live.get(exercise['id'], {})
        foundation = exercise['kind'] == 'FOUNDATION'
        version = detail.get('content_version') if foundation else None
        # A deleted legacy exercise may have no context or unit; never merge those placeholders.
        key = exercise_node(exercise, detail)
        node = nodes.setdefault(key, {
            'id': key, 'kind': 'foundation' if foundation else 'unit',
            'label': detail.get('unit_title', exercise['title']), 'scope': exercise['root_label'],
            'descriptions': [detail['description']] if foundation and detail.get('description') else
                            [detail['unit_description']] if detail.get('unit_description') else [],
            'exercise_ids': [],
        })
        node['exercise_ids'].append(exercise['id'])
        units[exercise['id']] = key
        catalog = CATALOG.get(exercise.get('unit_id')) if foundation else None
        if catalog and version == catalog['version'] and not exercise.get('deleted'):
            foundation_units[exercise['unit_id']] = key

    for concept in saved['concepts']:
        ids = sorted({eid for outcome in concept['outcomes'] for eid in outcome['exercise_ids'] if eid in exercises})
        if not ids:
            continue
        # shortcut: legacy concepts have scoped names, replace this identity with canonical IDs during ontology migration.
        key = node_id('concept', concept['root_key'], concept['name'].strip().casefold())
        node = nodes.setdefault(key, {'id': key, 'kind': 'concept', 'label': concept['name'],
                                     'scope': concept['root_key'].removeprefix('framework:'),
                                     'descriptions': [], 'exercise_ids': []})
        node['descriptions'] = list(dict.fromkeys(node['descriptions'] + [o['summary'] for o in concept['outcomes']]))
        node['exercise_ids'] = sorted(set(node['exercise_ids']) | set(ids))
        for eid in ids:
            edge_id = node_id('edge', key, units[eid])
            edge = edges.setdefault(edge_id, {'id': edge_id, 'source': key, 'target': units[eid],
                'kind': 'evidence', 'label': '학습 근거', 'exercise_ids': [],
                'description': '이 단원에서 통과한 문제를 근거로 정리한 개념입니다. 선행 지식이나 숙달을 뜻하지 않습니다.'})
            if eid not in edge['exercise_ids']:
                edge['exercise_ids'].append(eid)

    for lesson_id, target in foundation_units.items():
        for prerequisite in CATALOG[lesson_id]['prerequisites']:
            if prerequisite not in foundation_units:
                continue
            source = foundation_units[prerequisite]
            key = node_id('edge', source, target, 'prerequisite')
            edges[key] = {'id': key, 'source': source, 'target': target, 'kind': 'prerequisite',
                'label': '선행 단원', 'exercise_ids': [],
                'description': f"기초 학습 카탈로그 · {lesson_id} v{CATALOG[lesson_id]['version']}에 지정된 학습 순서입니다. 개념 전체의 필수 조건을 뜻하지 않습니다."}
    for entry in entries or []:
        if not entry['context_id']:
            continue
        for prerequisite in json.loads(entry['data'])['prerequisites']:
            source, target = node_id('unit', entry['context_id'], prerequisite), entry['node_id']
            if source not in nodes:
                continue
            key = node_id('edge', source, target, 'prerequisite')
            edges[key] = {'id': key, 'source': source, 'target': target, 'kind': 'prerequisite',
                          'label': '선행 단원', 'exercise_ids': [],
                          'description': '등록 당시 학습 과정에 지정된 권장 순서입니다. 개념 전체의 필수 조건을 뜻하지 않습니다.'}
    for edge in edges.values():
        if edge['kind'] == 'coverage':
            # Related unit exercises aid review; coverage itself remains separate from solving evidence.
            nodes[edge['target']]['exercise_ids'] = list(nodes[edge['source']]['exercise_ids'])
    return {'nodes': list(nodes.values()), 'edges': list(edges.values()), 'exercises': list(exercises.values())}


def view(owner, record_id=None):
    saved = learning.status(owner, record_id)
    current = learning.evidence(owner)
    entries = None
    if not record_id:
        entries = db.all('SELECT * FROM knowledge_entries WHERE owner=? ORDER BY created_at,node_id', (owner,))
        contexts = {r['id'] for r in db.all('SELECT id FROM contexts WHERE owner=?', (owner,))}
        for entry in entries:
            catalog = CATALOG.get(entry['unit_id'])
            entry['source_available'] = entry['context_id'] in contexts if entry['context_id'] else bool(
                catalog and catalog['version'] == entry['version'])
        keys = {entry['node_id'] for entry in entries}
        live = {item['id']: item for item in current}
        saved = {**saved, 'exercises': [e for e in saved['exercises'] if exercise_node(e, live.get(e['id'], {})) in keys]}
        current = [e for e in current if exercise_node(e, e) in keys]
    # Legacy AI summaries remain in dated records; the current graph uses persisted concept IDs.
    graph = build(saved if record_id else {**saved, 'concepts': []}, current, historical=bool(record_id), entries=entries)
    if not record_id:
        graph = ontology.extend_graph(owner, graph)
    return {**saved, **graph}
