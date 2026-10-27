# Second Brain release 테스트·유지보수 안내

대상: `release/second-brain-redesign`. 이 안내의 기능은 release용이며, `main`과 운영 Mac 서버에 배포됐다는 뜻이 아니다. 최초 설계 초안보다 이 안내와 흐름별 구현 문서를 우선한다.

## 개발 환경에서 열기

현재 작업 폴더의 미커밋 문서를 보존하려면 별도 worktree를 사용한다. 아래 경로가 이미 있으면 새 경로를 선택한다.

```sh
git fetch origin
git worktree add --detach ../code-trainer-release-test origin/release/second-brain-redesign
cd ../code-trainer-release-test
uv venv --python 3.12 .venv
uv pip sync --python .venv/bin/python requirements.txt
```

루트 `.env.example`을 `.env`로 복사하고 기존에 사용하던 개발용 AI 설정을 넣는다. 기존 `.env`를 직접 복사해 같은 AI 연결을 사용할 수도 있다. `.env`를 커밋하지 않는다. 개인 API 키를 화면에서 저장하려면 `TRAINER_AI_ENCRYPTION_KEY` 또는 기존 `TRAINER_GITHUB_ENCRYPTION_KEY`가 필요하다. 이미 암호화해 저장한 데이터가 있으면 암호화 키를 임의로 교체하지 않는다. [AI 설정 정책](ai-settings-plan.md), [암호화 키 초기 설정](github-sharing.md).

터미널 1:

```sh
cd backend
./dev.sh
# 종료: ./dev.sh stop
# 기존 개발 서버를 종료하고 이 작업 폴더에서 재시작: ./dev.sh restart
```

터미널 2, 테스트 worktree 루트에서:

```sh
cd frontend
npm ci
npm run dev
```

| 대상 | 개발 환경 |
| --- | --- |
| 브라우저 | `http://127.0.0.1:5173` |
| FastAPI | `127.0.0.1:8011` |
| DB | 해당 worktree의 `data/dev/trainer.sqlite3` |
| 코드 실행 | Colima `code-trainer-dev`, `code-trainer-runner:dev` |
| AI | `.env`의 로컬 공통 설정 또는 해당 사용자 개인 설정 |

`npm run dev`는 프론트엔드만 실행한다. SQLite는 별도 DB 서버를 띄우지 않는다. `backend/dev.sh`가 개발 실행 VM을 준비하므로 Docker CLI와 Colima가 필요하다. 개발 DB의 계정은 운영 DB와 별개다. 새 DB에서는 첫 계정을 만들고, 기존 개발 DB라면 그 DB의 계정으로 로그인한다. 포트가 점유됐으면 `lsof -nP -iTCP:8011 -sTCP:LISTEN`으로 소유 프로세스를 먼저 확인한다.

## 권장 확인 순서

