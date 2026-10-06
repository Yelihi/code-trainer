"""Read a sanitized host snapshot. The API never controls Docker or reads host secrets."""
from datetime import datetime, timezone
import json
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal
from . import db


class Certificate(BaseModel):
    name: Literal['앱 연결', '실행기 연결']
    expires_at: str | None = None
    days_left: int | None = None


class Snapshot(BaseModel):
    model_config = ConfigDict(strict=True)
    collected_at: str
    backup_at: str | None = None
    internal_free_gib: float = Field(ge=0, allow_inf_nan=False)
    external_free_gib: float = Field(ge=0, allow_inf_nan=False)
    certificates: list[Certificate] = Field(max_length=2)
    checks: dict[Literal['full_reboot', 'off_device_recovery'], str] = Field(default_factory=dict)


def status():
    try:
        raw = Snapshot.model_validate(json.loads((db.path().parent / 'operations.json').read_text())).model_dump()
        collected = datetime.fromisoformat(raw['collected_at'])
        age = (datetime.now(timezone.utc) - collected).total_seconds()
        # Explicit allowlist; never relay arbitrary host files to the browser.
        result = {k: raw.get(k) for k in ('collected_at', 'backup_at', 'internal_free_gib', 'external_free_gib', 'certificates', 'checks')}
        result['stale'] = age > 900 or age < -60
    except (OSError, ValueError, KeyError, TypeError, ValidationError):
        return {'available': False, 'stale': True, 'warnings': ['운영 상태를 아직 수집하지 못했습니다.']}
    warnings = []
    if result['stale']:
        warnings.append('운영 정보가 오래되었습니다. 수집 작업을 확인해주세요.')
    free = result.get('internal_free_gib')
    if not isinstance(free, (int, float)) or free < 10:
        warnings.append('내장 디스크 여유를 확인해주세요. 백업 최소 기준은 5GiB입니다.')
    try:
        backup_age = (datetime.now(timezone.utc) - datetime.fromisoformat(result['backup_at'])).total_seconds()
        if backup_age > 36 * 3600 or backup_age < -60:
            warnings.append('최근 36시간 안의 정상 백업을 확인하지 못했습니다.')
    except (ValueError, TypeError):
        warnings.append('마지막 백업 성공 시각이 없습니다.')
    for cert in result.get('certificates') or []:
        if cert.get('days_left') is None or cert['days_left'] <= 14:
            warnings.append(f"{cert['name']} 인증서 갱신을 확인해주세요.")
    result.update(available=True, warnings=warnings)
    return result
