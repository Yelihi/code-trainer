# 자료구조·알고리즘 학습 화면 정리 · 2026-11-16

대상: `feat/technical-learning-redesign`, 사전 생성 문제집의 개념 탐구 / 설명 / 구현·테스트 / 참고 풀이 / 피드백 / 검증 결과 / 테스트 도움말.

## 확인한 문제

- 1720px 실습 폭과 별도의 개념 폭, 고정 높이·최소 높이가 섞여 여백이 과도했다.
- 실험 안내가 main 바로 아래 문단으로 렌더링되어 다른 영역과 폭이 달랐고 시각화에 붙어 있었다.
- 단원 탭의 링크가 일반 본문 링크 스타일을 받아 정렬과 밑줄이 달랐다.
- 기존 초록 강조와 큰 단계 숫자, 왼쪽 테두리 피드백, 넓게 벌어진 조작 버튼이 현재 테마와 맞지 않았다.

## 적용

페이지 폭을 공통 1180px 상한으로 맞췄다. 섹션 사이 24px, 시각화/실험 안내 사이 16px, 섹션 내부 24px(모바일 20px)를 사용한다. 핵심 규칙·시각화·실험 안내·해설을 구분하고 설명 문단은 읽기 폭을 제한한다. 학습 내용과 문제·기준 풀이·시각화 좌표·프레임·검증 로직은 변경하지 않는다.

시각화는 그림/현재 단계 설명을 정렬하고, 오른쪽의 고정 높이를 제거한다. 단계 수는 작은 상태 표기로, 조작은 같은 폭의 4개 버튼으로 묶었다. 연결 리스트처럼 넓은 그림은 데스크톱에서 별도 전체 폭 행에 배치한다. 모바일에서 넓은 그림은 내부에서 가로 스크롤하며 문서 전체 폭을 밀어내지 않는다. 활성 상태는 보라색, 실제 성공·실패 표시는 기존 의미를 유지한다.

설명 입력과 글자 수, 코드/테스트 편집기, 참고 풀이, 피드백, 검증 결과를 같은 폭·간격으로 정리했다. 피드백의 왼쪽 테두리와 중첩 장식을 줄였다. 저장 중·AI 검토 중·코드 검증 중 버튼은 공통 loading 스피너를 사용한다. 테스트 도움말의 배경·탭·타이포그래피도 맞췄다.

디자인 방향은 [기존 참고 기록](ui-reference-directions.md)과 `DESIGN.md`를 따른다. 새 레퍼런스 화면을 조회했다는 의미가 아니다.

## 화면

| 화면 | 데스크톱 | 모바일 |
| --- | --- | --- |
| 최대공약수 개념 | [1440px](technical-learning-evidence/2026-11-16-uibowl/foundation-gcd-1440.png) | [390px](technical-learning-evidence/2026-11-16-uibowl/foundation-gcd-390.png) |
| 이전 최대공약수 | [이전](technical-learning-evidence/2026-11-16-uibowl/foundation-before-gcd-1440.png) | [이전](technical-learning-evidence/2026-11-16-uibowl/foundation-before-gcd-390.png) |
| 연결 리스트 | [1440px](technical-learning-evidence/2026-11-16-uibowl/foundation-linked-list-1440.png) | [390px](technical-learning-evidence/2026-11-16-uibowl/foundation-linked-list-390.png) |
| 스택 | [1440px](technical-learning-evidence/2026-11-16-uibowl/foundation-stack-1440.png) | [390px](technical-learning-evidence/2026-11-16-uibowl/foundation-stack-390.png) |
| 그래프 탐색 | [1440px](technical-learning-evidence/2026-11-16-uibowl/foundation-bfs-1440.png) | [390px](technical-learning-evidence/2026-11-16-uibowl/foundation-bfs-390.png) |
| 설명 입력 | [1440px](technical-learning-evidence/2026-11-16-uibowl/foundation-explain-1440.png) | [390px](technical-learning-evidence/2026-11-16-uibowl/foundation-explain-390.png) |
| 구현·테스트 | [1440px](technical-learning-evidence/2026-11-16-uibowl/foundation-implement-1440.png) | [390px](technical-learning-evidence/2026-11-16-uibowl/foundation-implement-390.png) |
| 검증 결과 | [1440px](technical-learning-evidence/2026-11-16-uibowl/foundation-result-1440.png) | [390px](technical-learning-evidence/2026-11-16-uibowl/foundation-result-390.png) |

[피드백](technical-learning-evidence/2026-11-16-uibowl/foundation-feedback-390.png) · [테스트 도움말](technical-learning-evidence/2026-11-16-uibowl/foundation-help-390.png)

자료 본문은 현재 카탈로그의 실제 공개 데이터다. 진행·피드백·검증 결과는 UI 검사용 fixture이며 실제 사용자 기록이나 실행 결과가 아니다. 전체 페이지 캡처의 고정 메뉴는 촬영 시점의 위치에 표시된다.

## 검증

- 54단원 × 1440/390px: 개념 화면 108건, 문서 가로 넘침 및 런타임 오류 없음.
- 설명·구현·실패 결과 × 1440/1024/768/390px: 12개 상태.
- 참고 풀이 열기, 기준 설명 펼침, 단계 이동/초기화, 슬라이더 키보드, 재생/일시정지, 도움말/Esc, 이중 연결 전환, 그래프 시작점 선택, 오류/재시도.
- 브라우저 검사는 실제 AI·코드 실행·사용자 저장 API를 호출하지 않는다. 풀이를 열기 전 저장하는 동작도 fixture로 격리했다.

[검사 코드](technical-learning-evidence/2026-11-16-uibowl/foundations-check.mjs) · [검사 결과](technical-learning-evidence/2026-11-16-uibowl/foundation-checks.json). Vite 5173, 프로젝트 `.venv`와 Playwright 설치 환경에서 검사 코드를 실행한다. 별도 Playwright 위치는 `PLAYWRIGHT_MODULE`로 지정한다. 검사 시 현재 Python 카탈로그에서 공개 데이터와 기준 풀이를 읽으며 사용자 DB를 조회하지 않는다.
