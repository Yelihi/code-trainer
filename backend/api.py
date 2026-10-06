from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import BackgroundTasks, Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from . import service, learning, access, practice, usage, operations
from .schema import Credentials, DraftInput, ExecutionInput, GenerationInput, ReportInput, ReportUpdate


@asynccontextmanager
async def lifespan(app):
    access.validate_config()
    service.initialize()
    yield


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
        async for chunk in request.stream():
            if len(body) + len(chunk) > 260000:
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
def health():
    return service.health()


@app.get('/api/contexts')
def contexts(current=Depends(user), page: int | None = Query(default=None, ge=1), page_size: int = Query(default=6, ge=1, le=50)):
    return service.contexts(current['id'], page, page_size)


@app.get('/api/contexts/{context_id}')
def context(context_id: str, current=Depends(user)):
    return service.get_context(current['id'], context_id)


@app.get('/api/sets/{set_id}')
def problem_set(set_id: str, current=Depends(user)):
    return service.get_set(current['id'], set_id)


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


dist = Path(__file__).resolve().parent.parent / 'frontend' / 'dist'
if (dist / 'assets').is_dir():
    app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='assets')


@app.get('/{path:path}')
def spa(path: str):
    if path.startswith('api/') or not (dist / 'index.html').exists():
        return JSONResponse({'detail': '페이지를 찾을 수 없습니다. 먼저 frontend를 빌드해주세요.'}, status_code=404)
    return FileResponse(dist / 'index.html')
