"""Immutable interpretation provenance for the existing code generation pipeline."""
from . import db, interpretations


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS code_origins (
        generation_id TEXT PRIMARY KEY REFERENCES generations(id) ON DELETE CASCADE,
        interpretation_id TEXT NOT NULL REFERENCES interpretations(id), section_id TEXT NOT NULL,
        language TEXT NOT NULL, difficulty TEXT NOT NULL, content TEXT NOT NULL)''')


def selection(owner, identifier, section_id):
    from . import service
    document = interpretations.view(owner, identifier)
    if document['state'] != 'ready' or not document['document']:
        raise service.Error('완료된 해석에서 코드 실습을 시작해주세요.', 409)
    section = next((s for s in document['document']['sections'] if s['id'] == section_id), None)
    if not section:
        raise service.Error('해석 섹션을 찾을 수 없습니다.', 404)
    return dict(interpretation_id=identifier, resource_id=document['resource_id'], revision=document['revision'],
                current_revision=document['current_revision'], source_name=document['source_name'],
                section_id=section_id, title=section['title'], section=section)


def material(selected):
    s = selected['section']
    return '\n\n'.join([f"# {s['title']}",
        '## 원문 근거 · 저장된 본문 v' + str(selected['revision']), *s['source_quotes'],
        '## AI 해석 · 원문과 구별해서 검토', s['body'],
        '## AI가 덧붙인 예시 · 원문 직접 인용이 아님', *s['examples'],
        '## AI가 제안한 확인 질문', *s['questions']])


def replay(c, generation_id, request):
    from . import service
    row = c.execute('SELECT * FROM code_origins WHERE generation_id=?', (generation_id,)).fetchone()
    if row or request.source_kind == 'interpretation':
        if not row or request.source_kind != 'interpretation' or tuple(row[k] for k in ('interpretation_id','section_id','language','difficulty')) != (request.interpretation_id,request.section_id,request.language,request.difficulty):
            raise service.Error('같은 요청 ID의 해석 섹션 또는 실습 설정이 달라졌습니다.', 409)


def origin(owner, context_id):
    row = db.one('''SELECT o.interpretation_id,o.section_id,i.resource_id,i.revision,i.source_name
        FROM code_origins o JOIN generations g ON g.id=o.generation_id
        JOIN interpretations i ON i.id=o.interpretation_id AND i.owner=g.owner
        WHERE g.owner=? AND g.context_id=?''', (owner, context_id))
    return row


def listing(owner, identifier, section_id):
    from . import diagnostics
    selected = selection(owner, identifier, section_id)
    selected.pop('section')
    rows = db.all('''SELECT g.id,g.state,g.stage,g.context_id,g.set_id,g.unit_id,g.error,g.events,g.created_at,o.language,o.difficulty
        FROM code_origins o JOIN generations g ON g.id=o.generation_id
        WHERE g.owner=? AND o.interpretation_id=? AND o.section_id=? ORDER BY g.created_at DESC,g.id DESC LIMIT 20''',
        (owner, identifier, section_id))
    return dict(source=selected, items=[diagnostics.view(r) for r in rows])
