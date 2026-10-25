import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import BackgroundTasks, Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from . import service, learning, access, practice, usage, operations, feeds, diagnostics, foundations, knowledge, reference_notes, ontology, db, github_sharing
from typing import Literal
from . import resources, interpretations, worksheets, practice_records
from .worksheet_schema import WorksheetInput
from .practice_record_schema import PracticeRecordInput
from . import ai_settings
from .ai_settings_schema import AISettingsInput, AISettingsRevision
from .interpretation_schema import InterpretationInput
from .resource_schema import ResourceInput
from .github_schema import GitHubConnection, GitHubRepository, GitHubDefaultRepository, GitHubSource, GitHubPublish, GitHubRecovery
from .note_schema import ReferenceInput, ImageInput, RevisionInput, RegisterKnowledge, ReviewStart, ReviewAnswer, ArchiveInput, ConceptLookup, ApplyNoteSuggestions
from .schema import FeedInput, FeedUpdate, Credentials, DraftInput, ExecutionInput, GenerationInput, ReportInput, ReportUpdate


@asynccontextmanager
async def lifespan(app):
    access.validate_config()
    service.initialize()
    collector = asyncio.create_task(feeds.poll())
    try:
        yield
    finally:
        await feeds.stop(collector)


app = FastAPI(title='Code Trainer', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(service.Error)
async def domain_error(request, error):
    return JSONResponse({'detail': str(error)}, status_code=error.status)


@app.exception_handler(service.Unavailable)
async def runner_error(request, error):
    return JSONResponse({'detail': str(error)}, status_code=503)


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    # The default response can echo source input. Never return raw input in errors.
    fields = ', '.join('.'.join(map(str, e['loc'][1:])) for e in error.errors())
    return JSONResponse({'detail': '입력 형식 또는 길이를 확인해주세요: ' + fields}, status_code=422)


@app.middleware('http')
async def local_boundary(request: Request, call_next):
    deployed = access.enabled()
    if deployed and request.url.path == '/healthz' and request.method in ('GET', 'HEAD'):
        return JSONResponse({'ok': True}, headers={'Cache-Control': 'no-store'})
    try:
        host = urlsplit('http://' + request.headers.get('host', '')).hostname
    except ValueError:
        return JSONResponse({'detail': '올바른 호스트 주소를 사용해주세요.'}, status_code=400)
    if host not in ('127.0.0.1', 'localhost', '::1', 'testserver'):
        return JSONResponse({'detail': '로컬 주소로 접속해주세요.'}, status_code=403)
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        allowed = {access.origin()} if deployed else {str(request.base_url).rstrip('/'), 'http://127.0.0.1:5173', 'http://localhost:5173'}
        if (deployed and not origin) or (origin and origin not in allowed) or request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': '허용되지 않은 요청 출처입니다.'}, status_code=403)
        if request.headers.get('content-type', '').split(';')[0] != 'application/json':
            return JSONResponse({'detail': 'JSON 요청을 사용해주세요.'}, status_code=415)
        body = bytearray()
        limit = 5700000 if request.url.path == '/api/reference-images' and request.method == 'POST' else 260000
        async for chunk in request.stream():
            if len(body) + len(chunk) > limit:
                return JSONResponse({'detail': '요청 크기 제한을 초과했습니다.'}, status_code=413)
            body.extend(chunk)
        request._body = bytes(body)
    if deployed:
        try:
            # JWKS retrieval is blocking I/O; keep it off the ASGI event loop.
            from starlette.concurrency import run_in_threadpool
            request.state.user = await run_in_threadpool(access.user, request)
        except service.Error as error:
            return JSONResponse({'detail': str(error)}, status_code=error.status,
                                headers={'Cache-Control': 'no-store', 'X-Trainer-Auth': 'access'})
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if deployed:
        response.headers['X-Trainer-Auth'] = 'access'
    return response


@app.middleware('http')
async def request_status(request: Request, call_next):
    if not request.url.path.startswith('/api/'):
        return await call_next(request)
    request_id = uuid.uuid4().hex[:12]
    started = time.monotonic()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers['X-Request-ID'] = request_id
        return response
    finally:
        elapsed = round((time.monotonic() - started) * 1000)
        route = getattr(request.scope.get('route'), 'path', '/api/unmatched')
        if status >= 400 or elapsed >= 2000 or route.endswith('/execute'):
            # Never log URL queries, tokens, submitted code, answers or raw exceptions.
            diagnostics.event('API request', request_id=request_id, method=request.method,
                              route=route, status=status, elapsed_ms=elapsed)


def user(request: Request):
    if access.enabled():
        return request.state.user
    return service.require_user(request.cookies.get('trainer_session', ''))


@app.get('/api/session')
def session(request: Request):
    if access.enabled():
        return {'user': user(request), 'setup_required': False, 'auth_mode': 'access'}
    return service.session(request.cookies.get('trainer_session', ''))


@app.post('/api/auth')
def auth(body: Credentials):
    if access.enabled():
        raise service.Error('이메일 인증을 사용해주세요.', 403)
    token = service.authenticate(body)
    response = JSONResponse({'ok': True})
    response.set_cookie('trainer_session', token, httponly=True, samesite='strict', max_age=604800)
    return response


@app.post('/api/logout')
def logout(request: Request, current=Depends(user)):
    if access.enabled():
        return {'logout_url': '/cdn-cgi/access/logout'}
    service.logout(request.cookies.get('trainer_session', ''))
    response = JSONResponse({'ok': True})
    response.delete_cookie('trainer_session')
    return response


@app.get('/api/health')
def health(request: Request):
    current = user(request) if access.enabled() else service.session(request.cookies.get('trainer_session', ''))['user']
    return service.health(current['id'] if current else None)


@app.get('/api/ai/settings')
def ai_connection(current=Depends(user)):
    return ai_settings.status(current['id'])


@app.put('/api/ai/settings')
def ai_connect(body: AISettingsInput, current=Depends(user)):
    return ai_settings.save(current['id'], body)


@app.delete('/api/ai/settings')
def ai_disconnect(body: AISettingsRevision, current=Depends(user)):
    return ai_settings.disconnect(current['id'], body.revision)


@app.get('/api/github/connection')
def github_connection(current=Depends(user)):
    return github_sharing.status(current['id'])


@app.put('/api/github/connection')
def github_connect(body: GitHubConnection, current=Depends(user)):
    return github_sharing.connect(current['id'], body.token)


@app.delete('/api/github/connection')
def github_disconnect(current=Depends(user)):
    return github_sharing.disconnect(current['id'])


@app.post('/api/github/repository-check')
def github_check(body: GitHubRepository, current=Depends(user)):
    service.rate('github-check:' + current['id'], 30)
    return github_sharing.check(current['id'], body.url)


@app.get('/api/github/default-repository')
def github_default(current=Depends(user)):
    return {'repository': github_sharing.default_repository(current['id'])}


@app.put('/api/github/default-repository')
def github_save_default(body: GitHubDefaultRepository, current=Depends(user)):
    return github_sharing.save_default(current['id'], body)


@app.post('/api/github/preview')
def github_preview(body: GitHubSource, current=Depends(user)):
    return github_sharing.preview(current['id'], body.kind, body.id)


@app.get('/api/github/shares')
def github_history(current=Depends(user)):
    return github_sharing.history(current['id'])


@app.post('/api/github/shares')
def github_publish(body: GitHubPublish, current=Depends(user)):
    return github_sharing.publish(current['id'], body)


@app.post('/api/github/shares/{share_id}/recover')
def github_recover(share_id: str, body: GitHubRecovery, current=Depends(user)):
    service.rate('github-recover:' + current['id'], 15)
    return github_sharing.recover(current['id'], share_id, body.url)


@app.get('/api/feed-posts')
def feed_posts(current=Depends(user), page: int = Query(default=1, ge=1), feed_id: str | None = Query(default=None, max_length=80)):
    return feeds.inbox(current['id'], page, feed_id)


@app.post('/api/feed-posts/refresh')
def refresh_feed(current=Depends(user)):
    feeds.refresh(manual=True)
    return feeds.inbox(current['id'])


@app.post('/api/feed-sources', status_code=201)
def add_feed(body: FeedInput, current=Depends(user)):
    return feeds.add(current, body.name, body.url)


@app.patch('/api/feed-sources/{feed_id}')
def update_feed(feed_id: str, body: FeedUpdate, current=Depends(user)):
    return feeds.set_enabled(current, feed_id, body.enabled)


@app.post('/api/feed-sources/{feed_id}/refresh')
def refresh_source(feed_id: str, current=Depends(user)):
    updated = feeds.refresh(manual=True, feed_id=feed_id)
    return {'updated': updated}


@app.get('/api/contexts')
def contexts(current=Depends(user), page: int | None = Query(default=None, ge=1), page_size: int = Query(default=6, ge=1, le=50)):
    return service.contexts(current['id'], page, page_size)


@app.get('/api/contexts/{context_id}')
def context(context_id: str, current=Depends(user)):
    return service.get_context(current['id'], context_id)


@app.get('/api/sets/{set_id}')
def problem_set(set_id: str, current=Depends(user)):
    return service.get_set(current['id'], set_id)


@app.post('/api/contexts/{context_id}/units/{unit_id}/knowledge')
def add_unit_knowledge(context_id: str, unit_id: str, current=Depends(user)):
    return knowledge.add_unit(current['id'], context_id, unit_id)


@app.post('/api/foundations/{lesson_id}/knowledge')
def add_foundation_knowledge(lesson_id: str, version: int = Query(ge=1), current=Depends(user)):
    return knowledge.add_foundation(current['id'], lesson_id, version)


@app.delete('/api/contexts/{context_id}')
def delete_context(context_id: str, current=Depends(user)):
    return service.delete_context(current['id'], context_id)


@app.post('/api/generations', status_code=202)
def begin_generation(body: GenerationInput, tasks: BackgroundTasks, current=Depends(user)):
    value, fresh = service.begin_generation(current['id'], body)
    if fresh:
        tasks.add_task(service.generate, current['id'], value['id'], body)
    return value


@app.get('/api/generations')
def generations(current=Depends(user)):
    return service.generations(current['id'])


@app.get('/api/generations/{generation_id}')
def generation(generation_id: str, current=Depends(user)):
    return service.generation(current['id'], generation_id)


@app.post('/api/generations/{generation_id}/reports', status_code=201)
def report_generation(generation_id: str, body: ReportInput, current=Depends(user)):
    return service.report_generation(current['id'], generation_id, body)


@app.put('/api/exercises/{exercise_id}/progress')
def progress(exercise_id: str, body: DraftInput, current=Depends(user)):
    return service.save_progress(current['id'], exercise_id, body)


@app.post('/api/exercises/{exercise_id}/execute')
def execute(exercise_id: str, body: ExecutionInput, current=Depends(user)):
    return service.execute(current['id'], exercise_id, body)


@app.get('/api/exercises/{exercise_id}/hints/{step}')
def hints(exercise_id: str, step: int, review_id: str | None = None, current=Depends(user)):
    return service.hints(current['id'], exercise_id, step, review_id)


@app.get('/api/exercises/{exercise_id}/solution')
def solution(exercise_id: str, review_id: str | None = None, current=Depends(user)):
    return service.solution(current['id'], exercise_id, review_id)


@app.post('/api/exercises/{exercise_id}/reports', status_code=201)
def report(exercise_id: str, body: ReportInput, current=Depends(user)):
    return service.report(current['id'], exercise_id, body)


@app.get('/api/me')
def history(current=Depends(user)):
    return service.history(current['id'])


@app.get('/api/me/learning-summary')
def learning_summary(current=Depends(user), record_id: str | None = None):
    return learning.status(current['id'], record_id)


@app.get('/api/me/knowledge-graph')
def knowledge_graph(current=Depends(user), record_id: str | None = None):
    return knowledge.view(current['id'], record_id)


@app.get('/api/knowledge/concepts')
def knowledge_concepts(current=Depends(user), q: str = Query(default='', max_length=160)):
    return ontology.concepts(current['id'], q)


@app.post('/api/knowledge/concept-matches')
def knowledge_concept_matches(body: ConceptLookup, current=Depends(user)):
    return ontology.concept_matches(current['id'], body)


@app.get('/api/resources')
def resource_list(q: str = Query(default='', max_length=160), page: int = Query(default=1, ge=1),
                  kind: Literal['all', 'text', 'url', 'note'] = 'all', current=Depends(user)):
    return resources.listing(current['id'], q, page, kind)


@app.get('/api/worksheets')
def worksheet_list(page: int = Query(default=1, ge=1), interpretation_id: str | None = Query(default=None, pattern=r'^[a-f0-9]{32}$'), current=Depends(user)):
    return worksheets.listing(current['id'], page, interpretation_id)


@app.post('/api/worksheets', status_code=202)
def worksheet_start(body: WorksheetInput, tasks: BackgroundTasks, current=Depends(user)):
    result, fresh = worksheets.begin(current['id'], body)
    if fresh:
        tasks.add_task(worksheets.generate, result['id'])
    return result


@app.get('/api/worksheets/{identifier}/practice')
def practice_record_view(identifier: str, current=Depends(user)):
    return practice_records.view(current['id'], identifier)


@app.post('/api/worksheets/{identifier}/practice')
def practice_record_save(identifier: str, body: PracticeRecordInput, current=Depends(user)):
    return practice_records.save(current['id'], identifier, body)


@app.get('/api/worksheets/{identifier}/practice/versions/{revision}')
def practice_record_version(identifier: str, revision: int, current=Depends(user)):
    return practice_records.version(current['id'], identifier, revision)


@app.get('/api/worksheets/{identifier}')
def worksheet_view(identifier: str, current=Depends(user)):
    return worksheets.view(current['id'], identifier)


@app.get('/api/interpretations')
def interpretation_list(page: int = Query(default=1, ge=1), resource_id: str | None = Query(default=None, pattern=r'^[a-f0-9]{32}$'), current=Depends(user)):
    return interpretations.listing(current['id'], page, resource_id)


@app.post('/api/interpretations', status_code=202)
def interpretation_start(body: InterpretationInput, tasks: BackgroundTasks, current=Depends(user)):
    result, fresh = interpretations.begin(current['id'], body)
    if fresh:
        tasks.add_task(interpretations.generate, result['id'])
    return result


@app.get('/api/interpretations/{identifier}')
def interpretation_view(identifier: str, current=Depends(user)):
    return interpretations.view(current['id'], identifier)


@app.get('/api/interpretations/{identifier}/code')
def interpretation_code(identifier: str, section_id: str = Query(pattern=r'^s[1-6]$'), current=Depends(user)):
    from . import code_practice
    return code_practice.listing(current['id'], identifier, section_id)


@app.post('/api/resources')
def resource_register(body: ResourceInput, current=Depends(user)):
    return resources.register(current['id'], body)


@app.get('/api/resources/{resource_id}')
def resource_view(resource_id: str, current=Depends(user)):
    return resources.view(current['id'], resource_id)


@app.get('/api/resources/{resource_id}/versions/{revision}')
def resource_version(resource_id: str, revision: int, current=Depends(user)):
    return resources.version(current['id'], resource_id, revision)


@app.get('/api/reference-notes')
def reference_list(current=Depends(user), q: str = Query(default='', max_length=160),
                   page: int = Query(default=1, ge=1), archived: bool = False):
    return reference_notes.listing(current['id'], q, page, archived)


@app.post('/api/reference-notes')
def reference_save(body: ReferenceInput, current=Depends(user)):
    return reference_notes.save(current['id'], body)


@app.get('/api/reference-notes/{note_id}')
def reference_get(note_id: str, current=Depends(user)):
    return reference_notes.view(current['id'], note_id)


@app.get('/api/reference-notes/{note_id}/versions/{revision}')
def reference_version(note_id: str, revision: int, current=Depends(user)):
    import json
    reference_notes.owned(current['id'], note_id)
    row = db.one('SELECT data FROM reference_note_versions WHERE owner=? AND note_id=? AND revision=?', (current['id'], note_id, revision))
    if not row:
        raise service.Error('노트 버전을 찾을 수 없습니다.', 404)
    return json.loads(row['data'])


@app.post('/api/reference-notes/{note_id}/archive')
def reference_archive(note_id: str, body: ArchiveInput, current=Depends(user)):
    return reference_notes.archive(current['id'], note_id, body.archived)


@app.get('/api/reference-notes/{note_id}/export')
def reference_export(note_id: str, current=Depends(user)):
    return Response(reference_notes.export(current['id'], note_id), media_type='application/zip',
                    headers={'Content-Disposition': 'attachment; filename="reference-note.zip"'})


@app.post('/api/reference-images')
def reference_image_upload(body: ImageInput, current=Depends(user)):
    return reference_notes.image_upload(current['id'], body)


@app.get('/api/reference-images/{image_id}')
def reference_image_get(image_id: str, current=Depends(user)):
    return Response(reference_notes.image_read(current['id'], image_id), media_type='image/webp')


@app.post('/api/reference-notes/{note_id}/proposals', status_code=202)
def reference_propose(note_id: str, body: RevisionInput, tasks: BackgroundTasks, current=Depends(user)):
    key, fresh = reference_notes.begin_proposal(current['id'], note_id, body.revision)
    if fresh:
        tasks.add_task(reference_notes.propose, current['id'], key)
    return reference_notes.proposal_view(current['id'], key)


@app.get('/api/reference-proposals/{proposal_id}')
def reference_proposal_get(proposal_id: str, current=Depends(user)):
    return reference_notes.proposal_view(current['id'], proposal_id)


@app.post('/api/reference-proposals/{proposal_id}/apply')
def reference_apply_suggestions(proposal_id: str, body: ApplyNoteSuggestions, current=Depends(user)):
    return reference_notes.apply_suggestions(current['id'], proposal_id, body)


@app.post('/api/reference-notes/{note_id}/knowledge')
def reference_register(note_id: str, body: RegisterKnowledge, current=Depends(user)):
    return reference_notes.register(current['id'], note_id, body)


@app.post('/api/reference-reviews')
def reference_review_start(body: ReviewStart, current=Depends(user)):
    return reference_notes.start_review(current['id'], body)


@app.get('/api/reference-reviews/{review_id}')
def reference_review_get(review_id: str, current=Depends(user)):
    return reference_notes.review_view(current['id'], review_id)


@app.post('/api/reference-reviews/{review_id}/answers', status_code=202)
def reference_review_answer(review_id: str, body: ReviewAnswer, tasks: BackgroundTasks, current=Depends(user)):
    fresh = reference_notes.answer_review(current['id'], review_id, body)
    if fresh:
        tasks.add_task(reference_notes.follow_up, current['id'], review_id)
    return reference_notes.review_view(current['id'], review_id)


@app.post('/api/me/learning-summary', status_code=202)
def summarize_learning(tasks: BackgroundTasks, current=Depends(user)):
    items = learning.begin(current['id'])
    if items is not None:
        tasks.add_task(learning.summarize, current['id'], items)
    return learning.status(current['id'])


@app.get('/api/attempts/{attempt_id}')
def attempt(attempt_id: str, current=Depends(user)):
    return service.get_attempt(current['id'], attempt_id)


@app.get('/api/admin/reports')
def reports(current=Depends(user)):
    return service.admin_reports(current)


@app.get('/api/admin/sources')
def sources(current=Depends(user)):
    return service.admin_sources(current)


@app.get('/api/admin/sources/{source_id}')
def source_document(source_id: str, current=Depends(user)):
    return service.admin_source(current, source_id)


@app.patch('/api/admin/reports/{report_id}')
def review_report(report_id: str, body: ReportUpdate, current=Depends(user)):
    return service.review_report(current, report_id, body)


@app.get('/api/me/reviews')
def review_queue(current=Depends(user)):
    return practice.queue(current['id'])


@app.post('/api/exercises/{exercise_id}/reviews')
def start_review(exercise_id: str, current=Depends(user)):
    return practice.begin(current['id'], exercise_id)


@app.get('/api/reviews/{review_id}')
def review_session(review_id: str, current=Depends(user)):
    return practice.view(current['id'], review_id)


@app.put('/api/reviews/{review_id}/progress')
def review_progress(review_id: str, body: DraftInput, current=Depends(user)):
    return practice.save(current['id'], review_id, body)


@app.get('/api/me/ai-usage')
def ai_usage(current=Depends(user)):
    return usage.summary(current['id'])


@app.get('/api/admin/operations')
def operation_status(current=Depends(user)):
    if not current['admin']:
        raise service.Error('관리자만 확인할 수 있습니다.', 403)
    return operations.status()


@app.get('/api/foundations')
def foundation_catalog(current=Depends(user)):
    return foundations.catalog(current['id'])


@app.get('/api/foundations/{lesson_id}')
def foundation_lesson(lesson_id: str, current=Depends(user)):
    return foundations.view(current['id'], lesson_id)


@app.put('/api/foundations/{lesson_id}/progress')
def foundation_progress(lesson_id: str, body: foundations.FoundationDraft, current=Depends(user)):
    return foundations.save(current['id'], lesson_id, body)


@app.post('/api/foundations/{lesson_id}/restart')
def foundation_restart(lesson_id: str, body: foundations.FoundationRestart, current=Depends(user)):
    return foundations.restart(current['id'], lesson_id, body)


@app.post('/api/foundations/{lesson_id}/explain', status_code=202)
def foundation_explain(lesson_id: str, body: foundations.ExplanationInput, tasks: BackgroundTasks, current=Depends(user)):
    value, fresh = foundations.begin(current['id'], lesson_id, body, explain=True)
    if fresh:
        tasks.add_task(foundations.review, current['id'], value['id'])
    return value


@app.post('/api/foundations/{lesson_id}/submit', status_code=202)
def foundation_submit(lesson_id: str, body: foundations.FoundationSubmission, tasks: BackgroundTasks, current=Depends(user)):
    value, fresh = foundations.begin(current['id'], lesson_id, body)
    if fresh:
        tasks.add_task(foundations.execute, current['id'], value['id'])
    return value


@app.get('/api/foundation-reviews/{job_id}')
def foundation_review(job_id: str, current=Depends(user)):
    return foundations.job(current['id'], job_id, explain=True)


@app.get('/api/foundation-attempts/{job_id}')
def foundation_attempt(job_id: str, current=Depends(user)):
    return foundations.job(current['id'], job_id)


@app.get('/api/foundations/{lesson_id}/history')
def foundation_submissions(lesson_id: str, current=Depends(user)):
    return foundations.submissions(current['id'], lesson_id)


@app.get('/api/foundations/{lesson_id}/solution')
def foundation_solution(lesson_id: str, current=Depends(user)):
    return foundations.solution(current['id'], lesson_id)


@app.get('/api/me/foundations')
def foundation_history(current=Depends(user)):
    return {'items': foundations.history(current['id'])}


dist = Path(__file__).resolve().parent.parent / 'frontend' / 'dist'
if (dist / 'assets').is_dir():
    app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='assets')


@app.get('/{path:path}')
def spa(path: str):
    if path.startswith('api/') or not (dist / 'index.html').exists():
        return JSONResponse({'detail': '페이지를 찾을 수 없습니다. 먼저 frontend를 빌드해주세요.'}, status_code=404)
    return FileResponse(dist / 'index.html')
