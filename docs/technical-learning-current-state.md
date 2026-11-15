# 기술 학습 중심 개편 — 현재 구조 조사

- 조사일: 2026-11-15
- 대상 기준: `e67961217b58ba0aee9c5fa99d3995ed7d9fb497` (main, PR #61 병합)
- 연결 계획: [PLAN.md](../PLAN.md), 계획상 Issue 01
- 상태: **기준 main 조사 완료**. 아래는 구현 전 기준 상태의 기록이다. 후속 구현과 실제 검증 결과는 [전환·검증 기록](technical-learning-release.md)을 따른다.
- 최초 조사 범위: 계획·조사 문서와 화면 증거. 이 조사 당시 제품 코드·운영 설정·사용자 데이터는 변경하지 않았다.

## 1. 작업 폴더·저장소·운영 상태

| 구분 | 확인 결과 | 의미 |
| --- | --- | --- |
| 원래 작업 폴더 | `release/second-brain-redesign`, HEAD `8349652` | 현재 운영 main과 다름. 이 폴더를 실행해 운영 UI라고 판단하면 안 됨 |
| 원래 미완료 변경 | `PLAN.md` 로컬 변경, 미추적 에이전트/스킬/디자인/배포 설계 파일 | 이번 작업에서 손대거나 임의로 커밋하지 않음 |
| 조사 worktree | `docs/technical-learning-redefinition`, 기준 `e679612` | 최신 main의 코드를 조사하고 기존 PLAN을 별도 보존 |
| 기존 이슈 | 열린 Issue 없음, #1~#7 모두 CLOSED | 기초 구현 학습 이슈다. 새 14개 계획의 완료로 재사용하지 않음 |
| 운영 배포 기록 | release-state `e679612`, `phase=complete` | 2026-11-15 확인 시 마지막 배포 기록 |
| 운영 컴포넌트 | frontend `e679612`, backend `98a0a07` | 이후 변경이 프런트엔드만이므로 컴포넌트 SHA가 다른 것은 기록상 정상 |
| 서비스 상태 | 로컬 `/healthz` 정상, 모니터 API/runner 정상 | 건강 상태 확인이며 전체 사용자 시나리오 검증을 뜻하지 않음 |
| 백업 기록 | 마지막 성공 2026-11-14 19:30 UTC (11-15 04:30 KST) | 상태 파일 확인만 수행. 이번 조사에서 운영 복원은 실행하지 않음 |
| 남은 운영 한계 | 모니터의 전체 재부팅 미검증·다른 기기 복구 미준비 | Issue 02/14에서 검증·문서화할 항목 |

이 표는 확인 시점의 관찰이다. 배포 설계 문서의 오래된 커밋·완료 표기를 현재 운영 상태와 혼동하지 않는다. 비밀키·개인 자료·운영 DB 본문은 조사 문서나 화면에 담지 않았다.

## 2. 현재 라우트와 정보 구조

[frontend/src/main.tsx](../frontend/src/main.tsx)와 [Navigation.tsx](../frontend/src/Navigation.tsx)를 기준으로 분류했다. 주요 메뉴는 아직 등록하기 / 탐구하기 / 데이터 쌓기 / 응용하기 / 설정이다.

| 현재 진입점 | 실제 화면·구현 | 개편 시 역할 |
| --- | --- | --- |
| `/` | `App.Home`, 자료 축적·그래프·응용의 소개와 기존 코딩 과정 목록 | 오늘의 학습으로 교체할 대상. 현재는 학습/복습/미해결 질문의 통합 홈이 아님 |
| `/library`, `/library/new/reference`, `/library/:id` | `Library`, 원자료 목록·텍스트/URL/파일 등록·원문 버전·해석 진입 | 학습 자료의 입구로 재사용 |
| `/references/new`, `/references/:id` | `ReferenceNotes`, 노트 에디터·버전·개념 등록·개별 ZIP | 직접 작성과 사용자 설명 보존에 재사용. 기술 레퍼런스와 역할 정리 필요 |
| `/inbox` | `FeedInbox`, 공개 RSS/Atom 수집 후 원문 등록 | 유지, 학습 자료의 수집 경로에 통합 |
| `/explore`, `/interpretations/:id` | `Interpretations`, 저장 원자료 버전의 해석 문서 | 학습 자료 상세의 개념 학습으로 연결 |
| `/learn/:id`, `/learn/:id/units/:unitId`, `/practice/:id` | 기존 자료 기반 개념·단원·코드 문제 | 유지, 새 탐색에서 정확한 위치로 재개 |
| `/explore/practice`, `/worksheets/:id`, `/foundations/*`, `/framework-practice`, `/problem-books/*` | 질문지·기초 구현·프레임워크·문제집 | 학습 유형·초안·채점 경계를 보존하며 연결 |
| `/reviews`, `/reviews/:id`, `/reviews/material/:id`, `/reference-reviews/:id` | 코드 복습·자료 간격 복습·노트 설명 검토 | 오늘의 복습에 통합하되 데이터/상태를 억지로 같은 점수로 합치지 않음 |
| `/questions`, `/questions/:id` + 공통 `QuickQuestion` | 독립 질문·가이드·자료 연결·해결/재열기·꼬리질문 트리 | 전역 진입을 재사용하고 생성 맥락·다중 대상 연결·추천 상태 보완 |
| `/knowledge/candidates/*`, `/knowledge` | 검토 자료 후보·명시적 그래프 등록·학습 그래프 | 필요한 근거·관계를 재사용. 수동 등록을 레퍼런스 필수 관문으로 두지 않음 |
| `/project-brain/*` | `Wiki`와 legacy `ProjectBrain`가 같은 경로 아래 공존 | 내보내기와 공유 의존성 처리 후 전환 안내·진입점 정리 |
| `/apply`, `/apply/explorations/*` | `DeepInside`, 그래프 제안·채택한 탐구 | 학습 추천에 필요한 부분을 확인해 분리 |
| `/me`, `/settings/*`, `/admin/*` | 학습 기록·AI·GitHub·운영 | 보조 경로·권한 유지 |

현 라우트는 단순 삭제/일괄 리다이렉트 대상으로 볼 수 없다. `feed_post_id`, 버전, 문제/단원 ID, 복습 모드, 검색 조건과 사용자 초안의 실제 참조를 이관 전에 확인해야 한다.

## 3. 자료 입력·학습·복습 계약

| 영역 | 코드로 확인한 사실 | 그대로 유지할 것 / 남은 차이 |
| --- | --- | --- |
| 텍스트·URL·RSA 등록 | [resources.register](../backend/resources.py), `resource_requests`, `resource_versions`, `resource_feed_posts`; [Library](../frontend/src/Library.tsx)에서 등록 초안·요청 ID와 revision 관리 | 등록 자체는 AI 생성과 분리되어 있음. 기존 문서의 ‘RSA 완료가 AI 성공에 묶임’은 현 구현 전체에 그대로 적용할 수 없음 |
| URL 수집 | 등록 요청·수집 상태·오류를 저장하고 원자료 버전을 보관 | 실제 네트워크 실패/재수집/중복 URL 시나리오는 후속 검증 필요 |
| 해석 | [interpretations.begin/generate](../backend/interpretations.py), 원자료 ID/버전과 별도 작업 상태·요청 기록 | 원문 저장과 별도. 해석 이후 코드 문제는 또 다른 요청 경로 |
| 원문·노트 연결 | [resources.link_note](../backend/resources.py), [reference_notes.save/archive](../backend/reference_notes.py) | 자료·노트를 독립된 중복 원본으로 새로 복제하지 말고 현재 연결·버전 의미 확인 |
| 코드 풀이 | [Practice.tsx](../frontend/src/Practice.tsx), [practice.py](../backend/practice.py), service/runner | 저장 revision, 일반 풀이·복습 모드, 결과와 실행 장애 구분 보존. 이번 조사에서 실제 실행기를 새로 돌리지는 않음 |
| 복습 | `practice.queue`의 코드 복습과 [spaced_reviews.queue](../backend/spaced_reviews.py)의 자료 복습, reference review가 별도 | 새 홈은 각 대상을 정확한 재개 URL로 집계. 하나의 임의 숙달 점수로 바꾸지 않음 |
| 기술 레퍼런스·Skill | 기존 노트/근거/위키의 일부 재사용 후보는 존재 | 사용자가 제시한 최소 레퍼런스 계약·Skill 패키지 전체를 이미 구현한 것으로 간주할 근거 없음 |

## 4. 질문과 추천의 현재 간극

- [App.tsx](../frontend/src/App.tsx)의 공통 헤더에서 로그인한 사용자에게 `QuickQuestion`을 제공한다. `Outlet`을 떠나지 않고 질문 창을 연다.
- [QuickQuestion.tsx](../frontend/src/QuickQuestion.tsx)는 3줄 자동 줄바꿈, 최대 500자, 로컬 React state, 명시적 저장 버튼을 쓴다. 생성 위치의 자료/단원/문제/레퍼런스를 조회하거나 저장 payload에 전달하지 않는다.
- [questions.Create](../backend/questions.py)는 `request_id`, `text`, `parent_id`를 받는다. `Update`는 맥락 문자열·자료 links·note_id·open/done·revision을 받는다. 현재 links는 원자료 구절 연결이며 여러 대상 종류를 표현하는 공통 맥락 계약은 아니다.
- 저장과 AI 가이드는 분리되어 있고 사용자가 해결/재열기를 선택한다. 꼬리질문은 부모 ID로 연결되며 목록 검색에서도 상위 맥락을 포함하고 부모 삭제 시 자식을 보존한다.
- QuickQuestion의 입력은 앱 재시작/페이지 새로고침 후 복구할 영속 초안이 아니다. 저장 실패 후 다시 누를 때 같은 `request_id`를 재사용하지 않으므로 서버의 중복 방지 기능만으로 이 UI의 응답 유실 재전송까지 보장하지 않는다.
- ‘오늘의 질문’은 미해결 질문을 다시 추천하는 목록이 아니다. `questions.daily_candidates`가 RSA 글과 유효한 Deep Inside bundle 제안을 선택한다. 피드 추천에는 AI 처리가 연결된다.
- `question_memos`에는 추천 미루기·숨김·노출 이력 정책이 없다. `open/done`에 이를 섞어 저장하지 않아야 한다.
- [insight_context.build](../backend/insight_context.py)는 활성 `knowledge_sources`, 지원 근거와 개념 관계를 중심으로 입력을 구성한다. 현재 학습 진도·복습 일정·미해결 질문을 포괄한 학습 추천 계약과 다르다.
- 기존 insight의 입력 fingerprint·출처 재검증·중복 요청·상태 처리는 Issue 08의 재사용 후보다. 코드 존재만으로 새 추천의 정확한 근거·무효화 요구가 충족되지는 않는다.

## 5. 삭제 전에 풀어야 할 공유 의존성

| 제거/축소 후보 | 확인한 연결 | 먼저 필요한 조치 |
| --- | --- | --- |
| Deep Inside | `questions.py`가 `insight_context`, `insight_bundles`, `explorations`, `insight_skips`를 사용 | 오늘의 질문/제안을 새 홈 계약으로 이관하거나 호환 경로를 분리한 뒤 삭제 |
| 그래프 기반 추천 | insights → insight_context → ontology의 개념/관계/근거/출처 | 새 추천 입력 계약을 검증한 뒤 범용 추천 부분만 제거 |
| Wiki | [wiki.export](../backend/wiki.py)가 `project_brain.sources/source_view`를 사용 | legacy brain 원자료 보존/내보내기보다 `project_brain.py`·테이블을 먼저 삭제하면 안 됨 |
| Legacy ProjectBrain | resources의 특정 버전 스냅샷, GitHub 자료 가져오기, AI 설정·사용량과 연결 | 공유 원자료·설정·사용량을 보존하고 일반 개인 기록/전용 UI만 분리 |
| 명시적 지식 등록 | 노트·검토 자료·단원·기초 학습이 ontology/knowledge_source를 사용 | 새 레퍼런스가 필요한 근거를 확보한 뒤 중복 사용자 절차만 축소 |
| 시작 시 복구 | [db.initialize](../backend/db.py)와 [service.initialize](../backend/service.py)가 wiki/brain/insight/질문 등의 스키마와 중단 작업을 함께 처리 | UI만 숨긴 후 초기화/복구 SQL까지 없는 테이블을 참조하지 않도록 단계적 분리 |
| 자료 보관/삭제 | resource/note archive가 지식 출처 상태·리뷰 대상과 연결 | 새 화면에서도 근거 stale/deleted와 과거 이력의 의미 보존 |

### 예약·비동기 실행 경계

[api.lifespan](../backend/api.py)은 두 반복 작업을 시작한다.

1. `feeds.poll`: 30초마다 점검하고 활성 출처를 refresh한다. refresh 내부의 수집 간격 제한과 중복 방지를 유지하며 RSA 수집 자체는 남긴다.
2. `insight_schedule.poll`: 30초마다 예약을 확인한다. 기본 꺼짐이며, 활성화한 소유자에 대해 주간 점검·입력 변경·예산(기간 내 자동 시도 상한)을 확인하고 insight를 생성할 수 있다. 메뉴를 숨기는 것만으로 이 호출은 중단되지 않는다.

위키 compile/query/lint, brain 초안, 자료 해석, 질문 가이드 등은 API 요청과 BackgroundTasks를 통해 시작한다. wiki 전용 반복 poll이 lifespan에 있는 것으로 확인되지는 않았다. 운영의 배포·모니터·백업 launch agent는 학습 제품 범위 제외와 별개이므로 유지한다.

## 6. 보존·내보내기 현황

| 기존 경로 | 코드상 포함 범위 | Issue 02에서 확인할 간극 |
| --- | --- | --- |
| `GET /api/wiki/export` | 현재 wiki 페이지, 전체 문서 버전, 활동 로그, project-brain 원자료 Markdown, index/AGENTS | 모든 `wiki_page_versions`를 순회하는 완전한 페이지 버전 export는 아님. ZIP을 곧 전체 DB 복원물로 간주하지 않음 |
| `GET /api/project-brain/records/{id}/export` | 현재 기록·주장·링크·인용 원자료 스냅샷 Markdown | 기록의 전체 버전·모든 개인 기록 일괄 패키지·재가져오기까지 보장하지 않음 |
| `GET /api/reference-notes/{id}/export` | 노트·버전·관련 개념/근거/별칭/관계 manifest와 이미지 ZIP | 질문·풀이·복습·위키 전체를 포함하는 서비스 일괄 export가 아님 |
| `scripts/backup.py` 및 운영 backup | SQLite backup API, 무결성 검사, 운영 restic 백업 | 실제 복원·대표 데이터 재열기·범위 검증은 별도. 개인 DB를 PR이나 공개 첨부에 넣지 않음 |

질문·학습·도움 사용·복습·개인 기록·위키 버전의 보존 표를 작성하고, 대표 fixture의 round-trip 검사 후 제외 기능을 정리해야 한다. 이 조사에서는 운영 데이터 내보내기·삭제·복원을 수행하지 않았다.

## 7. 실제 화면 증거

아래는 **현재 main 코드를 로컬 빌드한 화면**이다. 운영 DB를 복사하지 않고 별도의 임시 DB에 ‘조사 예시’ 자료 2개와 질문 1개를 넣었다. 실제 AI·RSS 수집·예약 생성은 껐다. 샌드박스 없음 안내는 이 격리 환경의 상태이며 운영 실행기 장애의 증거가 아니다.

환경: macOS Chrome, 반응형 viewport 1440×1000 / 390×1000, 원본 크기 전체 페이지 캡처. 네 파일을 모두 열어 내용과 상태를 확인했다. 실제 모바일 기기·가상 키보드·모든 브라우저의 검증을 뜻하지 않는다.

| 화면 | 증거 | 확인한 내용 |
| --- | --- | --- |
| 자료 목록 1440px | [데스크톱 캡처](technical-learning-evidence/2026-11-15/library-desktop.png) | 5개 영역의 메뉴, 등록/노트/보관 동작, 검색·종류·세로 자료 목록 |
| 자료 목록 390px | [모바일 캡처](technical-learning-evidence/2026-11-15/library-mobile.png) | 검색·필터·자료 목록은 세로 배치. 상단 세 버튼은 짧은 폭에서 글자가 여러 줄로 나뉨 |
| 자료 화면의 전역 질문 390px | [질문 창 캡처](technical-learning-evidence/2026-11-15/question-entry-mobile.png) | 페이지 이동 없이 하단 질문 창과 저장/닫기. 생성 자료·단원 선택/해제 UI는 현재 없음 |
| 홈 1440px | [홈 캡처](technical-learning-evidence/2026-11-15/home-desktop.png) | 등록·탐구·그래프·응용 소개와 ‘기존 코딩 과정’. 오늘의 이어서 하기/복습/질문 통합 홈이 아님 |

### 화면에서 도출한 변경 경계

- 이미 세로 목록인 자료 보관함을 ‘모든 화면이 테이블’이라는 가정으로 다시 만들 필요는 없다. 목록 구조와 house controls를 재사용하되 정보와 다음 행동을 학습 중심으로 바꾼다.
- 주요 메뉴가 내부 처리 단계별로 갈라져 있다. 사용자 목표별 세 메뉴로 정리하는 데는 공통 탐색과 상세 진입의 계약이 필요하다.
- 홈의 큰 소개 영역과 단계 설명보다 실제 이어서 할 대상이 우선하는 구조가 필요하다. 현재 목록이 비어 있는 이 fixture로 기존 사용자 전체의 완료·재개 흐름을 평가하지 않는다.
- 모바일 질문 창은 기존 맥락 위에 올라온다. 실제 키보드가 열린 상태와 코드 초안 보존은 이번 정적 캡처만으로 통과시킬 수 없다.

## 8. 다음 구현 경계와 미검증

1. **Issue 01 잔여:** 실제 단원→문제→돌아오기, 일반/복습 초안, 해석→질문지/코드 실습, 레퍼런스/위키 이력의 대표 흐름을 추가 실행하고 공유 의존성 표를 보완한다. Issue 01은 계속 진행 중이다.
2. **Issue 02:** 현재 export를 대표 fixture로 다시 읽고 누락된 페이지/기록 버전과 질문·학습 묶음의 범위를 확정한다. 복원 검증은 운영 파일을 덮지 않는 격리 환경에서 수행한다.
3. **Issue 03:** 이번 실제 캡처를 기준으로 세 메뉴·학습 홈·읽기 상세·모바일 질문의 시안을 만든다. 현재 화면을 새 설계의 승인 결과로 취급하지 않는다.
4. **Issue 06~08:** 질문의 대상 연결/출처 맥락과 추천 선택 상태를 별도로 정의하고, 캐시 입력·시간 정책·완료 시 무효화를 검증한다.
5. **Issue 10~13:** 새 레퍼런스의 근거 계약과 보존 경로를 확보한 후 일반 위키·수동 그래프 등록 관문·범용 추천을 정리한다.

| 검사 | 이번 실행 결과 |
| --- | --- |
| 현재 main 빌드 | `npm --prefix frontend ci` 및 `npm --prefix frontend run build` 통과. 기존 bundle 크기 경고 존재 |
| 브라우저 대표 화면 | 실제 앱 + 임시 DB, 위 네 화면 캡처·열기 확인 |
| 정책 문서/Issue 중복 | 현재 코드와 기존 계획 대조, 열린 Issue 없음 확인 |
| 제품 회귀 테스트/실제 코드 실행 | 이번 문서 변경에서 재실행하지 않음 |
| 실제 AI 추천·해석 품질/유료 호출 | 실행하지 않음 |
| URL/RSA 실제 수집·실패·재시도 | 코드 조사만 수행, 이번 fixture에서는 수집 중단 |
| 실제 모바일 키보드/뒤로 가기·위치 복원 | 미검증 |
| 운영 DB 내용·복원·데이터 이전 | 접근/실행하지 않음. 건강 상태와 운영 상태 파일만 읽음 |
| 신규 제품 개편 배포 | 수행하지 않음 |

기존 PR #59~#61의 통과/배포 기록은 해당 변경의 근거이며, 이번 제품 개편 전체의 완료 근거로 쓰지 않는다.
