"""Curated document -> reviewed incremental wiki -> cited answers contracts."""
import io
import json
import unittest
import zipfile
import httpx
from unittest.mock import patch
from . import ai, db, service, test_app, wiki


class WikiTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def document(self, **changes):
        data = {'id': service.uid(), 'revision': 0, 'title': '배포 메모',
                'body': '외장 SSD가 연결되어야 배포할 수 있다.', 'source_ids': [], **changes}
        result = self.client.post('/api/wiki/documents', json=data)
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()

    def compilation(self, document, slug='deployment', revision=0):
        return {'summary': '배포 문서를 기존 위키에 통합', 'pages': [{
            'slug': slug, 'revision': revision, 'title': '배포 구조', 'summary': 'SSD를 확인한다.',
            'body': document['body'], 'citations': [{'document_id': document['id'], 'revision': document['revision'],
                                                    'quote': document['body']}], 'links': []}]}

    def start(self, kind, result, documents=(), question='', request_id=None):
        payload = {'request_id': request_id or service.uid(), 'kind': kind, 'question': question,
                   'documents': [{'id': d['id'], 'revision': d['revision']} for d in documents]}
        model = wiki.WikiCompilation if kind == 'ingest' else wiki.WikiAnswer
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'generate', return_value=model.model_validate(result)) as generate:
            response = self.client.post('/api/wiki/jobs', json=payload)
            self.assertEqual(response.status_code, 202, response.text)
        job = self.client.get('/api/wiki/jobs/' + response.json()['id']).json()
        return job, generate

    def apply(self, job, result):
        return self.client.post('/api/wiki/jobs/' + job['id'] + '/apply', json=result)

    def seed(self):
        doc = self.document()
        result = self.compilation(doc)
        job, _ = self.start('ingest', result, [doc])
        self.assertEqual(job['state'], 'ready', job)
        self.assertEqual(self.apply(job, result).status_code, 200)
        return doc, result, job

    def test_curated_document_preserves_raw_snapshot_and_versions(self):
        raw = self.client.post('/api/project-brain/sources', json={
            'id': service.uid(), 'kind': 'excerpt', 'title': '원문', 'body': '수정하지 않는 원문'}).json()
        doc = self.document(source_ids=[raw['id']])
        changed = self.document(id=doc['id'], revision=1, body='사용자가 수정하고 보완한 내용', source_ids=[raw['id']])
        self.assertEqual(changed['revision'], 2)
        self.assertEqual(self.client.get(f"/api/wiki/documents/{doc['id']}?revision=1").json()['body'], doc['body'])
        self.assertEqual(self.client.get('/api/project-brain/sources/' + raw['id']).json()['body'], '수정하지 않는 원문')
        self.assertEqual(self.client.post('/api/wiki/documents', json={
            'id': doc['id'], 'revision': 1, 'title': '오래된 수정', 'body': '덮어쓰기'}).status_code, 409)
        self.assertEqual(self.client.post('/api/wiki/documents', json={
            'id': service.uid(), 'revision': 0, 'title': ' ', 'body': ' '} ).status_code, 422)
        self.assertEqual(self.client.get('/api/wiki/pages').json(), [])

    def test_document_accepts_all_twenty_sources_supported_by_legacy_records(self):
        identifiers = []
        for _ in range(20):
            source = self.client.post('/api/project-brain/sources', json={
                'id': service.uid(), 'kind': 'excerpt', 'title': '기존 근거', 'body': '이전에 보존한 원문'}).json()
            identifiers.append(source['id'])
        doc = self.document(source_ids=identifiers)
        self.assertEqual(doc['source_ids'], identifiers)

    def test_incremental_compile_reads_existing_wiki_and_only_applies_after_review(self):
        first, _, _ = self.seed()
        second = self.document(title='추가 조건', body='배포 전에 백업을 수행한다.')
        result = self.compilation(second, revision=1)
        result['pages'][0]['body'] = first['body'] + '\n\n' + second['body']
        result['pages'][0]['citations'].append({'document_id': first['id'], 'revision': 1, 'quote': first['body']})
        job, generate = self.start('ingest', result, [second])
        snapshot = generate.call_args.args[2]
        self.assertEqual(snapshot['pages'][0]['slug'], 'deployment')
        self.assertEqual(len(snapshot['evidence']), 2)
        self.assertEqual(self.client.get('/api/wiki/pages/deployment').json()['revision'], 1)
        self.assertEqual(job['before'][0]['revision'], 1)
        result['pages'][0]['title'] = '검토해서 보완한 제목'
        applied = self.apply(job, result)
        self.assertEqual(applied.status_code, 200, applied.text)
        self.assertEqual(applied.json()['state'], 'applied')
        self.assertEqual(self.apply(job, result).status_code, 200)
        self.assertEqual(len(self.client.get('/api/wiki/pages').json()), 1)
        page = self.client.get('/api/wiki/pages/deployment').json()
        self.assertEqual((page['title'], page['revision']), ('검토해서 보완한 제목', 2))
        self.assertEqual(self.client.get('/api/wiki/pages/deployment?revision=1').json()['body'], first['body'])
        result['pages'][0]['body'] = '이미 반영한 요청 변경'
        self.assertEqual(self.apply(job, result).status_code, 409)

    def test_stale_document_or_wiki_rejects_all_changes(self):
        doc = self.document()
        result = self.compilation(doc)
        pending, _ = self.start('ingest', result, [doc])
        other, _ = self.start('ingest', result, [doc])
        self.assertEqual(self.apply(other, result).status_code, 200)
        self.assertEqual(self.apply(pending, result).status_code, 409)
        result = self.compilation(doc, revision=1)
        pending, _ = self.start('ingest', result, [doc])
        self.document(id=doc['id'], revision=1, body='다시 검토하고 변경한 문서')
        self.assertEqual(self.apply(pending, result).status_code, 409)
        self.assertEqual(self.client.get('/api/wiki/pages/deployment').json()['revision'], 1)
        self.assertEqual(self.client.get('/api/wiki/inspection').json()[0]['kind'], 'stale-document')

    def test_invalid_citations_unknown_links_and_dropped_selected_documents_fail(self):
        doc = self.document()
        bad = self.compilation(doc)
        bad['pages'][0]['citations'][0]['quote'] = '존재하지 않는 문구'
        job, _ = self.start('ingest', bad, [doc])
        self.assertEqual(job['state'], 'failed')
        result = self.compilation(doc)
        bad = json.loads(json.dumps(result))
        bad['pages'][0]['links'] = ['unknown']
        job, _ = self.start('ingest', bad, [doc])
        self.assertEqual(job['state'], 'failed')
        another = self.document(body='새로운 자료')
        job, _ = self.start('ingest', result, [doc, another])
        self.assertEqual(job['state'], 'failed')
        ready, _ = self.start('ingest', result, [doc])
        result['pages'].append({**result['pages'][0], 'slug': 'other', 'links': ['unknown']})
        self.assertEqual(self.apply(ready, result).status_code, 422)
        self.assertEqual(self.client.get('/api/wiki/pages').json(), [])

    def test_query_is_cited_to_versioned_wiki_and_answer_can_be_curated(self):
        doc, _, _ = self.seed()
        answer = {'answer': '배포 전에 SSD 연결을 확인해야 합니다.', 'insufficient': False,
                  'citations': [{'slug': 'deployment', 'revision': 1, 'quote': doc['body']}]}
        job, generate = self.start('query', answer, question='배포 조건은?')
        self.assertEqual(job['state'], 'ready')
        self.assertNotIn('evidence', generate.call_args.args[2])
        saved = self.document(title='질문에서 발견한 내용', body=answer['answer'], origin_job=job['id'])
        self.assertEqual(saved['origin_job'], job['id'])
        answer['citations'][0]['quote'] = '알 수 없는 인용'
        invalid, _ = self.start('query', answer, question='배포 조건은?')
        self.assertEqual(invalid['state'], 'failed')
        answer = {'answer': '이 위키에는 답할 근거가 없습니다.', 'insufficient': True, 'citations': []}
        unknown, _ = self.start('query', answer, question='다른 질문')
        self.assertEqual(unknown['state'], 'ready')

    def test_jobs_idempotency_interruption_and_owner_boundaries(self):
        doc = self.document()
        request = wiki.JobInput(request_id='same-request', kind='ingest', documents=[wiki.DocumentRef(id=doc['id'], revision=1)])
        with patch.object(ai, 'available', return_value=True):
            first, fresh = wiki.begin(self.owner, request)
            same, repeated = wiki.begin(self.owner, request)
            self.assertTrue(fresh)
            self.assertFalse(repeated)
            self.assertEqual(first['id'], same['id'])
            with self.assertRaises(service.Error):
                wiki.begin(self.owner, request.model_copy(update={'kind': 'query', 'documents': [], 'question': '질문'}))
        service.initialize()
        self.assertEqual(wiki.job(self.owner, first['id'])['state'], 'interrupted')
        db.execute("INSERT INTO users VALUES ('other','other','unused',0)")
        for call in [lambda: wiki.document('other', doc['id']), lambda: wiki.job('other', first['id']),
                     lambda: wiki.apply('other', first['id'], wiki.WikiCompilation.model_validate(self.compilation(doc)))]:
            with self.assertRaises(service.Error):
                call()
        self.assertEqual(wiki.documents('other'), [])
        self.assertEqual(wiki.pages('other'), [])
        self.assertEqual(wiki.jobs('other'), [])
        self.assertEqual(self.client.post('/api/wiki/documents', json={
            'id': service.uid(), 'revision': 0, 'title': '실패', 'body': '내용', 'source_ids': [service.uid()]}).status_code, 404)

    def test_connected_pages_lint_and_portable_markdown_export(self):
        doc = self.document()
        result = self.compilation(doc)
        result['pages'][0]['links'] = ['storage']
        result['pages'].append({**result['pages'][0], 'slug': 'storage', 'title': '외장 SSD', 'links': ['deployment']})
        job, _ = self.start('ingest', result, [doc])
        self.assertEqual(self.apply(job, result).status_code, 200)
        self.assertEqual(self.client.get('/api/wiki/pages/storage').json()['backlinks'][0]['slug'], 'deployment')
        report, _ = self.start('lint', {'answer': '문서 간 연결이 있습니다.', 'insufficient': False,
            'citations': [{'slug': 'storage', 'revision': 1, 'quote': doc['body']}]})
        self.assertEqual(report['state'], 'ready')
        exported = self.client.get('/api/wiki/export')
        self.assertEqual(exported.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
            self.assertIn('AGENTS.md', archive.namelist())
            self.assertIn('index.md', archive.namelist())
            self.assertIn('wiki/deployment.md', archive.namelist())
            self.assertIn(f"documents/{doc['id']}-v1.md", archive.namelist())
            self.assertIn('lint', archive.read('log.md').decode())
            self.assertIn('storage.md', archive.read('wiki/deployment.md').decode())

    def test_wiki_provider_prompt_and_structured_output_for_non_programming_documents(self):
        doc = self.document(title='읽은 책', body='인물의 선택은 앞선 사건의 영향을 받는다.')
        client = httpx.Client
        outputs = [self.compilation(doc), {'answer': '관련 문서가 더 필요합니다.', 'insufficient': True, 'citations': []}]
        for model, output in zip((wiki.WikiCompilation, wiki.WikiAnswer), outputs):
            def handle(request):
                payload = json.loads(request.content)
                prompt = payload['messages'][0]['content']
                self.assertIn('personal LLM wiki', prompt)
                self.assertNotIn('unrelated to the selected language', prompt)
                self.assertNotIn('No network, filesystem dependencies', prompt)
                self.assertEqual(payload['response_format']['json_schema']['name'], model.__name__)
                return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({'data': output, 'error': ''})}}]})
            with patch.object(ai.httpx, 'Client', side_effect=lambda **kwargs: client(transport=httpx.MockTransport(handle), **kwargs)):
                generated = ai._generate(model, 'Use supplied sources.', {}, connection={
                    'model': 'test-model', 'api_key': 'test-only', 'provider_url': 'https://example.test'})
            self.assertEqual(generated.model_dump(), output)


if __name__ == '__main__':
    unittest.main()
