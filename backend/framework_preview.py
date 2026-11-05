"""Render a single React or Vue component inside the existing isolated runner."""
import json
from typing import Literal
from pydantic import Field
from . import runner, service
from .schema import Model


class PreviewInput(Model):
    framework: Literal['react', 'vue']
    code: str = Field(min_length=1, max_length=24000)


def render(owner, request: PreviewInput):
    service.rate('framework-preview:' + owner, 30, 60)
    result = runner.run(request.framework, request.code, [''])[0]
    if result['status'] != 'ok' or result['exit_code']:
        return {'status': result['status'] if result['status'] != 'ok' else 'runtime_error',
                'error': result['stderr'][:2000] or '컴포넌트를 렌더링하지 못했습니다.',
                'warnings': '', 'html': '', 'css': '', 'client': ''}
    try:
        preview = json.loads(result['stdout'])
        if not isinstance(preview, dict) or not all(isinstance(preview.get(key), str) for key in ('html', 'css', 'client')):
            raise ValueError('Invalid preview')
    except (json.JSONDecodeError, ValueError):
        raise service.Error('실행 결과를 화면으로 표시할 수 없습니다. 출력 크기와 코드를 확인해주세요.', 422) from None
    return {'status': 'ok', 'error': '', 'warnings': result['stderr'][:2000],
            'html': preview['html'], 'css': preview['css'], 'client': preview['client']}
