import io
import json
import unittest
import zipfile
from unittest.mock import patch
from . import db, service, technical_references as refs, reference_packages as packages, record_export, test_app


class PackageTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def create(self):
        ref = refs.save(self.owner, refs.ReferenceInput(id='a'*32, request_id=service.uid(), revision=0,
            title='작업용 레퍼런스', user_body='상태 경계를 정하고 입력과 결과를 검증합니다. '*10))
        skill = refs.SkillDraft(name='state-check', description='상태 변경을 검사할 때 사용합니다.', when_to_use='상태 변경', scope='상태',
            exclusions='기타', inputs='입력', steps='1. 검사합니다.', decisions='경계', verification='검사', limitations='미실행', source_ids=['user-writing'],
            files=[{'path':'scripts/check.py','content':'print(42)\n'}])
        with patch.object(refs.ai,'available',return_value=True), patch.object(refs.ai,'generate',return_value=skill):
            job,_=refs.begin(self.owner,ref['id'],refs.Generate(revision=1,request_id=service.uid()),kind='skill')
            refs.generate(job['id'])
        return ref,job

    def test_generation_edit_status_history_and_export_keep_identity(self):
        ref, job = self.create()
        view=packages.read(self.owner,ref['id'])
        self.assertEqual(view['status'],'backlog')
        self.assertEqual(view['files']['scripts/check.py'],'print(42)\n')
        first=packages.save(self.owner,ref['id'],packages.Edit(revision=view['revision'],files=view['files'],status='active',destination=''))
        merged=packages.save(self.owner,ref['id'],packages.Edit(revision=first['revision'],files=first['files'],status='merged',destination='https://github.com/example/fs'))
        back=packages.save(self.owner,ref['id'],packages.Edit(revision=merged['revision'],files=merged['files'],status='backlog',destination=merged['destination']))
        self.assertEqual(back['status'],'backlog')
        self.assertEqual(db.one('SELECT COUNT(*) n FROM technical_references')['n'],1)
        self.assertEqual(len(back['history']),4)
        self.assertEqual(packages.version(self.owner,ref['id'],first['revision'])['status'],'active')
        with zipfile.ZipFile(io.BytesIO(packages.download(self.owner,ref['id']))) as z:
            self.assertIn('state-check/scripts/check.py',z.namelist())
            self.assertIn('state-check/references/provenance.json',z.namelist())
        self.assertEqual(packages.read(self.owner,ref['id'])['status'],'backlog')
        response=self.client.get('/api/technical-references/'+ref['id']+'/package')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['package']['status'],'backlog')
        with zipfile.ZipFile(io.BytesIO(record_export.export(self.owner))) as archive:
            self.assertEqual(json.loads(archive.read('records/reference_packages.json'))[0]['reference_id'],ref['id'])
            self.assertEqual(len(json.loads(archive.read('records/reference_package_versions.json'))),4)

    def test_paths_conflicts_and_owner_are_rejected_without_losing_files(self):
        ref,_=self.create(); view=packages.read(self.owner,ref['id'])
        for path in ['../secret','scripts/../../x','/tmp/x','scripts/a\\b.py','references/provenance.json']:
            with self.assertRaises(service.Error):
                packages.save(self.owner,ref['id'],packages.Edit(revision=1,files={**view['files'],path:'bad'},status='backlog'))
        with self.assertRaises(service.Error):
            packages.save(self.owner,ref['id'],packages.Edit(revision=0,files=view['files'],status='active'))
        with self.assertRaises(service.Error): packages.read('other',ref['id'])
        self.assertEqual(packages.read(self.owner,ref['id'])['revision'],1)
        self.assertEqual(self.client.put('/api/technical-references/'+ref['id']+'/package',json={'revision':1,'files':view['files'],'status':'invalid'}).status_code,422)

    def test_learning_sources_do_not_require_manual_explanation_or_claim_mastery(self):
        q=self.client.post('/api/questions',json={'text':'状態の境界は？','request_id':'package-question'}).json()
        candidates=packages.sources(self.owner,'')['items']
        self.assertTrue(any(x['id']==q['id'] for x in candidates))
        self.assertEqual(packages.sources('other','')['items'],[])
        ref=refs.save(self.owner,refs.ReferenceInput(id='b'*32,request_id=service.uid(),revision=0,title='質問から生成',targets=[{'kind':'question','id':q['id']}]))
        self.assertTrue(refs.skill_snapshot(self.owner,ref['id'])['sources'])

    def test_generation_does_not_overwrite_concurrent_edit_or_reset_status(self):
        ref,job=self.create(); view=packages.read(self.owner,ref['id'])
        current=packages.save(self.owner,ref['id'],packages.Edit(revision=1,files=view['files'],status='merged'))
        row=db.one('SELECT * FROM technical_reference_jobs WHERE id=?',(job['id'],))
        self.assertFalse(packages.apply_generated(row,refs.SkillDraft.model_validate_json(row['data']),expected_revision=1))
        self.assertEqual(packages.read(self.owner,ref['id'])['status'],'merged')
        self.assertEqual(packages.read(self.owner,ref['id'])['revision'],current['revision'])

    def test_existing_skill_migrates_once_and_filter_keeps_legacy_documents(self):
        ref,job=self.create()
        db.execute('DELETE FROM reference_package_versions')
        db.execute('DELETE FROM reference_packages')
        with db.connect(write=True) as c: packages.initialize(c)
        self.assertEqual(packages.read(self.owner,ref['id'])['status'],'backlog')
        with db.connect(write=True) as c: packages.initialize(c)
        self.assertEqual(len(packages.read(self.owner,ref['id'])['history']),1)
        items=self.client.get('/api/technical-references?status=backlog').json()['items']
        self.assertEqual([x['id'] for x in items],[ref['id']])
        self.assertEqual(self.client.get('/api/technical-references?status=active').json()['items'],[])
        self.assertEqual(self.client.get('/api/technical-references?status=invalid').status_code,422)

    def test_regeneration_preserves_merged_and_stale_source_result_requires_explicit_apply(self):
        ref,job=self.create(); original=packages.read(self.owner,ref['id'])
        current=packages.save(self.owner,ref['id'],packages.Edit(revision=1,files=original['files'],status='merged'))
        db.execute("UPDATE technical_reference_jobs SET created_at='2026-01-01T00:00:00+00:00' WHERE id=?",(job['id'],))
        skill=refs.SkillDraft.model_validate_json(db.one('SELECT data FROM technical_reference_jobs WHERE id=?',(job['id'],))['data'])
        with patch.object(refs.ai,'available',return_value=True),patch.object(refs.ai,'generate',return_value=skill):
            new,_=refs.begin(self.owner,ref['id'],refs.Generate(revision=1,request_id=service.uid(),refresh=True),kind='skill')
            self.assertNotEqual(new['id'],job['id'])
            refs.generate(new['id'])
        view=packages.read(self.owner,ref['id'])
        self.assertEqual(view['status'],'merged')
        self.assertEqual(view['revision'],current['revision']+1)
        row=db.one('SELECT * FROM technical_reference_jobs WHERE id=?',(new['id'],))
        refs.save(self.owner,refs.ReferenceInput(id=ref['id'],request_id=service.uid(),revision=1,title=ref['title'],user_body='수정'))
        self.assertFalse(packages.apply_generated(row,skill,view['revision']))
        applied=packages.apply_job(self.owner,ref['id'],packages.ApplyJob(revision=view['revision'],job_id=new['id']))
        self.assertTrue(applied['stale'])
        self.assertEqual(applied['status'],'merged')
        bad={**applied['files'],'SKILL.md':applied['files']['SKILL.md']+'\n[missing](scripts/missing.py)'}
        with self.assertRaises(service.Error): packages.save(self.owner,ref['id'],packages.Edit(revision=applied['revision'],files=bad,status='backlog'))

    def test_empty_package_envelope_and_large_source_snapshot(self):
        ref=refs.save(self.owner,refs.ReferenceInput(id='e'*32,request_id=service.uid(),revision=0,title='생성 전'))
        self.assertEqual(self.client.get('/api/technical-references/'+ref['id']+'/package').json(),{'package':None})
        created,job=self.create()
        row=db.one('SELECT * FROM technical_reference_jobs WHERE id=?',(job['id'],))
        value=json.loads(row['snapshot']);value['sources']=value['sources']*10
        for source in value['sources']: source['excerpt']='본문 '*4000
        row['snapshot']=json.dumps(value)
        files=packages.generated_files(row,refs.SkillDraft.model_validate_json(row['data']))
        self.assertLess(len(files['references/REFERENCE.md']),60000)
        self.assertIn('발췌',files['references/REFERENCE.md'])
        for header in ['name: null\ndescription: text','name: state-check\ndescription: |\n  hidden','name: state-check\ndescription: [list]']:
            with self.assertRaises(service.Error): packages.validate_files({'SKILL.md':'---\n'+header+'\n---\nbody'})
