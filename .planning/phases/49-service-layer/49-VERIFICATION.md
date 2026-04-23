---
phase: 49-service-layer
verified: 2026-04-23T00:00:00Z
status: human_needed
score: 6/7
overrides_applied: 0
human_verification:
  - test: "Run `uv run pytest tests/test_service_sort.py tests/test_sse_sentinel.py -x -q` against a live MongoDB at localhost:27017"
    expected: "All MongoDB-dependent tests pass — invalid sort fallback, all 10 allowed values accepted, WARNING log content, sentinel rendered/suppressed correctly"
    why_human: "These tests require a live MongoDB instance which is not available in the static verification environment; the test_view_dict.py and static test_allowed_sort_fields_constant_has_10_values pass without DB, but the 7 DB-dependent tests in test_service_sort.py and test_sse_sentinel.py need human execution"
---

# Phase 49: Service Layer Verification Report

**Phase Goal:** `get_qso_page()` validates sort parameters against an allowlist before querying MongoDB, `_created_at` is exposed to templates via the view dict, and the SSE auto-refresh sentinel fires on both default date sort and entry-timestamp sort.
**Verified:** 2026-04-23T00:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Passing an invalid sort field (e.g. `_deleted`, `hashed_password`) to `get_qso_page()` falls back to `-qso_date_utc`, never reaches MongoDB | VERIFIED | `service.py` lines 212-218: `if sort_by not in _ALLOWED_SORT_FIELDS:` guard fires first, sets `sort_by = _DEFAULT_SORT` before any query is built. `test_invalid_sort_falls_back_to_default` covers runtime behavior. |
| 2 | All 10 allowed sort values (`-qso_date_utc`, `qso_date_utc`, `-CALL`, `CALL`, `-BAND`, `BAND`, `-MODE`, `MODE`, `-_created_at`, `_created_at`) are accepted without fallback | VERIFIED | `frozenset` at `service.py` lines 18-24 contains exactly these 10 values. `test_allowed_sort_fields_constant_has_10_values` passes (no DB required, confirmed). |
| 3 | A WARNING log is emitted containing both the rejected field name and the operator callsign | VERIFIED | `logger.warning("Invalid sort field '%s' for operator '%s', falling back to default", sort_by, operator)` at lines 213-217. Both `%s` args confirmed. `test_warning_contains_field_and_operator` validates content at runtime. |
| 4 | The view dict returned by `_qso_to_view_dict()` contains a `created_at` key with a `datetime` value | VERIFIED | `ui_router.py` line 232: `"created_at": qso.created_at,` immediately after `"qso_date_utc"`. `test_view_dict_contains_created_at` passes (1 passed, confirmed). |
| 5 | The SSE auto-refresh sentinel renders when sort is `-_created_at` on page 1 with no filters | VERIFIED | `log_table.html` line 1: `{% if page == 1 and (sort == '-qso_date_utc' or sort == '-_created_at') and not filters.call ...%}`. Parentheses around the disjunction are present. `test_sentinel_rendered_for_created_at_sort` validates at runtime. |
| 6 | The SSE auto-refresh sentinel still renders for `-qso_date_utc` (regression check) | VERIFIED | Same condition as above — `sort == '-qso_date_utc'` is retained. `test_sentinel_rendered_for_default_sort` validates at runtime. |
| 7 | The SSE auto-refresh sentinel does NOT render for non-newest-first sorts like `CALL` | VERIFIED | Condition requires `sort == '-qso_date_utc' or sort == '-_created_at'`; `CALL` does not match. `test_sentinel_not_rendered_for_call_sort` and `test_sentinel_not_rendered_with_filter_active` validate at runtime. |

