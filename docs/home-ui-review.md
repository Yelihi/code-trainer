# 홈·질문 다시보기 설정 개선 · 2026-11-17

대상: `feat/technical-learning-redesign`. 사용자 피드백은 홈의 긴 펼침 설정 폼과 기본 숫자 입력이 학습 흐름을 방해한다는 점이었다. 회색/흰 표면, 보라/분홍, 플랫폼 산세리프는 유지한다.

## UI 플러그인에서 확인한 화면

유아이볼에서 `학습`, `설정 + 라디오버튼`, `대시보드`를 검색해 반환된 대표 이미지를 직접 확인했다. 검색 메타데이터의 총 결과 전체를 검토한 것은 아니다. Mobbin은 이전의 유료 플랜 거절 상태가 해소되지 않아 재호출하지 않았다.

- [플랭 · 학습 전](https://uibowl.io/name/%ED%94%8C%EB%9E%AD?patterns=%EB%A9%94%EC%9D%B8&patternName=%ED%95%99%EC%8A%B5%20%EC%A0%84) — 중앙 학습 콘텐츠와 하단의 큰 ‘오늘의 학습 시작하기’ 버튼. 홈에서 하나의 이어하기 행동을 먼저 보여주는 판단에 참고했다. 캐릭터·이미지·연속 학습 통계는 가져오지 않았다.
- [퍼블리 · 알림설정](https://uibowl.io/name/%ED%8D%BC%EB%B8%94%EB%A6%AC?patterns=%EC%84%A4%EC%A0%95&patternName=%EC%95%8C%EB%A6%BC%EC%84%A4%EC%A0%95) — 흰 설정 행의 왼쪽 라벨과 오른쪽 토글, 아래 별도 안내 문구. 질문 표시 설정도 라벨/설명과 작은 오른쪽 값으로 분리했다. 숫자 설정을 토글로 바꾸지는 않았다.
- [바나프레소 · 포장/픽업 예정시간](https://uibowl.io/name/%EB%B0%94%EB%82%98%ED%94%84%EB%A0%88%EC%86%8C?patterns=%EC%84%A4%EC%A0%95&patternName=%ED%8F%AC%EC%9E%A5%2F%ED%94%BD%EC%97%85%EC%98%88%EC%A0%95%EC%8B%9C%EA%B0%84%20%EC%84%A4%EC%A0%95) — 짧은 항목과 현재 값·이동 표시를 분리한 주문 설정 행. 큰 입력폼보다 짧은 값 표현을 쓰는 판단에 참고했다. 결제 화면 구성은 채택하지 않았다.
- [Moodpress · 대시보드 편집](https://uibowl.io/name/Moodpress?patterns=%EC%84%A4%EC%A0%95&patternName=%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C%20%ED%8E%B8%EC%A7%91) — 닫기 버튼이 있는 별도 설정 표면과 그룹화한 행 목록. 설정을 주 콘텐츠와 분리하는 점만 참고했고 삭제·드래그 정렬은 도입하지 않았다.

헬로우봇의 미션 빈 화면, 플리토의 참여 카드, 에이닷 계정 연결 모달도 반환됐지만 학습 이어하기/질문 주기 설정과 맞지 않아 채택하지 않았다. 인프런 앱명 조회는 일치 결과가 없었다. 검색 태그에 라디오버튼이 있더라도 대표 이미지에 보이지 않는 라디오 UI를 관찰했다고 주장하지 않는다.

## 바꾼 흐름

1. 홈 첫 행동은 마지막 학습 이어가기다. 그라데이션 배너를 흰 콘텐츠 표면과 명확한 주 행동으로 바꿨다.
2. 복습 → 남겨둔 질문 → 다른 진행 학습 순서다. 모바일의 시각 순서와 DOM/키보드 순서도 일치한다.
3. 질문 추천 숫자 폼을 홈에서 제거했다. 질문 제목 옆 설정 버튼 또는 설정 메뉴에서 `/settings/questions`로 이동한다.
4. 설정 화면은 항목 4개를 짧은 라벨/보조 설명/작은 숫자/단위 행으로 표시한다. 1~365일, 1~90일, 1~10개 제한과 임의 정수 설정을 유지한다. 거대한 입력과 네이티브 스핀 버튼 대신 직접 입력·키보드 화살표를 사용한다.
5. AI 제안은 학습 활동 아래의 보조 영역이다. 홈을 열어도 AI 요청은 시작하지 않는다. 생성 버튼을 누를 때만 기존 API를 호출한다. 연결 기록은 기본 펼침 상자 대신 짧은 링크 목록으로 보인다.
6. 홈의 빈 상태 설명을 줄이고 질문함 이동을 명시했다. 숨김/미루기는 해결 처리하지 않으며 한국 시간 기준과 기존 기록을 유지한다.

## 화면과 검증

- [홈 1440px](technical-learning-evidence/2026-11-16-uibowl/home-refresh-home-1440.png) · [홈 390px](technical-learning-evidence/2026-11-16-uibowl/home-refresh-home-390.png)
- [설정 1440px](technical-learning-evidence/2026-11-16-uibowl/home-refresh-policy-1440.png) · [설정 390px](technical-learning-evidence/2026-11-16-uibowl/home-refresh-policy-390.png)
- [이전 홈 1440px](technical-learning-evidence/2026-11-16-uibowl/home-before-refresh-1440.png) · [이전 홈 390px](technical-learning-evidence/2026-11-16-uibowl/home-before-refresh-390.png)
- [검사 코드](technical-learning-evidence/2026-11-16-uibowl/home-check.mjs) · [검사 결과](technical-learning-evidence/2026-11-16-uibowl/home-refresh-checks.json)

화면의 콘텐츠는 격리한 예시 fixture다. 실제 사용자 설정·기록·AI 사용량을 바꾸지 않았다. 기존 홈 캡처는 11월 16일의 직전 UI이며 이후 홈 검사에서 덮어쓰지 않도록 별도 보관했다.

1440/1024/768/390px 홈/설정 8건, 네이티브 숫자 범위·빈 값 검증, 저장 실패 시 입력 유지, 로딩 스피너, 나머지 설정 값 보존, 홈 반영, 자동 AI 호출 없음, 명시적 AI 요청, 빈 상태와 오류 재시도를 확인한다. 기존 17개 페이지의 68건 회귀 검사도 유지한다.

후속 미세 조정: ‘질문함 열기’ 호버의 사방 패딩을 8px/12px로 맞췄다. 실습문제 생성의 예제 시작 카드를 제거했고, Markdown 입력은 10행·최소 320px(모바일 260px), 짧은 placeholder로 바꿨다. 예제를 가리키던 AI 미연결 안내는 설정 링크로 교체했다. 1440/390px에서 입력 높이·placeholder 공간, 예제 제거, URL 전환·Markdown 파일 불러오기와 호버 여백을 확인했다. 실제 생성 요청은 실행하지 않았다.

## 다음 학습 제안 상태 구성 · 11월 17일 후속

줄글만 남았던 제안 영역은 [토스 TDS Result](https://tossmini-docs.toss.im/tds-mobile/components/result/)의 상태 시각 요소·제목·짧은 설명·행동 구성을 참고해 수정했다. 기존 색과 아이콘 체계를 유지하며 흰 패널 안에 상태와 생성 버튼을 묶었다. 모바일은 버튼을 전체 폭으로 표시한다. 요청 시 AI 사용과 7일 재사용 조건은 패널 아래 아이콘 정보 행으로 분리했다.

초기 로드는 스켈레톤, 실제 생성은 버튼 중앙 스피너와 상태 문구로 구별한다. 조회 오류는 다시 불러오기, 생성 오류는 오류 내용과 재생성 버튼을 제공한다. 제안이 있으면 기존 연결 기록과 행동을 유지하고 재생성 중에도 내용을 숨기지 않는다. 자동 AI 생성은 추가하지 않았다.

검증: 기존 홈·설정 8건에 1440/390px 제안 상태 5종(빈 상태·생성 중·생성 실패·조회 실패·완료) 10건을 추가했다. 가로 넘침, 중앙 스피너·비활성화, 오류 재조회, 재생성 중 기존 결과 보존을 확인했다. 빌드와 lint 통과. 실제 AI 요청은 fixture로 대체했다.

- [빈 상태 데스크톱](technical-learning-evidence/2026-11-16-uibowl/recommendations-empty-1440.png) · [모바일](technical-learning-evidence/2026-11-16-uibowl/recommendations-empty-390.png)
- [생성 중](technical-learning-evidence/2026-11-16-uibowl/recommendations-running-390.png) · [오류](technical-learning-evidence/2026-11-16-uibowl/recommendations-failed-390.png)
