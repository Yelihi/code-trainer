"""Owner-checked learning targets shared by questions, recommendations and references."""
import json
import re
from typing import Literal
from pydantic import Field
from .schema import Model
from . import db, service


class Target(Model):
    kind: Literal['resource', 'note', 'course', 'unit', 'exercise', 'interpretation', 'worksheet', 'reference', 'review', 'problem', 'question', 'foundation', 'material_review', 'note_review']
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,100}$')
    unit_id: str = Field(default='', max_length=100)


def resolve(owner, target, c=None):
    if c is None:
        with db.connect() as connection:
            return resolve(owner, target, connection)
    kind, identifier = target.kind, target.id
    row = None
    revision = None
    if kind == 'question':
        row = c.execute('SELECT text AS title,revision FROM question_memos WHERE owner=? AND id=?', (owner, identifier)).fetchone()
        href = '/questions/' + identifier
    elif kind == 'foundation':
        from . import foundations
        item = foundations.lesson(identifier)
        row = {'title': item['title'], 'revision': item['version']}
        href = '/foundations/' + identifier + ('/practice' if target.unit_id == 'practice' else '')
    elif kind == 'material_review':
        item = c.execute('SELECT snapshot,revision FROM spaced_reviews WHERE owner=? AND id=?', (owner, identifier)).fetchone()
        row = {'title': json.loads(item['snapshot'])['title'], 'revision': item['revision']} if item else None
        href = '/reviews/material/' + identifier
    elif kind == 'note_review':
        row = c.execute('SELECT n.title,r.revision FROM reference_reviews r JOIN reference_notes n ON n.owner=r.owner AND n.id=r.note_id WHERE r.owner=? AND r.id=?', (owner, identifier)).fetchone()
        href = '/reference-reviews/' + identifier
    elif kind == 'resource':
        row = c.execute('''SELECT v.name AS title,v.revision FROM resources r JOIN resource_versions v
            ON v.owner=r.owner AND v.resource_id=r.id WHERE r.owner=? AND r.id=? AND r.archived=0 ORDER BY v.revision DESC LIMIT 1''', (owner, identifier)).fetchone()
        href = '/library/' + identifier
    elif kind == 'note':
        row = c.execute('SELECT title,revision FROM reference_notes WHERE owner=? AND id=? AND archived=0', (owner, identifier)).fetchone()
        href = '/references/' + identifier
    elif kind in ('course', 'unit'):
        context = c.execute('SELECT data FROM contexts WHERE owner=? AND id=?', (owner, identifier)).fetchone()
        href = '/learn/' + identifier
        if context:
            data = json.loads(context['data'])
            row = {'title': data['title']}
            if kind == 'unit':
                unit = next((unit for unit in data['units'] if unit['id'] == target.unit_id), None)
                row = {'title': unit['title']} if unit else None
                href += '/units/' + target.unit_id
    elif kind == 'exercise':
        item = c.execute('''SELECT e.data,e.set_id FROM exercises e JOIN sets s ON s.id=e.set_id JOIN contexts c ON c.id=s.context_id
            WHERE c.owner=? AND e.id=? AND s.withdrawn=0''', (owner, identifier)).fetchone()
        href = f"/practice/{item['set_id']}?exercise={identifier}" if item else ''
        row = {'title': json.loads(item['data'])['title']} if item else None
    elif kind == 'interpretation':
        item = c.execute("SELECT source_name,attempt FROM interpretations WHERE owner=? AND id=? AND archived=0", (owner, identifier)).fetchone()
        row = {'title': item['source_name'], 'revision': item['attempt']} if item else None
        href = '/interpretations/' + identifier
    elif kind == 'worksheet':
        item = c.execute('SELECT * FROM worksheets WHERE owner=? AND id=?', (owner, identifier)).fetchone()
        row = {'title': json.loads(item['data'])['title']} if item and item['data'] else None
        href = '/worksheets/' + identifier
    elif kind == 'reference':
        row = c.execute('SELECT title,revision FROM technical_references WHERE owner=? AND id=?', (owner, identifier)).fetchone()
        href = '/technical-references/' + identifier
    elif kind == 'review':
        item = c.execute('SELECT exercise_id FROM review_sessions WHERE owner=? AND id=?', (owner, identifier)).fetchone()
        row = resolve(owner, Target(kind='exercise', id=item['exercise_id']), c) if item else None
        href = '/reviews/' + identifier
    else:
        item = c.execute('SELECT v.data,p.revision FROM manual_problems p JOIN manual_problem_versions v ON v.problem_id=p.id AND v.revision=p.revision WHERE p.owner=? AND p.id=? AND p.archived=0', (owner, identifier)).fetchone()
        row = {'title': json.loads(item['data'])['title'], 'revision': item['revision']} if item else None
        href = '/problem-books/problems/' + identifier + '/solve'
    if not row:
        raise service.Error('연결할 학습 기록을 찾을 수 없습니다.', 404)
    if 'revision' in row.keys():
        revision = row['revision']
    return {**target.model_dump(), 'title': row['title'], 'href': href, 'revision': revision}