1. **등록하기 → 레퍼런스 등록**: 텍스트/Markdown 또는 URL을 저장한다. 파일 버튼과 화면 전체 드롭으로 `.md`/`.txt`를 추가하고 파일 이름이 표시되는지 확인한다. 작성 중 다른 화면으로 이동할 때 계속 작성은 내용을 유지하고 이탈은 임시 글을 삭제해야 한다. 등록 단계에 언어·난이도 선택이나 AI 생성이 필요하지 않다. 제목만 바꾸면 본문 버전이 유지되고, 본문을 바꾸면 새 버전이 생기는지 확인한다. 직접 노트는 기존 노트 편집·이미지·보관/복원 기능을 사용한다.
2. **탐구하기 → 해석하기**: 저장한 원문 버전을 선택해 AI 해석을 만든다. 출처 버전과 섹션을 확인한다. 질문지를 만들고 자신의 답변·요약을 저장한다. 코드 실습은 해석 섹션에서 언어·난이도를 선택해 생성한다. 자료구조·알고리즘 카탈로그도 실습하기에서 접근한다.
3. **정리 확인 → 데이터 쌓기**: 정확한 자료 버전을 검토 완료로 표시한다. 추출 가능 자료에서 AI 후보를 생성하고, 개념·관계·인용을 검토·수정한 뒤 명시적으로 그래프에 등록한다. 자료를 읽거나 AI 후보를 생성한 것만으로 등록되지 않는다. 사용자 작성 자료의 실제 설명 관찰과 AI 해석을 구분한다.
4. **복습에 추가 → 다시 검토**: 자료를 별도로 복습에 추가한다. 항목별 곡선에 다음 날의 복습 예정점이 표시되고, 마우스·키보드 선택 시 요구사항이 나타나는지 확인한다. 곡선은 실제 기억률 측정값이 아니라 복습 간격 안내다. 기한이 되면 직접 응답하고 다음 일정으로 이동한다. ‘설명할 수 있음’은3·7·14일, ‘다시 확인 필요’는1일이다. 열람만으로 완료되지 않는다. 기존 코드 복습은 도움·실패 기록을 반영하는 기존 규칙을 유지한다.
5. **응용하기 → Deep Inside**: 근거가 있는 개념 관계를 등록한 뒤 제안을 받는다. 질문·읽기·작은 실습 가이드와 출처를 확인한다. 채택하면 ‘나의 탐구’에서 내 예상·관찰·질문을 작성한다. 새 제안 묶음으로 바꿔도 채택 기록은 남는다. 건너뛴 연결은30일간 재제안에서 제외된다.
6. **설정**: GitHub 기본 저장소 등록과 AI 개인 연결을 확인한다. 저장소 등록만으로 외부 이슈를 게시하지 않는다. 예약 생성은 기본 꺼짐이다. 켜면7일 뒤부터 변경된 유효 그래프를 확인하며, 최근30일 자동 시도4회·호출당 최대4,000출력 토큰 한도가 적용된다. 실패·중단도 시도 횟수에 포함되고 금액 상한은 보장하지 않는다. 실제 AI 요청에는 연결한 제공자의 비용이 발생한다.

자료 변경·보관 후 과거 해석/학습/그래프 근거/복습/탐구가 최신 자료로 잘못 표시되지 않는지도 확인한다. 다른 창에서 같은 기록을 수정했을 때 입력이 사라지거나 자동으로 덮어써지면 안 된다.

## 유지보수할 때 찾을 곳

| 흐름 | 화면 | 서버 경계 / 주요 검사 |
| --- | --- | --- |
| 등록·본문 버전·RSA | `Library.tsx`, `ReferenceEditor.tsx`, `FeedInbox.tsx` | `resources.py`, `feeds.py`; `test_resources`, `test_feeds` |
| 해석·질문지·내 답변 | `Interpretations.tsx`, `Worksheets.tsx`, `PracticeRecords.tsx` | `interpretations.py`, `worksheets.py`, `practice_records.py`; 같은 이름의 테스트 |
| 해석 기반 코드 실습 | `InterpretationCode.tsx`, 기존 `Practice.tsx` | `code_practice.py` → 기존 `service.py`/`ai.py`/`runner.py`; `test_code_practice` |
| 검토·추출·등록 | `MaterialReview.tsx`, `KnowledgeCandidates.tsx`, `ReferenceKnowledge.tsx` | `materials.py`, `material_proposals.py`, `material_knowledge.py` → `ontology.py`; `test_material*` |
| 일반 자료 복습 | `SpacedReviews.tsx`, `Reviews.tsx`, `reviewCurve.ts` | `spaced_reviews.py`; `test_spaced_reviews`, `reviewCurve.test.ts` |
| Deep Inside | `DeepInside.tsx`, `Explorations.tsx`, `InsightSchedule.tsx` | `insight_context.py`, `insights.py`, `insight_adoptions.py`, `insight_schedule.py`; `test_insight*` |
| 개인 AI·GitHub | `AISettings.tsx`, `GitHubSharing.tsx` | `ai_settings.py`, `github_sharing.py`; `test_ai_settings`, `test_github_sharing` |
| 공통 경계 | `main.tsx`, `Navigation.tsx`, `App.tsx`, `api.ts` | `api.py` 인증 경로 → 도메인 모듈 → `db.connect(write=True)` |

