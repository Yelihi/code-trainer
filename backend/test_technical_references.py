import unittest
from unittest.mock import patch
from . import db, service, technical_references as references, test_app


class ReferenceTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def save(self, **patches):
        value = {'id': 'a' * 32, 'request_id': service.uid(), 'revision': 0, 'title': '상태 관리', 'user_body': '내가 작성한 설명', 'targets': []}
        value.update(patches)
        return references.save(self.owner, references.ReferenceInput(**value))

    def test_save_replay_conflict_versions_and_owner_boundaries(self):
        first = self.save(request_id='reference-save')
        self.assertEqual(self.save(request_id='reference-save'), first)
        with self.assertRaises(service.Error):
            self.save(request_id='reference-save', user_body='변경')
        with self.assertRaises(service.Error):
            self.save(user_body='오래된 탭 변경')
        second = self.save(revision=1, user_body='보완한 내 설명')
        self.assertEqual(second['revision'], 2)
        self.assertEqual(references.version(self.owner, first['id'], 1)['user_body'], '내가 작성한 설명')
        self.assertEqual(references.listing('other', ''), [])
        with self.assertRaises(service.Error):
            references.read('other', first['id'])
        with self.assertRaises(service.Error):
            self.save(id='b' * 32)
        self.assertEqual(self.client.get('/api/technical-references/' + first['id']).status_code, 200)

    def test_ai_never_overwrites_user_writing_and_marks_changed_evidence(self):
        first = self.save()
        draft = references.ReferenceDraft(purpose='목적', explanation='AI 설명', conditions='조건', procedure='절차', examples='실행하지 않은 예제', cautions='주의', verification='검증 필요', source_ids=['user-writing'])
        with patch.object(references.ai, 'available', return_value=True):
            request = references.Generate(request_id='generate-reference', revision=1)
            job, fresh = references.begin(self.owner, first['id'], request)
            self.assertTrue(fresh)
            self.assertFalse(references.begin(self.owner, first['id'], request)[1])
        def generate(*args):
            self.save(revision=1, user_body='생성 중 사용자가 보완한 내용')
            return draft
        with patch.object(references.ai, 'generate', side_effect=generate):
            references.generate(job['id'])
        value = references.read(self.owner, first['id'])
        self.assertEqual(value['user_body'], '생성 중 사용자가 보완한 내용')
        self.assertEqual(value['ai']['explanation'], 'AI 설명')
        self.assertTrue(value['stale'])
        self.assertEqual(len(value['versions']), 2)

    def test_failed_ai_retains_source_and_invalid_target_rejected(self):
        first = self.save()
        with patch.object(references.ai, 'available', return_value=True), patch.object(references.ai, 'generate', side_effect=RuntimeError('failure')):
            job, _ = references.begin(self.owner, first['id'], references.Generate(request_id='failed-reference', revision=1))
            references.generate(job['id'])
        value = references.read(self.owner, first['id'])
        self.assertEqual(value['user_body'], first['user_body'])
        self.assertEqual(value['jobs'][0]['state'], 'failed')
        with self.assertRaises(service.Error):
            self.save(id='b' * 32, title='다른 문서', targets=[{'kind': 'resource', 'id': 'f' * 32}])

    def test_skill_preview_package_validation_and_provenance(self):
        import io
        import json
        import zipfile
        first = self.save(user_body='명시적으로 작성한 기술 설명과 적용 조건, 작업 절차, 입력 검증 및 실행 결과 확인 방법. ' * 5)
        skill = references.SkillDraft(name='state-boundary', description='상태 경계를 정하고 검증합니다. 컴포넌트 상태 설계 시 사용합니다.', when_to_use='상태 설계', scope='컴포넌트 상태', exclusions='개인 분석 제외', inputs='요구사항', steps='1. 소유자를 정한다.\n2. 변경 경로를 확인한다.', decisions='공유 범위 확인', verification='실제 입력으로 테스트한다.', limitations='예제 미실행', source_ids=['user-writing'])
        with patch.object(references.ai, 'available', return_value=True), patch.object(references.ai, 'generate', return_value=skill):
            request = references.Generate(request_id='skill-request', revision=1)
            job, fresh = references.begin(self.owner, first['id'], request, kind='skill')
            self.assertTrue(fresh)
            references.generate(job['id'])
            self.assertFalse(references.begin(self.owner, first['id'], request, kind='skill')[1])
        preview = references.skill_job(self.owner, first['id'], job['id'])
        self.assertIn('## 작업 절차', preview['markdown'])
        with zipfile.ZipFile(io.BytesIO(references.skill_package(self.owner, first['id'], job['id']))) as archive:
            markdown = archive.read('state-boundary/SKILL.md').decode()
            frontmatter = dict((key, json.loads(value.strip())) for key, value in (line.split(':', 1) for line in markdown.split('---\n')[1].strip().splitlines()))
            self.assertEqual(frontmatter['name'], 'state-boundary')
            self.assertIn('state-boundary/references/REFERENCE.md', archive.namelist())
            provenance = json.loads(archive.read('state-boundary/references/provenance.json'))
            self.assertEqual(provenance['reference_revision'], 1)
        self.assertIsNone(references.read(self.owner, first['id'])['ai'])
        with self.assertRaises(service.Error):
            references.skill_job('other', first['id'], job['id'])
        with self.assertRaises(service.Error):
            references.skill_markdown(skill.model_copy(update={'steps': '[없는 파일](missing.md)'}))

    def test_problem_and_foundation_evidence_do_not_bypass_hidden_answers(self):
        import json
        from . import foundations, learning_links, problem_books
        problem = problem_books.save_problem(self.owner, problem_books.ProblemInput(title='비공개 답안', kind='text', language='cpp', prompt='질문', answer='secret-reference-answer'))
        target = learning_links.resolve(self.owner, learning_links.Target(kind='problem', id=problem['id']))
        evidence = references.evidence(self.owner, target)
        self.assertNotIn('secret-reference-answer', evidence['excerpt'])
        foundation = next(iter(foundations.CATALOG.values()))
        target = learning_links.resolve(self.owner, learning_links.Target(kind='foundation', id=foundation['id']))
        excerpt = json.loads(references.evidence(self.owner, target)['excerpt'])
        self.assertNotIn('reference', excerpt)
        self.assertFalse(any('answer' in question for question in excerpt['questions']))

    def test_new_ai_models_use_learning_envelope_instead_of_exercise_prompt(self):
        import json
        import httpx
        from . import ai, study
        models = [study.Suggestions(suggestions=[]), references.ReferenceDraft(purpose='목적', explanation='설명', conditions='조건', procedure='절차', examples='미실행', cautions='주의', verification='검증', source_ids=['user-writing']),
                  references.SkillDraft(name='example-skill', description='기술 작업 시 사용', when_to_use='작업', scope='기술', exclusions='기타', inputs='입력', steps='절차', decisions='판단', verification='검증', limitations='제한', source_ids=['user-writing'])]
        client = httpx.Client
        for value in models:
            def handle(request):
                payload = json.loads(request.content)
                self.assertIn('technical learning', payload['messages'][0]['content'])
                self.assertNotIn('deterministic coding exercises', payload['messages'][0]['content'])
                self.assertEqual(payload['response_format']['json_schema']['name'], type(value).__name__)
                return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({'data': value.model_dump(), 'error': ''})}}]})
            with patch.object(ai.httpx, 'Client', side_effect=lambda **kwargs: client(transport=httpx.MockTransport(handle), **kwargs)):
                result = ai._generate(type(value), 'Use supplied records.', {}, connection={'model': 'fixture-model', 'api_key': 'fixture-only', 'provider_url': 'https://example.test'})
            self.assertEqual(result, value)
