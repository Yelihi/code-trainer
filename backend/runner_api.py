"""Run only inside the runner VM, behind uvicorn's mandatory client certificate check."""
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from . import runner
from .execution import ExecutionRequest, ExecutionResponse, Runtime


@asynccontextmanager
async def lifespan(app):
    if runner.remote():
        raise RuntimeError('Runner service must use its own local Docker engine')
    values = json.loads(Path(os.environ['TRAINER_RUNTIME_MANIFEST']).read_text())
    if not isinstance(values, list) or not values:
        raise ValueError('A nonempty, operator-managed runtime manifest is required')
    app.state.runtimes = {Runtime(image_id=value).image_id for value in values}
    current = runner.pin_runtime()
    if current not in app.state.runtimes:
        raise ValueError('Current runtime is not approved')
    app.state.current = current
    runner.cleanup()
    yield
    runner.cleanup()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware('http')
async def boundary(request: Request, call_next):
    # TLS rejects clients without the app certificate before HTTP reaches this code.
    if request.method == 'POST':
        if request.headers.get('content-type', '').split(';')[0] != 'application/json':
            return JSONResponse({'detail': 'JSON required'}, status_code=415)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 512000:
                return JSONResponse({'detail': 'Request too large'}, status_code=413)
        request._body = bytes(body)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.exception_handler(RequestValidationError)
async def invalid(request, error):
    return JSONResponse({'detail': 'Invalid execution request'}, status_code=422)


@app.exception_handler(runner.Unavailable)
async def unavailable(request, error):
    return JSONResponse({'detail': 'Runner unavailable'}, status_code=503)


@app.get('/runtime', response_model=Runtime)
def runtime():
    return Runtime(image_id=app.state.current)


@app.post('/run', response_model=ExecutionResponse)
def run(body: ExecutionRequest):
    image_id = body.image_id or app.state.current
    if image_id not in app.state.runtimes:
        return JSONResponse({'detail': 'Runtime not approved'}, status_code=422)
    return {'results': runner.run(body.language, body.code, body.inputs, image_id=image_id)}
