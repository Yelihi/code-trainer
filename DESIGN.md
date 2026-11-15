---
name: Code Trainer
description: An ink, paper, and gold technical reading notebook.
colors:
  primary: "#dcc18b"
  primary-foreground: "#20251c"
  background: "#141614"
  foreground: "#eee9dd"
  panel: "#1b1e1a"
  border: "#393e34"
  muted: "#b4b6a8"
  secondary: "#252a22"
  surface-muted: "#22261f"
  accent: "#343c2d"
  input: "#626954"
  success: "#99c8ac"
  error: "#ffb0a5"
typography:
  display:
    fontFamily: "'Trainer Reading Serif', Georgia, serif"
    fontSize: "clamp(1.9rem, 3.5vw, 2.7rem)"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "-.03em"
  headline:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif'
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "-.02em"
  title:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif'
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif'
    fontSize: ".9375rem"
    fontWeight: 400
    lineHeight: 1.7
  reading:
    fontSize: "1rem"
    lineHeight: 1.85
  label:
    fontSize: ".75rem"
    fontWeight: 500
  code:
    fontFamily: '"IBM Plex Mono", ui-monospace, SFMono-Regular, Consolas, monospace'
    fontSize: "1rem"
    lineHeight: 1.75
rounded:
  flat: "0"
  control: "4px"
  field: "4px"
  pill: "9999px"
spacing:
  compact: "12px"
  control: "16px"
  mobile-gutter: "20px"
  row: "24px"
  desktop-gutter: "32px"
  section: "48px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.control}"
    padding: "8px 16px"
  button-secondary:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.control}"
    padding: "8px 16px"
  input:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.field}"
    padding: "8px 20px"
  reading-link:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    rounded: "{rounded.flat}"
  reading-row:
    backgroundColor: "transparent"
    textColor: "{colors.foreground}"
    rounded: "{rounded.flat}"
    padding: "24px 0"
  badge-secondary:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
---

# Design System: Code Trainer

## Overview

**Creative North Star: "Technical reading notebook"**

The notebook metaphor comes from the recorded user direction in `docs/technical-learning-ui.md`: ink surroundings, warm paper-colored text, and restrained gold emphasis. The interface supports sustained Korean reading and deliberate learning actions. Paper describes the text's warmth; the implemented surface remains dark.

This is a source-derived record of the implemented system, not a retrospective direction approval. The formal THESIS, OWN-WORLD, STORY, FIRST VIEWPORT, and FORM blocks and concept-seed protocol were not completed. An independent reviewer opened and validated all seven post-fix captures and returned a scoped ship verdict for the scored fixes only: distinct reading links, bundled Korean serif, and honest protocol omissions. No fix-batch regressions were found; this is not a broader product approval. Browser checks also confirmed native back navigation restored the library query (예시) and scroll position (650px), and a 390×500 viewport kept the question panel bottom (488px) and save control (467px) visible. Actual-device keyboard behavior remains unverified. Sources: `frontend/src/learning.css` (loaded last), `styles.css`, `typography.css`, `shadcn.css`, `components/ui`, `App.tsx`, `Navigation.tsx`, `Today.tsx`, and `TechnicalReferences.tsx`.

**Key Characteristics:**
- Dark ink surfaces with warm readable text and restrained gold actions.
- Serif page titles paired with practical sans-serif interface text.
- Ruled reading lists, limited prose measure, and generous vertical rhythm.
- Three primary destinations with settings in a secondary disclosure.

## Colors

Gold supplies the primary accent; olive-tinted neutrals hold the reading space. Frontmatter records the effective learning theme, rather than earlier declarations overridden by it. The sidecar tonal ramps are synthesized panel previews, not additional colors authorized for product use.

### Primary
- **Bookmark gold:** primary actions, current navigation underline, reading links, selection, caret, and focus.
- **Dark action ink:** text on filled gold actions and selected text.

### Secondary
- **Quiet green:** success and confirmed-result text, not a substitute for written state labels.
- **Warm error:** error text; describe the problem and offer a local recovery action.

### Neutral
- **Ink:** page background and editable field interiors.
- **Warm paper:** principal text.
- **Raised ink:** question and settings panels.
- **Olive rule:** separators and quiet control boundaries.
- **Muted paper:** supporting explanations and timestamps.
- **Secondary ink / muted ink / active olive:** control, subdued surface, and hover layers.
- **Field edge:** stronger input boundary.

**The Bookmark Rule.** Use gold to identify reading links, action priority, and current position; retain written labels and an underline or other structural cue.

## Typography

**Display Font:** Trainer Reading Serif, with Georgia and generic serif fallbacks. The full Korean WOFF2 is bundled, declared at regular weight, and preloaded in `frontend/index.html`; its OFL notice is distributed in `frontend/public/fonts/OFL-NanumMyeongjo.txt`.

**Body Font:** The platform sans-serif stack in frontmatter. **Code Font:** The mono stack in frontmatter; IBM Plex Mono is a preferred family name, not a bundled-font guarantee.

