"""Project brain ownership, provenance, state and explicit AI contracts."""
import unittest
import httpx
from unittest.mock import patch
from . import ai, db, github_sharing, project_brain, resources, service, test_app
from .project_brain import BrainDraft, SourceInput
from .resource_schema import ResourceInput


class ProjectBrainTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def source(self, body='원본: 실패한 해석은 같은 기록에서 재시도한다.'):
        response = self.client.post('/api/project-brain/sources', json={
            'id': service.uid(), 'kind': 'excerpt', 'title': '작업 발췌', 'body': body})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def record(self, source):
        response = self.client.post('/api/project-brain/records', json={
            'id': service.uid(), 'revision': 0, 'kind': 'decision', 'title': '같은 항목에서 재시도',
            'summary': '해석 재시도는 기존 기록의 시도를 갱신한다.', 'body': '원본 버전을 유지한다.',
            'claims': [{'text': '사용자가 같은 기록의 재시도를 요청했다.', 'attribution': 'user_statement',
                        'source_id': source['id'], 'quote': '실패한 해석은 같은 기록에서 재시도한다.'}]})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_source_snapshot_record_versions_graph_and_export(self):
        raw = resources.register(self.owner, ResourceInput(request_id=service.uid(), kind='text',
            name='원자료', content='첫 번째 본문과 근거'))
        response = self.client.post('/api/project-brain/sources', json={
            'id': service.uid(), 'kind': 'resource', 'resource_id': raw['id'], 'revision': 1})
        self.assertEqual(response.status_code, 200, response.text)
        source = response.json()
        self.assertEqual(source['body'], '첫 번째 본문과 근거')
        resources.register(self.owner, ResourceInput(request_id=service.uid(), resource_id=raw['id'], revision=1,
            kind='text', name='변경', content='두 번째 본문'))
        self.assertEqual(self.client.get('/api/project-brain/sources/' + source['id']).json()['body'], '첫 번째 본문과 근거')
        record = self.record(self.source())
        self.assertEqual(record['review'], 'unreviewed')
        self.assertEqual(self.client.post(f"/api/project-brain/records/{record['id']}/confirm", json={'revision': 1}).json()['review'], 'confirmed')
        update = {key: record[key] for key in ('id', 'revision', 'kind', 'title', 'summary', 'body', 'claims')}
        update['title'] = '수정한 결정'
        self.assertEqual(self.client.post('/api/project-brain/records', json=update).json()['review'], 'unreviewed')
        self.assertEqual(self.client.get(f"/api/project-brain/records/{record['id']}?revision=1").json()['title'], '같은 항목에서 재시도')
        self.assertEqual(self.client.post('/api/project-brain/records', json=update).status_code, 409)
        other = self.record(self.source('원본: 실패한 해석은 같은 기록에서 재시도한다. 두 번째 요청'))
        self.assertEqual(self.client.post(f"/api/project-brain/records/{other['id']}/links", json={
            'target_id': record['id'], 'kind': 'supersedes', 'reason': '새 결정으로 바뀌었다.'}).status_code, 200)
        self.assertEqual(self.client.get(f"/api/project-brain/records/{record['id']}").json()['lifecycle'], 'superseded')
        graph = self.client.get('/api/project-brain/graph').json()
        self.assertTrue(any(edge['kind'] == 'supersedes' for edge in graph['edges']))
        self.assertTrue(any(edge['kind'] == 'evidence' for edge in graph['edges']))
        exported = self.client.get(f"/api/project-brain/records/{record['id']}/export")
        self.assertIn('실패한 해석은 같은 기록에서 재시도한다.', exported.text)
        self.assertIn('review: unreviewed', exported.text)
        self.client.post(f"/api/project-brain/records/{record['id']}/archive", json={'archived': True})
        self.assertFalse(any(item['id'] == record['id'] for item in self.client.get('/api/project-brain/records').json()))
        self.assertTrue(any(item['id'] == record['id'] for item in self.client.get('/api/project-brain/records?archived=true').json()))

    def test_quote_validation_and_owner_isolation(self):
        source = self.source()
        body = {'id': service.uid(), 'revision': 0, 'kind': 'observation', 'title': '관찰', 'summary': '요약',
                'body': '본문', 'claims': [{'text': '없는 인용', 'attribution': 'observed',
                                      'source_id': source['id'], 'quote': '존재하지 않는 문장'}]}
        self.assertEqual(self.client.post('/api/project-brain/records', json=body).status_code, 422)
        record = self.record(source)
        db.execute("INSERT INTO users VALUES ('other','other','unused',0)")
        with self.assertRaises(service.Error):
            project_brain.source_view('other', source['id'])
        with self.assertRaises(service.Error):
            project_brain.record_view('other', record['id'])
        self.assertEqual(project_brain.records('other'), [])
        self.assertEqual(project_brain.graph('other'), {'nodes': [], 'edges': []})
        with self.assertRaises(service.Error):
            project_brain.link('other', record['id'], project_brain.LinkInput(target_id=service.uid(), kind='related', reason='연결'))

    def test_requested_ai_draft_is_not_saved_or_confirmed_automatically(self):
        source = self.source()
        draft = {'kind': 'decision', 'title': '재시도', 'summary': '같은 기록에서 다시 시도', 'body': '기존 ID를 유지한다.',
                 'claims': [{'text': '사용자 요청', 'attribution': 'user_statement', 'source_id': source['id'],
                             'quote': '실패한 해석은 같은 기록에서 재시도한다.'}]}
        body = {'request_id': 'draft-request', 'source_ids': [source['id']]}
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'generate', return_value=BrainDraft.model_validate(draft)) as generate:
            response = self.client.post('/api/project-brain/drafts', json=body)
            self.assertEqual(response.status_code, 202, response.text)
            identifier = response.json()['id']
            self.assertEqual(generate.call_count, 1)
            self.assertEqual(self.client.get('/api/project-brain/drafts/' + identifier).json()['state'], 'ready')
            self.assertEqual(self.client.post('/api/project-brain/drafts', json=body).json()['id'], identifier)
            self.assertEqual(generate.call_count, 1)
        self.assertEqual(self.client.get('/api/project-brain/records').json(), [])
        self.assertEqual(self.client.get('/api/project-brain/graph').json()['nodes'][0]['kind'], 'source')
        invalid = {**draft, 'claims': [{**draft['claims'][0], 'quote': 'AI가 지어낸 문장'}]}
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'generate', return_value=BrainDraft.model_validate(invalid)):
            response = self.client.post('/api/project-brain/drafts', json={'request_id': 'draft-invalid', 'source_ids': [source['id']]})
        self.assertEqual(self.client.get('/api/project-brain/drafts/' + response.json()['id']).json()['state'], 'failed')
        self.assertEqual(self.client.get('/api/project-brain/records').json(), [])

    def test_github_snapshot_validates_response_and_source_id_collision(self):
        url = 'https://github.com/example/repo/pull/3'
        identifier = service.uid()
        payload = {'id': identifier, 'kind': 'github_pr', 'url': url}
        good = httpx.Response(200, json={'html_url': url, 'title': '실제 변경', 'body': '결정의 이유'})
        bad = httpx.Response(200, json={'html_url': 'https://github.com/other/repo/pull/3', 'title': '다른 글', 'body': '본문'})
        with patch.object(github_sharing, 'credential', return_value={'token': 'test-token'}), patch.object(github_sharing, 'remote', return_value=bad):
            self.assertEqual(self.client.post('/api/project-brain/sources', json=payload).status_code, 502)
        with patch.object(github_sharing, 'credential', return_value={'token': 'test-token'}), patch.object(github_sharing, 'remote', return_value=good):
            response = self.client.post('/api/project-brain/sources', json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn('결정의 이유', response.json()['body'])
            self.assertEqual(self.client.post('/api/project-brain/sources', json=payload).json()['id'], identifier)
        db.execute("INSERT INTO users VALUES ('other','other','unused',0)")
        with self.assertRaises(service.Error):
            project_brain.source_save('other', SourceInput(id=identifier, kind='excerpt', title='다른 사람', body='다른 본문'))

    def test_superseded_record_cannot_replace_another(self):
        source = self.source()
        first, second, third = (self.record(source) for _ in range(3))
        payload = {'target_id': first['id'], 'kind': 'supersedes', 'reason': '새 근거'}
        self.assertEqual(self.client.post(f"/api/project-brain/records/{second['id']}/links", json=payload).status_code, 200)
        self.assertEqual(self.client.post(f"/api/project-brain/records/{first['id']}/links", json={**payload, 'target_id': third['id']}).status_code, 409)
        self.assertEqual(self.client.get(f"/api/project-brain/records/{third['id']}").json()['lifecycle'], 'current')


if __name__ == '__main__':
    unittest.main()
