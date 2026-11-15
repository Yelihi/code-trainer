---
name: Code Trainer
description: A mobile-friendly learning workspace with explicit tasks and reusable work surfaces.
colors:
  brand: "#49144f"
  pink: "#e86fb5"
  background: "#e2e2e2"
  foreground: "#181818"
  panel: "#ffffff"
  primary: "#181818"
  primary-foreground: "#ffffff"
  secondary: "#f4f1f5"
  surface-muted: "#efebf0"
  accent: "#f6e1ef"
  border: "#d2ccd4"
  muted: "#655d68"
  input: "#86798a"
  field-background: "#faf9fb"
  success: "#236442"
  success-surface: "#e8f4ec"
  error: "#b42342"
  error-surface: "#fff0f3"
typography:
  page:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif'
    fontSize: "2rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-.03em"
  section:
    fontSize: "1.2rem"
    fontWeight: 600
    letterSpacing: "-.02em"
  title:
    fontSize: ".95rem"
    fontWeight: 600
    lineHeight: 1.5
  body:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif'
    fontSize: ".875rem"
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
  status: "6px"
  control: "12px"
  action-card: "16px"
  surface: "18px"
  dock: "20px"
  resume: "22px"
  pill: "9999px"
spacing:
  tight: "8px"
  control: "16px"
  mobile-gutter: "20px"
  surface: "24px"
  desktop-gutter: "28px"
  section: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-primary-hover:
    backgroundColor: "{colors.brand}"
  button-secondary:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.control}"
    padding: "8px 16px"
  input:
    backgroundColor: "{colors.field-background}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.control}"
    padding: "8px 20px"
  badge-secondary:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  action-card:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.action-card}"
    padding: "20px"
  document-card:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.surface}"
    padding: "24px"
  resume-card:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.resume}"
    padding: "28px"
---

# Design System: Code Trainer

## Overview

**Creative North Star: “Learning workspace.”**

A light gray workspace makes saved material, questions, practice and references easy to open. White reusable surfaces organize tasks; plum identifies the learning focus, pink adds context, and black carries decisive actions. The original Code Trainer system sans supports Korean headings, interface labels and sustained reading.

This records the implemented replacement world from source, following the user-pinned brief in PRODUCT.md and the surface direction contract. It does not claim image-comp approval or pixel reproduction. The rejected serif, ink and gold system is superseded. The source authority is `frontend/src/shadcn.css` for the shared light palette, `typography.css` for fonts and shared type roles, and `learning.css` for the final workspace treatment; `main.tsx` loads shadcn, base styles and learning styles in that order.

**Key Characteristics:**

- Explicit labeled task menus and reusable icon-led action cards.
- Gray ground, white work surfaces, plum focus and restrained pink accents.
- Rounded controls with visible boundaries and keyboard focus.
- Mobile reading and question capture; a dark editor for detailed code work.

## Colors

### Primary

- **Black action** (`primary`): decisive buttons and the current primary destination, with white text.
- **Plum learning focus** (`brand`): resume surface, context icons, links and the focus ring.

### Secondary

- **Pink** (`pink`): selected text and the emphasized action icon well.
- **Pale pink context** (`accent`): selected material destination, card hover and contextual states.

### Neutral

- **Light gray ground** (`background`): the page and sticky top bar.
- **White work surface** (`panel`): reusable cards, document sections and overlays.
- **Charcoal text** (`foreground`), **muted plum gray** (`muted`): primary and supporting information.
- **Secondary** and **surface-muted**: quiet controls, icon wells, inline code and disabled surfaces.
- **Border**, **input** and **field-background**: surface separators, stronger form outlines and near-white fields.
- **Success/error** and their surfaces: feedback with written status, never color alone.

**The Action and Context Rule.** Black marks the primary action or top-level destination; plum and pale pink identify learning context. Preserve labels and `aria-current` or written status alongside color.

## Typography

**Display and body font:** the original platform sans stack recorded in the frontmatter. No custom serif face or font preload is required. **Code font:** the existing mono stack; availability of its first family is platform-dependent.

Page headings use the page role and shrink to (1.7rem) on mobile. Section headings use the section role; repeated section headers use (1.1rem). Action and activity titles use the title role; document-card titles use (1.1rem). Supporting card copy is usually (.8rem–.9rem). Body inherits the shared role; page paragraphs use line-height (1.65), with reading content retaining its own reading role. Metadata and mobile menu labels use the label scale.

**The Reading Measure Rule.** Introductory and shared reading copy stop at (72ch); lesson articles and reference chapters use (74ch). Keep long content readable inside the task-oriented shell.

## Layout

The centered shell and pages share a maximum width of (1180px), desktop side gutters of (28px), and mobile side gutters of (20px). Page padding ends at (72px) on desktop. Cards commonly use (20px–24px) padding and (12px–24px) grid gaps. Sections start with (32px) separation, reduced to (26px) on mobile.

Desktop content collections use two columns; task entry groups use three. The Today launch pairs a wider resume surface with a column of task entries. At (900px), Today stacks and its quick actions become three compact tiles; practice and lesson layouts stack with the problem before the editor. At (700px), content collections become one column while the three compact task entries and four Materials destinations remain directly visible.