**Score:** 7/7 truths structurally verified. Runtime confirmation of truths 1, 2 (partial), 3, 5, 6, 7 requires human test execution against MongoDB (see Human Verification below).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/qso/service.py` | `_ALLOWED_SORT_FIELDS` frozenset, `_DEFAULT_SORT` constant, guard block in `get_qso_page()` | VERIFIED | `_ALLOWED_SORT_FIELDS` at line 18 (10 values), `_DEFAULT_SORT` at line 17, guard block at lines 212-218. `import logging` at line 4, `logger` at line 13. |
| `app/qso/ui_router.py` | `created_at` key in view dict | VERIFIED | Line 232: `"created_at": qso.created_at,` present immediately after `"qso_date_utc"` key. |
| `templates/log/log_table.html` | Extended SSE sentinel condition with `-_created_at` | VERIFIED | Line 1 contains `(sort == '-qso_date_utc' or sort == '-_created_at')` with load-bearing parentheses. |
| `tests/test_service_sort.py` | SORT-04 allowlist validation tests | VERIFIED | 4 test functions present: `test_invalid_sort_falls_back_to_default`, `test_all_allowed_sort_values_accepted`, `test_warning_contains_field_and_operator`, `test_allowed_sort_fields_constant_has_10_values`. |
| `tests/test_sse_sentinel.py` | SORT-03 sentinel integration tests with `auto-refresh-ok` | VERIFIED | 4 test functions present with correct `id="auto-refresh-ok"` assertions. `_mongo_available()` skip guard in `sentinel_db` fixture. |
| `tests/test_view_dict.py` | View dict `created_at` key presence and type test | VERIFIED | `test_view_dict_contains_created_at` present, uses `model_construct()` (no DB required), passes (confirmed). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/qso/service.py` | `app/qso/ui_router.py` | `get_qso_page()` called from `log_view()` | VERIFIED | `ui_router.py` line 287-297: `get_qso_page(... sort_by=sort)` call confirmed. `from app.qso.service import ... get_qso_page` at line 32. |
| `app/qso/ui_router.py` | `templates/log/log_table.html` | Jinja2 template rendering with `sort` context var | VERIFIED | `ui_router.py` line 315: `"sort": sort` in context dict. `log_table.html` line 1 uses `sort` variable in sentinel condition. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `app/qso/service.py` guard | `sort_by` | Query parameter via `ui_router.py` `sort: str = Query("-qso_date_utc")` | Yes — user-supplied string | FLOWING |
| `app/qso/ui_router.py` `_qso_to_view_dict()` | `created_at` | `qso.created_at` — Beanie model field with `default_factory=lambda: datetime.now(timezone.utc)` (Phase 48) | Yes — UTC datetime from DB insert | FLOWING |
| `templates/log/log_table.html` sentinel | `sort` | `ctx["sort"] = sort` from `log_view()` | Yes — request query parameter | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `test_view_dict_contains_created_at` | `uv run pytest tests/test_view_dict.py -x -q` | 1 passed in 0.21s | PASS |
| `test_allowed_sort_fields_constant_has_10_values` | `uv run pytest tests/test_service_sort.py::test_allowed_sort_fields_constant_has_10_values -x -q` | 1 passed in 0.01s | PASS |
| DB-dependent tests (7 tests across `test_service_sort.py` and `test_sse_sentinel.py`) | `uv run pytest tests/test_service_sort.py tests/test_sse_sentinel.py -x -q` | Skipped (no MongoDB in environment) | SKIP — route to human |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SORT-04 | 49-01-PLAN.md | `get_qso_page()` validates sort parameter against `_ALLOWED_SORT_FIELDS` allowlist — arbitrary fields rejected with fallback | SATISFIED (static) | Guard block at `service.py` lines 212-218; `_ALLOWED_SORT_FIELDS` frozenset; `import logging` + `logger`; 4 tests in `test_service_sort.py` |
| SORT-03 | 49-01-PLAN.md | SSE auto-refresh fires on `-_created_at` sort in addition to existing `-qso_date_utc` | SATISFIED (static) | Sentinel condition in `log_table.html` line 1 with correct parenthesization; 4 tests in `test_sse_sentinel.py` |

No orphaned requirements found: REQUIREMENTS.md maps only SORT-03 and SORT-04 to Phase 49, both claimed by `49-01-PLAN.md`.

### Anti-Patterns Found

No anti-patterns found. Scanned `app/qso/service.py`, `app/qso/ui_router.py`, `templates/log/log_table.html`, `tests/test_view_dict.py`, `tests/test_service_sort.py`, `tests/test_sse_sentinel.py` for TODO/FIXME, placeholder patterns, empty returns, and stub indicators. Clean.

The SUMMARY notes the deviation from plan in `test_view_dict.py` (using `model_construct()` instead of `QSO()` to avoid Beanie's DB init requirement). This is correct behavior — the plan's specification was impossible without DB, the auto-fix was the right call, and the test validates the actual contract (`_qso_to_view_dict()` maps `qso.created_at` to `result["created_at"]`).

### Human Verification Required

#### 1. MongoDB-dependent test suite

**Test:** In an environment with MongoDB running at localhost:27017, run:
```
uv run pytest tests/test_service_sort.py tests/test_sse_sentinel.py -x -q
```
**Expected:** All tests pass (0 failures). The SUMMARY reports "2 passed, 7 skipped" in a no-MongoDB environment — when MongoDB is available, expect approximately 7 tests to pass (the 3 DB-dependent sort tests + 4 sentinel HTTP integration tests).
**Why human:** These tests require a live MongoDB instance. The verifier's environment does not have MongoDB available at localhost:27017. Static analysis confirms all test logic is correct and complete, but runtime confirmation is required for full SORT-03 and SORT-04 satisfaction.

### Gaps Summary

No structural gaps found. All 7 observable truths are satisfied by the codebase as written. All 6 required artifacts exist, are substantive, and are wired correctly. Both SORT-03 and SORT-04 requirements are covered by implementation and tests.

The human_needed status is solely due to the 7 MongoDB-dependent tests that cannot be executed without a live MongoDB instance. Static evidence strongly indicates they will pass.

---

_Verified: 2026-04-23T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
