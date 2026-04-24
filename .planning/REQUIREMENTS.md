# Requirements: v2.6 llms.txt Support

## Overview

Serve structured, full-text documentation at standard llms.txt endpoints on the
operator app so LLM tooling can discover and consume ollog's API and field reference.

## v1 Requirements

### Endpoints (LLMS)

- [ ] **LLMS-01**: `GET /llms.txt` on the operator app (port 8000) returns a plain-text
      index: project title, one-sentence description, and links to all content sections
      available in `/llms-full.txt`
- [ ] **LLMS-02**: `GET /llms-full.txt` on the operator app (port 8000) returns all
      content (API reference, ADIF field guide, operator getting-started) as a single
      monolithic plain-text document
- [ ] **LLMS-03**: Both endpoints return `Content-Type: text/plain; charset=utf-8` and
      are excluded from the OpenAPI schema (`include_in_schema=False`)
- [ ] **LLMS-04**: Source content lives in `static/llms.txt` and `static/llms-full.txt`
      as static text files — updating content requires no Python code changes

### Content (CONTENT)

- [ ] **CONTENT-01**: `/llms-full.txt` includes the full API reference — all REST
      endpoints with method, path, auth mechanism, request fields, response shape,
      status codes, and at least one curl example per endpoint (source:
      `docs/api-reference/index.md`)
- [ ] **CONTENT-02**: `/llms-full.txt` includes the full ADIF field reference — all
      QSO field format tables, accepted values, and format conventions (QSO_DATE
      YYYYMMDD, TIME_ON HHMM/HHMMSS, band designators, RST format) (source:
      `docs/reference/adif-field-reference.md`)
- [ ] **CONTENT-03**: `/llms-full.txt` includes the operator getting-started walkthrough
      — login flow, logging a QSO via UI and REST API, ADIF import/export (source:
      `docs/getting-started/index.md`, `docs/getting-started/first-qso.md`)

## Future Requirements

- Deployment guide section in llms-full.txt (deferred — lower value for LLM tooling)
- Dynamic endpoint introspection (deferred — static file is preferred)
- Admin app llms.txt (deferred — admin is a separate service, separate audience)

## Out of Scope

- Admin app (`app/admin_main.py`) — user specified operator portion only
- Dynamic generation from FastAPI route introspection — user wants static files
- Automated regeneration from MkDocs source on build — out of scope for v2.6

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| LLMS-01 | TBD | Pending |
| LLMS-02 | TBD | Pending |
| LLMS-03 | TBD | Pending |
| LLMS-04 | TBD | Pending |
| CONTENT-01 | TBD | Pending |
| CONTENT-02 | TBD | Pending |
| CONTENT-03 | TBD | Pending |
