---
phase: 42-stats-aggregation-backend
asvs_level: 1
audited_date: "2026-04-16"
result: SECURED
threats_total: 3
threats_closed: 3
threats_open: 0
---

# Phase 42 Security Audit

**Phase:** 42 — Stats Aggregation Backend
**ASVS Level:** 1
**Result:** SECURED — 3/3 threats closed

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-42-01 | Information Disclosure | mitigate | CLOSED | `app/stats/service.py:16` — `match_stage = {"$match": {"_operator": callsign, "_deleted": False}}` is the first stage in all 4 aggregation pipelines (band, mode, count, call). `callsign` originates from `Depends(get_current_operator_callsign_cookie)` in `app/stats/router.py:21`, never from query params. Test: `tests/test_stats.py:106` — `test_stats_operator_isolation` passes. |
| T-42-02 | Elevation of Privilege | mitigate | CLOSED | `app/stats/router.py:21` — `callsign: str = Depends(get_current_operator_callsign_cookie)` enforces cookie-JWT auth on the `stats_page` handler; the dependency raises HTTPException(401) when no valid cookie is present. Test: `tests/test_stats.py:177` — `test_stats_route_requires_auth` asserts 302 redirect to `/log/login` with no cookie. |
| T-42-03 | Information Disclosure | mitigate | CLOSED | `app/stats/service.py:16` — `_deleted: False` is included in the shared `match_stage` applied as the first stage of all 4 pipelines. Test: `tests/test_stats.py:134` — `test_stats_excludes_soft_deleted` inserts one active and one `is_deleted=True` QSO, asserts `total_qsos == 1`. |

## Unregistered Flags

None. The SUMMARY.md threat surface scan maps all three threat IDs with no additional unregistered flags.

## Accepted Risks

None.

## Notes

The executor deviated from the plan in two implementation details that do not affect the security properties of the mitigations:

1. `get_motor_collection()` replaced by `get_pymongo_collection()` — Motor was EOL'd May 2025. The operator-isolation `$match` guard is present regardless of which collection accessor is used.
2. The plan described a 3-pipeline design (band, mode, call); the implementation uses 4 pipelines (band, mode, count, call) with an additional `$count` pipeline. All 4 pipelines start with the same `match_stage`, so T-42-01 and T-42-03 remain fully covered.
