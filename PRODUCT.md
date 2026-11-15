# Code Trainer

<!-- impeccable:product-schema 1 -->

## Platform
web

## Users
기술 자료를 모으고 개념을 배우며 코드로 적용하고 복습하는 개인 학습자. 모바일에서는 읽기·질문·기록, 데스크톱에서는 코드 작성까지 이어간다.

## Product Purpose
자료 수집 → 이해와 질문 → 문제와 적용 → 복습 → 기술 레퍼런스와 AI Skill. 단계를 강제하지 않는다. 세부 요구사항은 PLAN.md를 따른다.

## Capabilities and Constraints
React/TypeScript/Vite, FastAPI/Pydantic, SQLite를 재사용한다. 자료 저장과 AI 생성을 분리한다. 원자료·버전·질문·풀이·도움 기록·복습 초안과 기존 개인 기록을 보존한다. 코드 실행 격리와 소유자 권한을 유지한다. 범용 개인 위키와 삶의 분석은 별도 서비스 범위다.

## Product Principles
- 사용자가 다음 학습 행동을 고를 수 있게 한다.
- 모든 주요 화면에서 질문을 기록한다. 답변이 저장 조건은 아니다.
- AI 설명과 사용자의 경험, 검증한 결과를 구분한다.
- 사용자 작성 내용은 AI가 조용히 덮어쓰지 않는다.

## Accessibility & Inclusion
터치 영역, 키보드 접근, 초점 표시, 모바일 키보드 상태의 저장/닫기, 한글 조합 입력, 페이지 가로 넘침 방지. 색상만으로 상태를 전달하지 않는다.

## Confirmed design brief
2026-11-15 사용자: 시각적 스타일도 변경하고 대시보드 및 테이블 중심 구성을 피한다. 오늘의 학습 / 학습 자료 / 내 레퍼런스가 주요 메뉴다. 읽기와 학습 행동을 중심에 둔다.
