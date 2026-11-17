# 새 디자인 독립 검토

첫 전체 검토와 수정 후 판정을 분리해 보존한다. 검토 범위는 아래 본문과 README의 한계를 따른다.

## 첫 전체 검토

disposition: fix

Missing inputs: no QUALITY BAR card supplied for the user-pinned world; no approved comp applies. Source review sampled the named primary components and relevant stylesheet sections; unrelated route bodies and remaining legacy stylesheet rules were not read.

## persistence

Pass: PRODUCT.md records the current user requirements; the surface brief and docs/technical-learning-ui.md carry the replacement code-led contract. seed:31278e23fbe62928 verifies as rolled on this machine (exit 0). Old DESIGN.md/design.json are expressly discarded and await the post-review documenter; they were not used as visual authority. No comp-round approval or comp reproduction is asserted. All eleven named PNG captures exist, show the claimed content, and match the supplied DPR2 dimensions: desktop 2880×2000, mobile 780×1688, short question 780×1000.

## fidelity

| Element or promise | State | Evidence |
| --- | --- | --- |
| TYPE | match | Original Code Trainer system sans restored; Korean headings and controls use a consistent sans hierarchy. The user's original-font requirement authorizes this over the category display-face default. |
| MATERIAL | match | Flat work surfaces, stroke icons, and an actual code editor; no simulated paper, metal, texture, or raster obligations. |
| GROUND | match | Light gray field matches the named #E2E2E2 target; source palette also defines plum #49144F, pink #E86FB5, and black #181818. |
| THESIS | match | Labeled primary menus, actionable resume surface, reusable task cards, and distinct document surfaces replace the rejected paragraph directory. |
| OWN-WORLD | match | Gray ground, white work surfaces, plum focus, pink contextual states, black actions, Lucide icons, and visible control boundaries hold across captures. |
| STORY | match | Today provides problem-book/review/question entries; Materials visibly exposes source/problem-book/course/practice destinations; References has explicit write/read actions. |
| FIRST VIEWPORT | match | Mobile Today shows title/date, task resume, three quick actions, and three labeled dock destinations within 390×844; Materials exposes problem books before content. |
| FORM | match | User-pinned component workspace is implemented without claiming screenshot pixel fidelity or a comp approval. Seed reference is corroborated. |
| Mobile adaptation | adaptation | The surface brief explicitly requires a bottom dock and mobile-friendly reusable components; navigation becomes a labeled dock and content grids stack without losing task actions. |
| Question capture | match | At 390×500 the full draft, learning context, save, and close controls remain visible; underlying practice editor remains present. |
| Reference reading | match | The mobile detail separates user explanation, linked evidence, and AI explanation; working return navigation is retained. |
| Resume label floor | contradicted | Today places a noninteractive play icon and “이어서 하기” above the resume h2, repeating the button below; this is the craft floor's explicitly banned eyebrow pattern. |
| Demonstration truth | match | Provided fixture packet declares isolated synthetic examples; visible material/reference/question titles are marked 예시, and source excerpts explicitly state screen-validation examples. No commercial outcome claims appear. |

## ceiling

The supplied user-pinned world commits to task clarity and reusable mobile surfaces; no separate QUALITY BAR card was supplied to support a higher ornamental or material ceiling. Existing sans, restrained stroke icons, differentiated primary/secondary states, task-specific cards, readable document sections, and the three-destination dock reach that functional commitment. No illustrated, dimensional, or decorative device is required by this brief.

## material_fixes

1. Floor / FIRST VIEWPORT: delete Today.tsx's noninteractive `.resume-card-label` and its unused styling/icon import; keep the actual task heading, timestamp, and working resume button. Recapture today-desktop.png and today-mobile.png at the same viewports for scoring.

## keep

Keep the restored sans and exact core palette, direct Materials → Problem books access, explicit book actions, three labeled primary destinations, retained editor context, and reachable question save/close controls.

## 수정 후 판정

## verdict

1. Resolved — both recaptured Today views remove the noninteractive “이어서 하기” eyebrow and play icon; the task title, last-study timestamp, and working resume CTA retain their hierarchy and contrast.
2. Fix-batch regressions: none visible. The additional visited reference appears as an ordinary other-learning item, while problem-book/review/question actions and the active three-destination dock remain clear.

## remaining

Clear. Ship covers the scored fix, not the whole surface. Other nine captures remain the previously reviewed evidence; real mobile OS keyboard and live paid AI behavior remain outside this visual scoring pass.

disposition: ship
