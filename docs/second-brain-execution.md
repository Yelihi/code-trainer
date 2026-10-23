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
