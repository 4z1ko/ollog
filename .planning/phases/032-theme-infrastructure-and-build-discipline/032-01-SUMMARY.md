---
phase: 032-theme-infrastructure-and-build-discipline
plan: "01"
subsystem: frontend/theme
tags: [theme, fouc, dark-mode, htmx, tailwind, build]
dependency_graph:
  requires: []
  provides:
    - FOUC-prevention IIFE with rAF-rAF transition suppression
    - color-scheme meta tag and CSS rules for native browser controls
    - htmx:afterSettle handler for icon sync
    - npm verify script for build safety gate
  affects:
    - templates/base.html
    - templates/base_app.html
    - static/css/input.css
    - static/css/output.css
    - package.json
tech_stack:
  added: []
  patterns:
    - rAF-rAF transition suppression (prevents color-fade flash on cold page load while preserving toggle animation)
    - color-scheme CSS property for native scrollbar/input theme adoption
    - htmx:afterSettle event listener for post-swap icon sync
key_files:
  created: []
  modified:
    - templates/base.html
    - templates/base_app.html
    - static/css/input.css
    - static/css/output.css
    - package.json
decisions:
  - "Use document.body (not document) for htmx:afterSettle listener to match existing HTMX event patterns in codebase"
  - "IIFE moved before stylesheet link tag to ensure synchronous execution before any paint"
  - "rAF-rAF pattern chosen over CSS no-transition class: inject style before dark class, remove after two animation frames"
metrics:
  duration: "~2 min"
  completed: "2026-04-11"
  tasks_completed: 2
  files_modified: 5
---

# Phase 32 Plan 01: Theme Infrastructure and Build Discipline Summary

**One-liner:** rAF-rAF FOUC suppression, color-scheme meta+CSS for native controls, htmx:afterSettle icon sync, and npm verify safety gate — all wired before any v1.9 component work begins.

## What Was Built

Theme infrastructure foundation for v1.9 consisting of four targeted changes across five files:

1. **FOUC IIFE hardened** — Added LOAD-BEARING annotation, moved IIFE before stylesheet link, replaced single-line comment with multi-line warning. Added rAF-rAF transition suppression: injects `transition: none !important` before applying the dark class, then removes it after two requestAnimationFrame callbacks so cold page loads have zero color flash while user-initiated toggles still animate smoothly.

2. **color-scheme support** — Added `<meta name="color-scheme" content="light dark">` as the first meta after viewport. Added `color-scheme: light` to the `html` rule and `html.dark { color-scheme: dark }` in `@layer base` of `input.css`. This causes scrollbars, form inputs, and select dropdowns to adopt the active theme's native color scheme.

3. **HTMX afterSettle handler** — Added `document.body.addEventListener('htmx:afterSettle', ...)` in `base_app.html` that calls `updateThemeIcons()` after every HTMX partial swap. Prevents the theme icon reverting to stale state when HTMX replaces markup containing the theme button.

4. **npm verify script** — Added `"verify"` to `package.json` scripts: runs `npm run build` then greps `output.css` for both `color-scheme` and `dark`. Exits 0 on success, exits 1 with error message on failure. Acts as build safety gate for all subsequent v1.9 phases.

## Verification Results

| Check | Result |
|-------|--------|
| `grep "LOAD-BEARING" templates/base.html` | Line 9 |
| `grep "noTransition" templates/base.html` | Lines 18, 19, 20, 29 |
| IIFE line (18) < stylesheet line (37) | PASS |
| `grep "color-scheme" templates/base.html` | Line 6 (meta tag) |
| `grep "color-scheme" static/css/input.css` | Lines 8 and 11 |
| `grep "htmx:afterSettle" templates/base_app.html` | Line 193 |
| `npm run verify` | Exit 0 — "Verify OK: dark classes and color-scheme present" |
| `grep "color-scheme" static/css/output.css` | Both light and dark rules present |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 270a6d3 | FOUC IIFE annotation, rAF-rAF transition suppression, color-scheme |
| Task 2 | 9daaa2f | htmx:afterSettle handler, verify script, rebuild output.css |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED
