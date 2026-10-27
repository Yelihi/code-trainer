"""Explicit registration of reviewed material through the shared ontology transaction."""
import json
from . import db, materials, ontology, practice_records, service


def register(owner, review_id, request):
    payload = service.dump({'review_id': review_id, **request.model_dump()})
    with db.connect(write=True) as c:
        receipt = c.execute('SELECT payload FROM knowledge_registrations WHERE owner=? AND request_id=?', (owner, request.request_id)).fetchone()
        if receipt:
            if receipt['payload'] != payload: raise service.Error('같은 등록 요청의 내용이 달라졌습니다.', 409)
        else:
            material = materials.detail(owner, review_id)
            if material['revision'] != request.revision or material['state'] != 'eligible':
                raise service.Error('자료가 변경되거나 보관되었습니다. 최신 자료를 다시 확인해주세요.', 409)
            latest = c.execute('SELECT * FROM material_proposals WHERE owner=? AND review_id=? ORDER BY created_at DESC,id DESC LIMIT 1', (owner, review_id)).fetchone()
            if not latest or latest['id'] != request.proposal_id or latest['state'] != 'ready':
                raise service.Error('현재 자료의 최신 후보 추출·검토를 완료해주세요.', 409)
            review = json.loads(latest['data'])['review']
            if review['issues']: raise service.Error('본문의 수정·확인 사항이 남아 있습니다. 새 자료를 저장하고 다시 검토해주세요.', 409)
            if material['registration']:
                raise service.Error('이 자료 버전은 이미 등록되었습니다.', 409)
            if any(item.basis == 'source' for item in [*request.data.concepts, *request.data.assertions]):
                raise service.Error('해석·작성분의 근거는 해석 또는 질문으로 구분해주세요.', 422)
            record = practice_records.version(owner, material['origin_id'], material['revision']) if material['kind'] == 'practice' else None
            if record and any(not any(item.quote in text for text in [*record['answers'].values(), record['summary']])
                              for item in [*request.data.concepts, *request.data.assertions]):
                raise service.Error('근거는 화면의 제목이 아니라 직접 작성한 답변이나 요약에서 선택해주세요.', 422)
            ontology.validate_proposal(owner, request.data, material['body'])
            identifier = service.uid()
            metadata = {k: material[k] for k in ('authorship','resource_id','raw_revision','interpretation_id')}
            metadata['review_id'] = review_id
            c.execute('INSERT INTO knowledge_sources VALUES (?,?,?,?,?,?,?,?,?,?)',
                      (owner, identifier, material['kind'], material['origin_id'], material['revision'], material['title'],
                       material['body'], service.dump(metadata), 'active', service.now()))
            concepts = ontology.register(c, owner, identifier, material['body'], request.data)
            provenance = dict(actor='user', proposal_id=latest['id'], model=latest['model'], prompt_version=latest['prompt_version'], review=review)
            c.execute('INSERT INTO knowledge_registrations VALUES (?,?,?,?,?,?)',
                      (owner, request.request_id, identifier, payload, service.dump(provenance), service.now()))
            if material['kind'] == 'practice':
                for concept in concepts:
                    c.execute('INSERT INTO learning_observations VALUES (?,?,?,?,?,?,?)',
                              (owner, service.uid(), concept, None, 'self_explanation',
                               service.dump(dict(material_review_id=review_id, source_id=identifier, mastery=None)), record['updated_at']))
    return materials.detail(owner, review_id)
