# Learning workspace redesign

Mode: Operate; article bodies remain Read. Targets: App, Navigation, Today, Library, TechnicalReferences, ProblemBooks and shared controls.

The user rejects the previous ink/paper/gold reading-notebook design. Confirmed constraints: original Code Trainer sans-serif; supplied #49144F, #E86FB5, #E2E2E2, #181818 palette; mobile-friendly reusable components; three primary areas; problem books and practice directly discoverable from materials. The supplied screenshots are interaction and palette references, explicitly not an approved pixel composition. Code-led implementation; no image comp approval is claimed. User-pinned direction takes precedence over the roll; no further aesthetic choice is required.

## Direction contract

THESIS: A learning workspace whose menus expose the actual tasks. Replace the editorial hero and text-link directory with labeled navigation, an actionable resume surface, and reusable content components.

OWN-WORLD: Light gray ground, white work surfaces, plum learning focus, pink selected/context accents, black actions. Use Code Trainer's existing system sans and Lucide stroke icons. Controls keep clear borders, state labels and focus.

STORY: Choose today's activity, open materials or a problem book in one step, then collect reusable references. Descriptions explain an action in one line; actual documents retain full readable content.

FIRST VIEWPORT: Compact title and date; plum resume card with a real task or honest empty state; visible problem-book/review/question actions. Three labeled destinations become a bottom dock on mobile. Materials exposes source/problem-book/course/practice navigation above its content.

FORM: User-pinned mobile component workspace; seed:31278e23fbe62928 was run and acknowledged. Its open expressive axes are constrained by the supplied palette, original font and explicit task navigation. No retrospective choice board or comp approval is claimed.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

기존 명조·금색 UI의 캡처와 검토 기록은 이전 구현 이력이며 이번 사용자 요구의 시각 기준으로 사용하지 않는다. 새 검증 결과는 구현 후 기록한다.

## 2026-11-16 사용성 보완

복습은 자료·내 문제·코드·일정 탭 중 하나만 표시하며 URL의 tab으로 선택을 유지한다. 방향키·Home/End·Tab은 Radix Tabs의 기본 접근성을 사용한다. 반복되는 주기 설명은 펼침 안내로 옮긴다. 자료·질문·문제·노트·자동 수집의 빈 목록은 공통 아이콘/제목/설명/행동 컴포넌트로 정리한다. 최소 높이는 데스크톱 220px, 모바일 200px다. 그라데이션은 이어서 하기 카드와 빈 상태 아이콘 배경에만 적용한다. 기존 사용자 데이터·복습 일정·실행 API는 변경하지 않는다.