프론트엔드는 `frontend/src/`, 서버는 `backend/` 기준이다. 기능별 모듈이 입력/owner/버전/상태 검사를 맡고, 기존 API 클라이언트·SQLite 트랜잭션·AI 호출/사용량·코드 실행 엔진을 재사용한다. 새 그래프 DB, 전역 상태 라이브러리, 메시지 브로커는 도입하지 않았다.

변경 시 시작 버튼부터 API·저장·화면 오류 처리까지 같은 흐름으로 확인한다. 주요 보존 규칙은 다음과 같다.

- 새 원문 본문 버전과 사용자가 검토한 정확한 버전을 혼동하지 않는다. 기존 노트의 버전 정책은 별도 유지된다.
- 후보와 확정 그래프, AI 설명과 사용자 작성/관찰, 복습 자기평가와 객관적 숙달 판정을 구분한다.
- AI 키·모델은 호출 시점의 owner 설정을 사용한다. 작업 모델/usage도 실제 호출 정보와 맞아야 한다.
- 유료 작업의 요청 재전송·동시 실행·재시작과 늦은 응답을 함께 검사한다. 실패한 새 결과로 기존 유효 결과를 지우지 않는다.
- 채택한 탐구는 임시 제안 정리 대상이 아니다. 원문 변경은 과거 근거의 상태를 바꾸며 기록 자체를 최신 내용으로 바꾸지 않는다.

정확한 전체 CI 명령은 [check.yml](../.github/workflows/check.yml)에 있다. 프론트엔드 `npm test`, `npm run typecheck`, `npm run lint`, `npm run build`와 변경한 서버 도메인 테스트를 먼저 실행한다. Python은 루트 `.venv/bin/python -m unittest backend.test_도메인 -q`를 사용한다. 코드 실행 경계를 변경하면 기존 Docker 샌드박스·카탈로그 검사도 필요하다.

## 검증 범위와 남겨둔 경계

P1–P16 기능은 흐름별 구현/테스트/리뷰와 release 대상 PR로 진행했다. 최신 기능 통합 상태에서 백엔드221개, 프론트엔드27개 테스트 및 타입·lint·build를 확인했다. CI에는 샌드박스와4개 카탈로그 분할 검사도 포함된다. 화면 검증에는 격리 DB와 가짜 AI 응답을 사용했다. 실제 제공자의 응답 품질·과금, 운영 Mac 서버의 DB 이행·성능은 사용자 테스트/배포 검증 대상이다.

FS 계획·검사·의미 검토는 각 흐름에 기록했다. 기능 구현 시점의 `.frontend-system/project.md`는 **partial** 기록이었으며, 기능별 검증을 전체 파일 정밀 분석 완료로 해석하지 않는다. 전체 분석의 최신 범위·기준 커밋·완료 여부는 해당 보고서의 상태를 확인한다. 이번 유지보수 표는 구현한 흐름의 실제 경계를 안내한다.

원문 영구 삭제/전체 파생 데이터 삭제, 재사용 가능한 절차 지식 모델, 자동 숙달 판정은 이번 기능 범위에 포함하지 않았다. 일반 raw 자료의 보관/복원 UI와 기존 노트의 보관/복원 기능도 동일하다고 가정하지 않는다. 새 본문 버전 정책은 [원문 등록](resource-library.md), 복습은 [일반 자료 복습](material-spaced-review-plan.md), 응용은 [생성](deep-inside-generation-plan.md)·[채택](deep-inside-adoption-plan.md)·[예약](deep-inside-schedule-plan.md)을 참고한다.
