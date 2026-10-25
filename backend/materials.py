"""Explicit review of immutable learning versions, independent of AI and scheduling."""
from . import db, service, interpretations, worksheets, practice_records, resources


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS material_reviews (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id),
        kind TEXT NOT NULL CHECK(kind IN ('interpretation','practice')), origin_id TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(revision>0), created_at TEXT NOT NULL,
        UNIQUE(owner,kind,origin_id,revision))''')
    c.execute('CREATE INDEX IF NOT EXISTS material_reviews_history ON material_reviews(owner,created_at DESC,id DESC)')


def read(owner, kind, origin_id, revision):
    if kind == 'interpretation':
        source = interpretations.view(owner, origin_id)
        if source['state'] != 'ready' or not source['document']:
            raise service.Error('완료된 해석을 선택해주세요.', 409)
        if revision != source['revision']:
            raise service.Error('해석의 원문 버전이 다릅니다.', 409)
        document = source['document']
        parts = [document['summary'], '## AI가 정리한 핵심 개념', *document['concepts']]
        for s in document['sections']:
            parts.extend(['## ' + s['title'], s['body'], '### 인용한 원문 근거', *s['source_quotes']])
            for label, key in [('AI 예시', 'examples'), ('AI 확장', 'extensions'), ('스스로 확인할 질문', 'questions')]:
                if s[key]: parts.extend(['### ' + label, *s[key]])
        body, title, authorship, current = '\n\n'.join(parts), document['title'], 'ai', revision
        interpretation_id = origin_id
        has_content = bool(body.strip())
    elif kind == 'practice':
        source = worksheets.view(owner, origin_id)
        if source['state'] != 'ready' or not source['document']:
            raise service.Error('준비된 질문지의 작성분을 선택해주세요.', 409)
        record = practice_records.version(owner, origin_id, revision)
        current = db.one('SELECT MAX(revision) revision FROM practice_record_versions WHERE owner=? AND worksheet_id=?', (owner, origin_id))['revision']
        # Only learner text is evidence; AI questions remain linked through the worksheet.
        parts = []
        for index, q in enumerate(source['document']['questions']):
            if record['answers'].get(q['id'], '').strip():
                parts.extend([f'## 내 답변 {index + 1}', record['answers'][q['id']]])
        if record['summary'].strip(): parts.extend(['## 내 말로 쓴 요약', record['summary']])
        body, title, authorship = '\n\n'.join(parts), source['document']['title'], 'user'
        interpretation_id = source['interpretation_id']
        has_content = bool(body.strip())
    else:
        raise service.Error('학습 자료 종류를 확인해주세요.', 422)
    raw = resources.view(owner, source['resource_id'])
    state, reason = 'eligible', ''
    if raw['archived']:
        state, reason = 'archived', '원문이 보관되어 있습니다. 복원 후 내용을 다시 확인해주세요.'
    elif current != revision or raw['revision'] != source['revision']:
        state, reason = 'stale', '원문 또는 내 작성분이 변경되었습니다. 최신 자료를 다시 검토해주세요.'
    elif not has_content:
        state, reason = 'empty', '확인할 답변이나 요약을 먼저 작성하고 저장해주세요.'
    return dict(kind=kind, origin_id=origin_id, revision=revision, current_revision=current, title=title,
                authorship=authorship, body=body, state=state, reason=reason, interpretation_id=interpretation_id,
                resource_id=source['resource_id'], raw_revision=source['revision'], source_name=source['source_name'])


def status(owner, kind, origin_id, revision):
    material = read(owner, kind, origin_id, revision)
    material.pop('body')
    review = db.one('SELECT id,created_at FROM material_reviews WHERE owner=? AND kind=? AND origin_id=? AND revision=?', (owner, kind, origin_id, revision))
    return dict(material=material, review=review)


def detail(owner, identifier):
    row = db.one('SELECT * FROM material_reviews WHERE owner=? AND id=?', (owner, identifier))
    if not row:
        raise service.Error('검토한 자료를 찾을 수 없습니다.', 404)
    return dict(read(owner, row['kind'], row['origin_id'], row['revision']), id=row['id'], reviewed_at=row['created_at'])


def mark(owner, kind, origin_id, revision):
    with db.connect(write=True) as c:
        previous = c.execute('SELECT id FROM material_reviews WHERE owner=? AND kind=? AND origin_id=? AND revision=?', (owner, kind, origin_id, revision)).fetchone()
        if previous:
            identifier = previous['id']
        else:
            material = read(owner, kind, origin_id, revision)
            if material['state'] != 'eligible':
                raise service.Error(material['reason'], 409)
            identifier = service.uid()
            c.execute('INSERT INTO material_reviews VALUES (?,?,?,?,?,?)', (identifier, owner, kind, origin_id, revision, service.now()))
    return detail(owner, identifier)


def listing(owner, page):
    total = db.one('SELECT COUNT(*) n FROM material_reviews WHERE owner=?', (owner,))['n']
    pages = max(1, (total + 19) // 20)
    page = min(page, pages)
    rows = db.all('SELECT id FROM material_reviews WHERE owner=? ORDER BY created_at DESC,id DESC LIMIT 20 OFFSET ?', (owner, (page - 1) * 20))
    items = []
    for row in rows:
        item = detail(owner, row['id'])
        item.pop('body')
        items.append(item)
    return dict(items=items, total=total, page=page, pages=pages)