Page titles use the reading serif. Interface headings retain sans-serif clarity, with semibold hierarchy. Font synthesis is disabled; do not request invented bold variants of the regular bundled face.

### Hierarchy
- **Display:** Page h1, responsive serif heading.
- **Headline:** General h2. Learning section headers use a smaller local size (1.2rem).
- **Title:** General h3 and reference-list h2. Learning-row h3 is locally smaller (1.1rem).
- **Body:** Effective base body role. Paragraph leading expands to the reading rhythm (1.85).
- **Reading:** Existing long-form reading role; the general body remains smaller.
- **Label:** Compact metadata and form-label role; navigation stays near body size.
- **Code:** Monospace blocks and editor content, distinct from prose.

**The Reading Measure Rule.** Keep introductory prose and reading copy within 72ch; longer lesson and reference chapters use a related 74ch limit.

## Layout

The header and navigation use a centered 1200px envelope. Pages use an 1100px maximum with desktop padding (52px 32px 100px). Reference reading and editing narrow further to 900px. Reading rows have vertical padding (24px), thin bottom rules, and a horizontal title/action relationship; sections separate by 48px.

At the shared narrow breakpoint (700px), page padding becomes 32px 20px 72px, row contents stack, action groups wrap, sections separate by 36px, and settings move below the three navigation links. At 900px, lesson and practice columns stack. Header stickiness and scroll padding preserve access to the question entry point.

Use reading lists and document sections for the primary learning surfaces. The user's rejection of dashboard/table-centered composition does not ban every table, bordered field, diagram, or code panel inside technical learning content.

## Elevation & Depth

Reading lists are flat, using type, spacing, and rules rather than raised cards. Settings use an opaque panel and border. The floating question panel has an ambient shadow (`0 12px 32px #0008`) to distinguish its overlap; ordinary reading rows do not inherit that shadow. Focus is a functional outline/ring, not decorative depth.

**The Ruled List Rule.** Keep recurring reading rows transparent with separators; reserve enclosed surfaces for controls, editable material, code, and overlays that need their own boundary.

## Shapes

Rows and reading links are square and transparent. Shared UI controls derive their gentle corner from the theme radius: the base is 6px and Tailwind's medium radius resolves to 4px. Badges use a full pill. Legacy `.button` links retain 7px corners; the floating question panel has its own overlay silhouette (12px, with a narrow-screen top-corner treatment). These coexist in the source; do not silently normalize the product through documentation.

## Components

### Buttons

Explicit actions use filled controls. The shared Button defaults to secondary; gold is used for primary emphasis. Default shared controls have a minimum height (36px), compact padding from frontmatter, and medium text. Hover uses the active surface for secondary controls; keyboard focus retains a visible outline and gold ring. Active buttons move down slightly (1px); disabled controls are visibly muted. Action-styled links remain appropriate for explicit continuation, creation, and opening actions.

### Reading links

In-page text links and unclassed page anchors are gold, transparent, borderless, square, and underlined with a visible offset (5px); hover turns them to principal text. Introductory reading links retain their underline and small vertical hit-area padding. Do not turn a reading link into a filled button by inheriting a broad page-anchor selector.

### Chips

The shared Badge supplies compact status/category pills. Use existing default, secondary, or outline roles; state must remain readable in text. The old language variant's purple literals are legacy drift, not a new palette role.

### Cards / Containers

Reading containers are transparent ruled rows, not a tiled card system. The learning row aligns content and explicit actions on desktop and stacks them on narrow screens. Retain explanatory text and metadata without making them competing headings.

### Inputs / Fields

Shared Input, Textarea, and NativeSelect keep their existing semantic behavior and labels. Inside the app shell, effective fields use ink interiors, principal text, a stronger field edge, and muted placeholders. Input minimum height is 44px. Focus shifts the edge and adds a gold ring; invalid and disabled states come from the shared primitives. Do not remove the focus outline when copying a visual pattern.

### Navigation

Three destinations occupy a horizontal text navigation: 오늘의 학습, 학습 자료, 내 레퍼런스. Inactive links use muted text; `aria-current` adds principal text and a gold bottom rule (2px). Settings and records remain a labeled disclosure. On narrow screens, the three links share the full width and settings sit on the next line.

### Question panel

The contextual question panel uses raised ink, a border, internal scrolling, and sticky form actions. Narrow screens use an inset fixed panel whose height/bottom can follow viewport-related CSS variables. This describes the implementation; real mobile keyboard behavior has not been visually verified in this pass.

## Do's and Don'ts

### Do:
- **Do** use the bundled regular serif for page titles and sans-serif for interface text.
- **Do** preserve transparent underlined reading links and distinct explicit action buttons.
- **Do** use ruled rows and limited reading measures for primary learning content.
- **Do** retain keyboard focus, written states, labeled inputs, and reduced-motion behavior.

### Don't:
- **Don't** make primary learning surfaces depend on dashboard tiles or table-centered composition.
- **Don't** promote legacy purple literals or every isolated radius into reusable theme decisions.
- **Don't** extend the scoped post-fix ship verdict into broad product approval or actual-device keyboard verification.
