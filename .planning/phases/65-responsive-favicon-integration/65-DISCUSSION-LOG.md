# Phase 65: Responsive Favicon Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-13
**Phase:** 65-Responsive Favicon Integration
**Areas discussed:** Static path, Metadata set, Guide coverage

---

## Static Path

| Option | Description | Selected |
|--------|-------------|----------|
| `/static/favicon/...` | Copy favicon files into `static/favicon/`; works naturally with the existing operator/admin `/static` mounts. | yes |
| `/favicon/...` | Add a new FastAPI static mount for the `favicon/` folder in both operator and admin apps. | |
| You decide | Agent chooses the lower-risk option for this codebase. | |

**User's choice:** `/static/favicon/...`
**Notes:** This keeps serving aligned with the existing app/static architecture.

---

## Metadata Set

| Option | Description | Selected |
|--------|-------------|----------|
| Full responsive bundle | Add `.ico`, 16/32 PNG icons, Apple touch icon, and `site.webmanifest`. | |
| ICO only | Add one shared `<link rel="icon" href="/static/favicon/favicon.ico">`. | yes |
| You decide | Agent chooses the best browser-compatible option. | |

**User's choice:** ICO only
**Notes:** App pages should not add PNG, Apple touch icon, or manifest metadata in this phase.

---

## Guide Coverage

| Option | Description | Selected |
|--------|-------------|----------|
| App pages only | Operator/admin app pages only; no MkDocs rebuild. | |
| Include guide | Also adjust/rebuild `/guide` so docs pages get the favicon too. | yes |
| You decide | Agent chooses based on lowest risk and least churn. | |

**User's choice:** Include guide
**Notes:** Phase 65 should account for MkDocs Material favicon behavior and rebuild committed `site/` output if needed.

---

## the agent's Discretion

- Choose the exact low-churn MkDocs favicon wiring mechanism after checking the existing `mkdocs.yml` and build output conventions.
- Choose whether to copy only `favicon.ico` or supporting files into `static/favicon/`, while keeping app-page metadata ICO-only.

## Deferred Ideas

- Full responsive metadata bundle for app pages.
- Per-operator or environment-specific favicon variants.
