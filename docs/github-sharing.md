# GitHub 지식 공유

왼쪽 **설정 → GitHub 연동**에서 Fine-grained PAT를 연결한다. 저장소를 기본값으로 고정하지 않는다. 저장한 레퍼런스 노트 또는 지식 그래프 상세 패널의 **GitHub 이슈로 공유**에서 저장소 주소 입력 → 권한 확인 → 본문 검토 → 명시적 등록으로 진행한다.

## 서버 설정

`TRAINER_GITHUB_ENCRYPTION_KEY`에 Fernet 키를 한 번 설정한다. 비어 있으면 다른 기능은 그대로 작동하며 GitHub 토큰 저장만 차단된다. 키를 매번 생성하거나 저장된 토큰이 있는 상태에서 교체하지 않는다.

로컬 `.env` 또는 배포용 비공개 `server.env`에 키를 추가하는 예:

```python
# .venv/bin/python으로 실행. path는 실제 비공개 환경 파일 경로로 지정한다.
from pathlib import Path
from cryptography.fernet import Fernet
path = Path('.env')
text = path.read_text()
lines = text.splitlines()
name = 'TRAINER_GITHUB_ENCRYPTION_KEY'
assert not any(line.startswith(name + '=') and line.split('=', 1)[1].strip() for line in lines), '기존 키를 유지하세요'
lines = [line for line in lines if not line.startswith(name + '=')]
lines.append(name + '=' + Fernet.generate_key().decode())
path.write_text('\n'.join(lines) + '\n')
path.chmod(0o600)
```

환경 파일 변경 후 서버를 재시작한다. 운영 환경은 일반 배포 절차를 따른다. 키는 터미널 출력·Git·채팅에 남기지 않는다. 기존 배포 백업은 SQLite 스냅샷과 `server.env`를 암호화된 restic 백업에 함께 보관한다. 복원 시 해당 키를 함께 복원한다. 키를 잃었다면 새 키를 설정한 뒤 사용자가 PAT를 다시 연결해야 한다.

토큰은 사용자 ID와 함께 Fernet으로 인증 암호화한 뒤 SQLite에 저장한다. API 응답·로그·localStorage에는 토큰을 넣지 않는다. 연결 해제는 현재 DB에서 암호문을 삭제하며 기존 이슈·공유 기록은 남긴다. GitHub 토큰 자체와 백업에 남은 토큰의 사용 권한을 폐기하려면 GitHub 설정에서 토큰을 취소한다.

## 토큰 설정과 확인 범위

- GitHub에서 Resource owner, 만료일, Only select repositories를 지정한다.
- Repository permissions → **Issues: Read and write**를 부여한다. Contents 쓰기는 필요하지 않다.
- 조직 승인이 필요한 경우 승인 완료 후 사용한다. Fine-grained PAT가 지원하지 않는 조직·외부 협업자 접근은 GitHub의 제한을 따른다.
- 앱은 `/user`, `/repos/{owner}/{repo}`를 조회해 계정·접근·공개 범위·Issues 사용·보관 여부를 확인한다.
- 조회 성공이나 저장소의 `permissions.push`는 이슈 생성 권한의 증거가 아니다. 쓰기 권한은 항상 **설정 확인 필요**로 표시하며 사용자가 토큰 설정을 확인한다. 검증용 이슈를 만들지 않는다.
- `X-Accepted-GitHub-Permissions`는 엔드포인트에 필요한 권한이며 현재 토큰의 실제 권한 목록이 아니다.
- 등록 직전에 계정·저장소 ID·공개 범위·활성 상태를 재조회한다. 이후 GitHub가 실제 권한을 최종 판단하며 거절 시 초안을 보존한다.

공식 자료: [이슈 생성 API](https://docs.github.com/en/rest/issues/issues#create-an-issue), [Fine-grained PAT 권한](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens), [PAT 관리와 제한](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

## 공유 데이터와 오류 처리

- 노트의 현재 저장 버전 또는 명시적으로 등록된 학습·개념을 Markdown으로 만든다. 공유하면서 새 개념이나 관계를 추론하지 않는다.
- 기존 ontology v1의 개념 ID·대표명·별칭·정의·범위·관계 유형과 방향·주장·근거·출처 버전을 포함한다. 개념 공유 시 연결된 출처의 본문 전체나 관계없는 노트는 넣지 않는다.
- 수정한 노트를 재등록하지 않았다면 예전 버전의 그래프 연결을 최신 내용에 붙이지 않는다. 개념 스냅샷의 오래된 근거는 출처 상태로 구분한다.
- 내부 이미지 주소는 생략하고 별도 첨부 안내를 표시한다. 사용자가 GitHub 에디터에서 직접 첨부한다.
- 공유 편집은 원본과 그래프를 변경하지 않는다. 초안은 기존 노트와 같이 사용자별 localStorage에 임시 보관한다. 제목·본문·공개 범위·작성 계정을 확인한 뒤에만 등록한다.
- SQLite에 원본 종류·ID·스냅샷 해시·저장소 ID·작성자·보낸 본문·요청 ID·이슈 URL을 기록한다. 같은 원본 스냅샷과 저장소에는 하나의 이슈만 생성한다. 기존 이슈의 자동 업데이트·동기화는 하지 않는다.
- 명확한 GitHub 4xx 거절은 `failed`로 저장해 재시도할 수 있다. POST 시간 초과·5xx·서버 재시작은 `unknown`이다. 이 경우 자동 재전송하지 않는다.
- 결과 미확인 상태에서는 GitHub 목록을 먼저 확인하고 이슈 URL을 입력한다. 숨겨진 요청 표식·저장소 ID·작성자를 확인한 뒤 기록을 연결한다. 실제 이슈가 없다면 보관된 원문과 표식을 복사하여 같은 계정으로 GitHub에서 수동 등록한 뒤 연결할 수 있다.
- GitHub 인증 오류를 앱의 HTTP 401로 반환하지 않는다. GitHub 토큰 만료가 Code Trainer 로그인 만료로 처리되지 않는다.

## 검증

`python -m unittest backend.test_github_sharing`은 외부 API를 MockTransport로 대체한다. 토큰·소유권·URL 검증, 출처 내보내기, 권한 재검사, 중복 요청, 시간 초과와 복구를 검증하며 실제 GitHub 이슈를 만들지 않는다.
