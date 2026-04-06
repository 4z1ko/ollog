---
phase: 16-udp-infrastructure
plan: 01
subsystem: service
tags: [refactor, adif, service-extraction, http-exception, value-error]

# Dependency graph
requires:
  - phase: 04-adif-import-export
    provides: process_import logic in app/adif/router.py

provides:
  - import_qsos_from_bytes() in app/qso/service.py (raises ValueError, not HTTPException)
  - _REQUIRED_FIELDS and _MAX_BYTES constants in app/qso/service.py
  - Thin HTTP wrapper in app/adif/router.py (ValueError → HTTPException 413)
  - Updated app/qso/ui_router.py (catches ValueError, renders same error div)

affects:
  - phase-17 (UDP handler can now call import_qsos_from_bytes from async task)
  - app/adif/router.py (import path simplified)
  - app/qso/ui_router.py (import path updated)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Service extraction: HTTP-specific exceptions (HTTPException) stay at HTTP boundary; domain functions raise ValueError"

key-files:
  created: []
  modified:
    - app/qso/service.py
    - app/adif/router.py
    - app/qso/ui_router.py

key-decisions:
  - "import_qsos_from_bytes raises ValueError (not HTTPException) — callable from any context including non-HTTP async tasks"
  - "parse_adi import inside function body (not top-level) to avoid circular imports at module load"
  - "HTTP 413 translation remains in app/adif/router.py import_adif endpoint — domain layer has zero FastAPI imports"

# One-liner
one_liner: "Extracted ADIF import core logic from HTTP router into app/qso/service.py as import_qsos_from_bytes() raising ValueError — prerequisite for UDP Phase 17 handler."

# Self-Check
## Self-Check: PASSED
- import_qsos_from_bytes exists in app/qso/service.py ✓
- Raises ValueError for size limit (not HTTPException) ✓
- app/adif/router.py translates ValueError to HTTP 413 ✓
- app/qso/ui_router.py catches ValueError, renders same error div ✓
- No process_import references remain in app/ Python files ✓
- No HTTPException imports in app/qso/service.py ✓
- uv run python -c "from app.qso.service import import_qsos_from_bytes" → OK ✓
- uv run python -c "from app.adif.router import router" → OK ✓
- uv run python -c "from app.qso.ui_router import ui_router" → OK ✓
