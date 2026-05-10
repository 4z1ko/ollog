---
phase: 56
slug: documentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-10
---

# Phase 56 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (existing); MkDocs build as doc-content gate |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run mkdocs build --strict` |
| **Full suite command** | `uv run pytest tests/` |
| **Estimated runtime** | ~10 seconds (mkdocs build) |

---

## Sampling Rate

- **After every task commit:** Run `uv run mkdocs build --strict`
- **After every plan wave:** Run `uv run mkdocs build --strict`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 56-01-01 | 01 | 1 | DOC-03 | — | N/A | build | `uv run mkdocs build --strict` | mkdocs.yml edit | ⬜ pending |
| 56-01-02 | 01 | 1 | DOC-01 | — | N/A | grep | `grep -n "Danger Zone" docs/operator-guide/profile.md` | Edit of existing | ⬜ pending |
| 56-01-03 | 01 | 1 | DOC-02 | — | N/A | grep | `grep -n "Clear Operator Log" docs/admin-guide/account-management.md` | Edit of existing | ⬜ pending |
| 56-01-04 | 01 | 1 | DOC-03 | — | N/A | build | `uv run mkdocs build --strict && grep -r 'class="admonition danger"' site/` | site/ rebuild | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

No new test files required — the MkDocs build is the automated verification gate for all three requirements. Existing pytest suite intentionally does not cover documentation content.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Admonition renders as styled block (not plain text) | DOC-01, DOC-02 | Visual check of built HTML in browser | Open `site/operator-guide/profile/index.html` and `site/admin-guide/account-management/index.html`; confirm danger admonition displays with red icon and styled border |
| Section placement correct in admin guide | DOC-02 | Structural order requires visual inspection | Confirm `## Clear Operator Log` appears after `## Reset a User's Password` in rendered page |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
