# Phase 64 Verification

**Date:** 2026-06-12
**Status:** Passed with documented skips

## Automated Checks

```bash
.venv/bin/python -m pytest tests/test_aclog_parser.py tests/test_aclog_client.py tests/test_profile_ui.py tests/test_qso_service_collections.py
```

Result: 25 passed, 5 skipped. Skips were Mongo-backed profile UI tests when the local MongoDB fixture was unavailable.

```bash
.venv/bin/python -m ruff check app/aclog app/qso tests/test_aclog_client.py tests/test_profile_ui.py
```

Result: passed.

```bash
.venv/bin/python -m compileall app/aclog app/qso tests/test_aclog_client.py tests/test_profile_ui.py
```

Result: passed.

```bash
npm run build
```

Result: passed. Tailwind regenerated `static/css/output.css` for the new Profile Settings grid class.

```bash
git diff --check
```

Result: passed.

## Contract Checks

- Manual sync source contains `<CMD><LIST><INCLUDEALL></CMD>`.
- Existing live bridge source still contains `<VALUE>5</VALUE>`.
- Profile Sync route is scoped to `user.aclog_bridges`.
- Sync button targets `#profile-result`.
- `new-0` bridge row has no sync route.
- Sync result fragment contains `ACLog sync complete`, `Missing QSOs imported`, `Already present`, `Errors`, `ACLog sync failed`, and the ACLog reachability hint.

## Manual UAT Still Pending

- Save a real ACLog bridge, press Sync, and confirm missing QSOs import.
- Press Sync again and confirm the same records are counted as already present with no duplicate inserts.