At (700px), primary navigation becomes a fixed three-destination bottom dock with labeled icons, (16px) side insets, and a bottom inset of (12px + safe area). Pages reserve (112px + safe area) at the bottom. The settings disclosure remains accessible at the top right. Materials navigation keeps four labeled entries: 원자료, 문제집, 개념 과정, 실습.

## Elevation & Depth

Work surfaces are flat at rest: gray surroundings and white cards provide separation without decorative shadows. Shadows identify floating controls and overlays, rather than making every card appear raised.

- **Settings menu:** `0 12px 32px #18181820`.
- **Question panel:** `0 12px 40px #18181826`.
- **Mobile dock:** `0 8px 28px #1818181c`.

**The Floating Layer Rule.** Keep recurring work cards tonal and flat; use the recorded shadows for the menu, dock and question panel.

## Shapes

Soft rectangular controls use the control radius; action cards use a slightly larger corner and document containers a larger surface corner. The resume surface is broader and more rounded; mobile reduces its radius to the dock radius. Status labels use compact corners, while shared badges remain pills. Thin form borders remain visible against the light ground. Lucide stroke icons accompany written labels; do not replace accessible names with decorative glyphs.

## Components

### Buttons

Use the existing shared Button and existing button-styled navigation links. Primary actions are black with white text and turn plum on hover. Shared Button defaults to the bordered secondary variant, with a pale pink hover; ordinary page link-buttons are white and hover to surface-muted. Controls have a minimum height of (44px) in the workspace. Pressed buttons move down (1px). Disabled shared buttons use muted surfaces and text; retain busy labels such as 저장 중…. Destructive actions use the error color.

### Inputs / Fields

Use the shared labeled Input, Textarea and NativeSelect. Fields have a near-white fill, stronger input border, control corners and minimum height of (44px). Input horizontal padding is (20px); textarea keeps a (90px) minimum height and vertical resizing. Shared fields show a plum focus border and a three-pixel translucent ring; invalid fields use the destructive border and ring. Placeholder text is muted and never replaces the label. Forced-color mode restores the native select appearance.

### Chips

Shared secondary badges are compact metadata pills. Language badges use pale pink context with plum text and a border. Activity status labels use pale pink and plum with written status. These labels describe content; interactive filters retain buttons and `aria-pressed`.

### Cards / Containers

ActionCard combines a stroke icon well, concise task title, optional description and a directional icon. The entire card is a link; hover changes the white surface to pale pink. Compact mobile entry cards retain the title and icon while hiding secondary description and arrow. EmptyState reuses the icon well, honest title, supporting copy and optional action.

ActivityItem places a title and wrapping metadata beside explicit actions; on narrow layouts the actions move below. Related activities share a white rounded list with separators. Document, reference and problem-book cards use white rounded containers and explicit open/edit actions. The document reading view separates user writing, linked evidence and AI explanation.

### Navigation

Keep the three labeled primary destinations: 오늘의 학습, 자료, 레퍼런스. Current primary navigation is black with white text; hover is pale pink with plum text. Materials current state is pale pink with plum text. Use `aria-current="page"` and decorative SVG icons with `aria-hidden`. Settings is a disclosure containing secondary destinations, including restricted administration entries when authorized.

### Resume and question capture

The resume surface carries a real task title, last-learning timestamp and a working continuation button; when empty it offers materials instead. Loading uses a labeled skeleton, errors show a written notice and retry where provided. Do not add a repeated noninteractive label above the title.

Question capture retains the current learning context, labeled textarea, save and close controls. The panel is scrollable and its action area sticks to the bottom. On mobile its available height and bottom position follow VisualViewport; the bottom dock hides while capture is open. Busy or context-loading states prevent duplicate submission. Closing or saving restores trigger focus; Escape respects Korean composition. Draft storage errors remain visible.

### Interaction and accessibility

All interactive elements keep visible focus: the shared outline is (2px) plum with (4px) offset, supplemented by shared control rings. Preserve semantic headings, labeled menus, written states and keyboard interaction. Reuse existing reduced-motion and forced-colors treatments. Action-card background changes use (160ms ease); buttons use existing (180ms ease) state transitions. Detailed code/editor surfaces remain dark charcoal with light code text inside the light workspace.

## Do's and Don'ts

### Do:

- **Do** reuse the shared headings, action cards, activity items, empty states and controls.
- **Do** expose problem books and practice as visible Materials destinations.
- **Do** retain task actions, labels, focus and safe-area space when layouts collapse.
- **Do** distinguish saved user writing, source evidence and AI explanation.

### Don't:

- **Don't** restore the rejected serif, gold palette or paragraph-link directory as the main workspace.
- **Don't** turn the primary learning screens into statistics dashboards or management tables.
- **Don't** use decorative eyebrows, repeated labels or hover-only task discovery.
- **Don't** extend component-preview or fixture-render evidence into real-device, paid-AI or whole-product approval.

Evidence scope: source-derived system, with actual Firefox renders of synthetic examples for Today, Materials, problem books, reference list/detail, practice and a short-viewport question panel. The post-fix review returned a scoped ship verdict for removal of the duplicate Today resume label, with no visible fix-batch regressions; it is not a whole-product approval. No new shipping raster assets were introduced. Real mobile OS keyboard behavior and paid AI were not exercised. Older ink/gold captures are not evidence for this world. Remaining isolated legacy route styles are not promoted into shared tokens; this record does not claim those routes received a complete visual audit.
