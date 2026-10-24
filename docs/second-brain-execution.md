# Supplied execution request

The user requested independent raw-reference management, separate AI interpretation,
the five navigation areas, and an incremental redesign on a separate branch.
The roadmap is `docs/second-brain-redesign-plan.md`.

After the recommendations were presented, the user said:

> 네 진행하죠

The user then explicitly invoked:

> $frontend-system:fs-work 진행하죠

This authorizes implementing the presented roadmap incrementally using fs-work.
It is not a selection of previously unspecified policy alternatives. The first
scoped implementation is the P1 legacy resource migration prerequisite. Existing
archive/graph semantics, new permanent deletion, review scheduling, action ontology,
AI credential policy, and Deep Inside are outside this first implementation.

Whole-project analysis is partial and must not be represented as completed. The
initial recorded baseline covers database declarations and tooling; scoped source
inspection for this implementation is separate. Remaining baseline areas stay pending.

## Delivery updates

The user selected `release/second-brain-redesign` as the integration branch for the
redesign, with release-to-main merging reserved for their final review.

On 2026-10-23 the user supplied this exception:

> 이번 인프라 개선만 main 병합에 들어가고, 현 release 는 Rebase 해서 계속 진행하는게 좋아보입니다

Only the development-environment changes on `chore/backend-dev-server` are to merge
into main now. Then rebase `release/second-brain-redesign` onto the updated main.
This does not authorize merging the P1 independent-resource migration or the wider
redesign into main. Subsequent redesign work still integrates through release.

Completed: infrastructure PR #21 passed CI and merged into main at `abe39d3`.
`release/second-brain-redesign` was rebased onto that commit and pushed without
force; it had no independent commits. The working checkout now uses release.
P1 remains separately on `feat/independent-resource-migration` at `d1f3e38`.

### P1 release delivery and P2 preparation — 2026-10-23

P1 was rebased without changing its patch: `d1f3e38` → `e577cf4`.
After the behavior explanation, the user supplied:

> 이거 rebase 에 반영하겠습니다. 다음 작업으로 또 계속 이어서 가죠

Continuation uses the previously selected release integration target. PR #22:
https://github.com/Yelihi/code-trainer/pull/22

Fresh verification in `/tmp/code-trainer-p1-delivery`: 93 backend tests passed,
frontend unit/lint/types/build passed, and the FS PR gate returned ready against
`origin/release/second-brain-redesign`. Historical records were not treated as
current proof; plan evidence, checks and scoped reviews were refreshed there.
The whole-project baseline remains partial. Main merge/deployment is excluded.

PR #22 passed all GitHub CI jobs and merged into release at `6f4a8ce`.
The next local branch is `feat/resource-library`, based on that release commit.
Main remains `abe39d3`. P1's fresh FS evidence stays in the isolated delivery
worktree; it is not asserted as current verification of future P2 changes.

Next milestone: P2 independent registration and an owner-scoped library. Existing
note editing retains its revision conflict, draft, image ownership and archive
contracts. URL/text registration is separated from AI generation; existing safe
public-URL fetching is reused. Registration must not require AI/runner readiness.

Open P2 decision: when a user explicitly registers an already stored URL, should
the app add a changed-content version to that resource, create an independent
resource, or let the user choose? This is not the transport-level retry case:
retrying an identical request must remain idempotent. No option is selected yet.
The answer affects registration storage and subsequent interpretation provenance.
P2 implementation has not started; no new schema/API/UI contract is approved yet.

Decision resolved by the user: "본문이 달라졌을 때만 버전 추가".
Re-registering the same URL reuses its resource and appends a version only when
the fetched body differs. Identical content adds no version; old versions and
their interpretation provenance remain intact. This does not change legacy P1
import identities or silently merge multiple historical learning sources.


## P2 release delivery and P5 navigation (2026-10-23)

P2 원문 등록·보관함은 PR #23으로 `release/second-brain-redesign`에 병합했다 (merge `4c798f5`). 백엔드 102개 테스트, 프론트엔드 검사와 GitHub CI가 통과했다. CI 첫 실행의 Docker Hub 502 오류는 코드 변경 없이 실패 작업을 재실행하여 해소했다. main 병합과 배포는 하지 않았다.

사용자의 다섯 영역 메뉴 누락 지적과 후속 작업 요청에 따라 P5를 `feat/second-brain-navigation`에서 먼저 진행한다. 기존 URL과 `/create`의 피드 쿼리는 유지하고, `/explore`(기존 해석 학습 목록), `/explore/practice`(실습 진입점)를 추가한다. 첫 화면은 원문 등록을 주 행동으로 안내한다. 추출 가능 자료·Deep Inside·사용자 AI 연결은 준비 상태 및 기존 기능 안내만 제공하며 생성/저장 기능을 구현한 것으로 표시하지 않는다.

P3 RSA 원문 저장 완료 전환, P4 보관함에서 독립 해석 시작은 아직 미구현이다. 이후 후보 추출·망각 곡선 일정·Deep Inside·사용자별 API 키도 별도 작업이다. P5 메뉴 적용을 전체 제품 전환 완료로 간주하지 않는다.

## P4 일반 해석 (2026-10-24)

P5는 PR #24로 release에 병합되었다. P3 RSA 원문 등록은 PR #25에서 release 검토 중이며 CI가 통과했다. main 병합·배포는 수행하지 않았다.

사용자가 일반 해석의 별도 관리를 선택했다. 기존 `contexts` 재사용 제안을 대체하고, `feat/resource-interpretation`에서 원문 버전 → 명시적 AI 요청 → 별도 개념 문서 흐름을 구현한다. 기존 코딩 모델과 `/learn`의 검증·기록은 유지한다. `/explore`는 일반 해석 기록, `/interpretations/:id`는 상태·출처·문서·같은 버전 재시도를 담당한다. 원문 인용과 AI 확장·질문을 구분하며 조회는 AI를 호출하지 않는다.

P4 검증은 버전 고정, 소유권, 요청 재전송·경합, 중단·실패 복구, 기존 코딩 회귀와 실제 브라우저 동작을 포함한다. 테스트 제공자 응답은 고정된 검증 자료이며 실제 모델의 해석 품질 검증은 별도다. P6 이후 추출·실습·복습·응용 기능은 아직 구현하지 않았다.