def from_path(owner, path):
    path = path.split('#')[0]
    match = re.fullmatch(r'/foundations/([a-zA-Z0-9_-]{1,100})(/practice)?', path)
    if match:
        return resolve(owner, Target(kind='foundation', id=match[1], unit_id='practice' if match[2] else ''))
    match = re.fullmatch(r'/reviews/material/([a-f0-9]{32})', path)
    if match:
        return resolve(owner, Target(kind='material_review', id=match[1]))
    match = re.fullmatch(r'/interpretations/([a-f0-9]{32})/code/(s[1-6])', path)
    if match:
        return resolve(owner, Target(kind='interpretation', id=match[1]))
    match = re.fullmatch(r'/learn/([a-f0-9]{32})/units/([^/?]{1,100})', path)
    if match:
        return resolve(owner, Target(kind='unit', id=match[1], unit_id=match[2]))
    match = re.fullmatch(r'/practice/([a-f0-9]{32})(?:\?exercise=([a-f0-9]{32}))?', path)
    if match:
        exercise = db.one('SELECT id FROM exercises WHERE set_id=? ORDER BY rowid LIMIT 1', (match[1],))
        return resolve(owner, Target(kind='exercise', id=match[2] or exercise['id'])) if exercise else None
    routes = {'library': 'resource', 'references': 'note', 'learn': 'course', 'interpretations': 'interpretation',
              'worksheets': 'worksheet', 'technical-references': 'reference', 'reviews': 'review', 'reference-reviews': 'note_review', 'questions': 'question'}
    match = re.fullmatch(r'/([a-z-]+)/([a-f0-9]{32})(?:/practice)?', path)
    if match and match[1] in routes:
        return resolve(owner, Target(kind=routes[match[1]], id=match[2]))
    match = re.fullmatch(r'/problem-books/problems/([a-f0-9]{32})/solve', path)
    return resolve(owner, Target(kind='problem', id=match[1])) if match else None


def listing(owner, query):
    result = []
    for row in db.all('''SELECT r.id, v.name FROM resources r JOIN resource_versions v ON v.owner=r.owner AND v.resource_id=r.id
        WHERE r.owner=? AND r.archived=0 AND v.revision=(SELECT MAX(revision) FROM resource_versions WHERE owner=r.owner AND resource_id=r.id)
        AND v.name LIKE ? ORDER BY v.created_at DESC LIMIT 15''', (owner, '%' + query + '%')):
        result.append(resolve(owner, Target(kind='resource', id=row['id'])))
    for row in db.all("SELECT id FROM contexts WHERE owner=? AND json_extract(data,'$.title') LIKE ? ORDER BY created_at DESC LIMIT 10", (owner, '%' + query + '%')):
        result.append(resolve(owner, Target(kind='course', id=row['id'])))
    for row in db.all('SELECT id FROM technical_references WHERE owner=? AND title LIKE ? ORDER BY updated_at DESC LIMIT 10', (owner, '%' + query + '%')):
        result.append(resolve(owner, Target(kind='reference', id=row['id'])))
    return result


def related_questions(owner, path):
    target = from_path(owner, path)
    if not target:
        return []
    targets = [target]
    if target['kind'] == 'reference':
        targets += json.loads(db.one('SELECT targets FROM technical_references WHERE owner=? AND id=?', (owner, target['id']))['targets'])
    conditions, params = [], [owner]
    for item in targets:
        conditions.append("EXISTS(SELECT 1 FROM json_each(q.targets) t WHERE json_extract(t.value,'$.kind')=? AND json_extract(t.value,'$.id')=? AND json_extract(t.value,'$.unit_id')=?)")
        params.extend((item['kind'], item['id'], item['unit_id']))
        if item['kind'] == 'resource':
            conditions.append("EXISTS(SELECT 1 FROM json_each(q.links) l WHERE json_extract(l.value,'$.resource_id')=?)")
            params.append(item['id'])
        if item['kind'] == 'note':
            conditions.append('q.note_id=?')
            params.append(item['id'])
    return db.all('SELECT DISTINCT q.id,q.text,q.status,q.updated_at FROM question_memos q WHERE q.owner=? AND (' + ' OR '.join(conditions) + ') ORDER BY q.updated_at DESC,q.id LIMIT 20', params)
