---
phase: 47
slug: new-qso-badge
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-17
---

# Phase 47 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (existing) |
| **Config file** | `pytest.ini` (existing) |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/`
- **Before `/gsd-verify-work`:** Full suite must be green + manual browser verification of SC-1 through SC-5
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 47-01-01 | 01 | 1 | LIVE-03 | — | N/A — read-only DOM, no user data | manual | n/a (browser: page 2+ SSE fires, badge appears) | ❌ manual-only | ⬜ pending |
| 47-01-02 | 01 | 1 | LIVE-04 | — | N/A — no server call on dismiss | manual | n/a (browser: click badge, no nav) | ❌ manual-only | ⬜ pending |
| 47-01-03 | 01 | 1 | LIVE-03+LIVE-04 | — | N/A | regression | `uv run pytest tests/ -x -q` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test infrastructure needed — phase modifies only `templates/log/log.html` (HTML + JS) with no new Python surface.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Badge appears when SSE fires on page 2+ | LIVE-03 | Requires real SSE delivery, HTMX swap lifecycle, and DOM state — not testable without a running browser | 1. Start Docker stack. 2. Log in, navigate to page 2 of the log. 3. Insert a QSO via UDP. 4. Verify badge reads "1 new QSO" with no page jump. 5. Insert 2 more — verify "3 new QSOs". |
| Badge absent on page 1 with no filters | LIVE-03 | Same — browser + SSE interaction | 1. Stay on page 1 (no filters). 2. Insert a QSO via UDP. 3. Verify no badge appears (table refreshes directly). |
| Click-to-dismiss resets counter | LIVE-04 | Requires browser click event | 1. With badge showing "3 new QSOs", click the badge. 2. Verify badge hides, page does not jump or reload. |
| Auto-dismiss on navigate to page 1 | SC-4 (LIVE-04) | Requires navigation + HTMX afterSettle event | 1. With badge showing N new QSOs, click page 1. 2. Verify badge disappears after table settles. |
| Badge survives #log-table SSE swap | SC-5 | Requires real SSE swap to observe DOM | 1. On page 1, wait for auto-refresh to fire. 2. Verify badge element still exists in DOM as sibling of #log-table. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
