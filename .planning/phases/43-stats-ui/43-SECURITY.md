---
phase: 43-stats-ui
asvs_level: 1
audited: 2026-04-16
auditor: gsd-secure-phase
result: SECURED
threats_total: 4
threats_closed: 4
threats_open: 0
---

# Phase 43 Security Audit

## Result: SECURED

**Phase:** 43 — Stats UI
**Threats Closed:** 4/4
**ASVS Level:** 1

---

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-43-01 | Tampering | mitigate | CLOSED | `templates/log/stats.html` lines 79–81: all three data variables (`band_counts`, `mode_counts`, `entity_counts`) use `\| tojson` filter. No `\| safe` or bare substitution found. Exactly 3 `\| tojson` occurrences. |
| T-43-02 | Tampering | accept | CLOSED | Accepted risk documented below. jsDelivr CDN, Chart.js pinned at 4.5.1, no SRI hash, internal private-network deployment. |
| T-43-03 | Information Disclosure | mitigate | CLOSED | `app/stats/service.py` line 16: `match_stage = {"$match": {"_operator": callsign, "_deleted": False}}` — every aggregation pipeline begins with this operator-scoped `$match` guard. `app/stats/router.py` line 21: callsign sourced from `Depends(get_current_operator_callsign_cookie)` auth dependency, then passed directly to `get_stats(callsign)`. No cross-operator data path exists. |
| T-43-04 | Spoofing | mitigate | CLOSED | `app/stats/router.py` line 21: `callsign: str = Depends(get_current_operator_callsign_cookie)`. Unauthenticated requests are rejected by the dependency before the handler body executes (302 redirect to login per auth module contract). |

---

## Accepted Risks Log

### T-43-02 — Chart.js CDN without SRI hash

**Category:** Tampering (supply chain)
**Component:** `<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js">` in `templates/log/stats.html`
**Risk:** A CDN compromise at jsDelivr for the pinned 4.5.1 version could inject malicious JavaScript into the stats page.
**Rationale for acceptance:**
- Version is pinned to `@4.5.1` — floating version tag attack is not possible.
- ollog is an internal ham radio logbook deployed on a private network; not an internet-facing public application.
- The stats page is behind cookie authentication; unauthenticated users cannot reach the page where the CDN script loads.
- SRI hash would be appropriate for an internet-facing deployment; deferred to a future hardening phase if deployment profile changes.
**Residual risk:** Low — limited blast radius (operator-only), private network, pinned version.
**Owner:** Accepted by project plan (PLAN.md T-43-02 disposition).

---

## Unregistered Threat Flags

None — SUMMARY.md `## Threat Flags` section absent; no unregistered flags to record.
