# Phase 4: ADIF Import & Export - Research

**Researched:** 2026-04-03
**Domain:** ADIF file I/O, FastAPI multipart upload, streaming export, MongoDB bulk insert, duplicate detection at batch scale
**Confidence:** HIGH

---

## Summary

Phase 4 builds on a solid foundation: the ADIF parser and serializer are already written and round-trip tested (Phase 1), `build_qso_dict()` and `find_duplicate()` are available (Phase 3), and the QSO model uses `extra="allow"` so arbitrary ADIF fields store verbatim. The implementation work is primarily **wiring** existing pieces together via two new endpoints (import, export) plus per-record duplicate checking during import.

The key blocker — **synchronous vs async import** — resolves clearly in favor of **synchronous within the request handler** for this project's self-hosted, single-operator use case. Real-world ADIF logbooks for a typical amateur radio operator fit in 200 KB–5 MB. At 100–200 QSOs/second MongoDB insertion throughput (with individual inserts inside duplicate-check loops), a 10,000-QSO file finishes in under 60 seconds — well within a 90-second Nginx/Gunicorn timeout with a sane `max_file_size` guard. Background tasks via `FastAPI BackgroundTasks` are same-process and provide no UX advantage: the user cannot poll for status and the response returns only after the task completes anyway. Celery + Redis adds an operational dependency incompatible with the project's self-hosted goal.

**Primary recommendation:** Implement import synchronously: read file, parse ADIF, iterate records calling `find_duplicate()` + insert one at a time, return a complete import report in the HTTP response. Add a 10 MB file size guard to bound worst-case latency. Export via `StreamingResponse` with a generator to avoid buffering large logbooks in memory.

---

## Blocker Resolution: Sync vs Async Import

**Decision: Synchronous import within the request handler.**

### Why Not FastAPI BackgroundTasks

`BackgroundTasks` runs in the **same process** after the response is sent. For import this is counter-productive: the operator needs the import report (accepted / duplicates / errors) to appear in the response. There is no way to return a useful response *and* process in the background simultaneously without a polling/job-status system — which is the full Celery architecture.

**Verdict:** BackgroundTasks is not appropriate. It solves "fire and forget" notifications, not "return a result after processing."

### Why Not Celery + Redis

- Redis is an additional operational dependency (container, process, port, persistence config)
- Self-hosted operators running Docker Compose or a single VPS would need to manage Redis + Celery workers
- Adds failure modes: Redis connection, worker availability, result backend expiration
- Overkill: amateur radio logbooks are not "big data"

**Verdict:** Redis adds unacceptable operational complexity for the self-hosted use case.

### Practical File Size Analysis

| File size | Approx QSOs | Estimated insert time | Verdict |
|-----------|-------------|----------------------|---------|
| 200 KB | ~500 QSOs | ~5 seconds | Trivial |
| 2 MB | ~5,000 QSOs | ~50 seconds | Acceptable |
| 10 MB | ~25,000 QSOs | ~250 seconds | Needs guard |
| 50 MB+ | 100k+ QSOs | Minutes | Must reject |

Assumptions: each QSO ~400 bytes in ADIF; `find_duplicate()` adds 1 MongoDB read per record; `qso.insert()` adds 1 write; sequential = ~5 ms/QSO on local MongoDB.

**Practical constraint:** Set `MAX_IMPORT_FILE_BYTES = 10 * 1024 * 1024` (10 MB). This covers virtually all real-world logbooks (active DXers with 50k+ QSOs are edge cases; they can batch-import in chunks). Return HTTP 413 if exceeded.

**Confidence:** MEDIUM — latency estimates from first principles. Validated by: upload + parse is CPU-bound (fast), bottleneck is per-record MongoDB round-trips. Bulk insert would be faster but skips per-record duplicate detection (required by spec).

---

## Standard Stack

### Core (no new dependencies needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi` | ≥0.135.0 (installed) | Import/export endpoints | Already in stack |
| `python-multipart` | bundled with `fastapi[standard]` | Multipart file upload parsing | Required for `UploadFile` |
| `app.adif.parser.parse_adi` | Phase 1 | Parse uploaded ADIF text | Already written, tested |
| `app.adif.serializer.serialize_adi` | Phase 1 | Serialize QSOs to ADIF | Already written, tested |
| `app.qso.service.find_duplicate` | Phase 3 | Per-record duplicate detection | Already written |
| `app.qso.service.build_qso_dict` | Phase 3 | Build QSO dict from parsed record | Already written |
| `fastapi.responses.StreamingResponse` | fastapi | Stream export without buffering | Built-in, no dep |

**No new pip dependencies required.** `python-multipart` is already included via `fastapi[standard]`.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `beanie.Document.insert_many()` | ≥2.1.0 (installed) | Bulk insert without dup check | Export-only use case (not import — import needs per-record dup detection) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Synchronous import | FastAPI BackgroundTasks | No advantage: can't return report in background. No-go. |
| Synchronous import | Celery + Redis | Operational complexity incompatible with self-hosted goal. No-go. |
| StreamingResponse (export) | Build full string, return Response | Works for small logbooks; wastes memory for large ones. Use StreamingResponse. |
| Sequential insert (import) | `insert_many(ordered=False)` | Bulk insert is faster but skips `find_duplicate()` per record — violates requirement ADIF-02. |

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── adif/
│   ├── parser.py          # Phase 1 — no changes
│   ├── serializer.py      # Phase 1 — no changes
│   └── import_router.py   # NEW: POST /api/adif/import, GET /api/adif/export
app/qso/
│   └── ui_router.py       # Add UI routes for import/export pages
templates/
│   └── log/
│       ├── import.html    # Upload form
│       └── import_report.html  # Import result partial
```

Or alternatively add import/export endpoints directly to the existing `app/qso/router.py` (fewer files). Either approach works; a dedicated `app/adif/` router keeps ADIF I/O separate from QSO CRUD.

### Pattern 1: Multipart File Upload (Import)

```python
# Source: https://fastapi.tiangolo.com/tutorial/request-files/
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi import File
from typing import Annotated

MAX_IMPORT_FILE_BYTES = 10 * 1024 * 1024  # 10 MB guard

router = APIRouter(prefix="/api/adif", tags=["adif"])

@router.post("/import", status_code=status.HTTP_200_OK)
async def import_adif(
    file: Annotated[UploadFile, File(description="ADIF .adi or .adif file")],
    operator: str = Depends(get_current_operator_callsign),
) -> dict:
    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_IMPORT_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
    text = raw_bytes.decode("utf-8", errors="replace")
    records, parse_errors = parse_adi(text)
    # ... iterate, dup-check, insert, collect report ...
    return {"accepted": accepted, "duplicates": duplicates, "errors": parse_errors}
```

**Key points:**
- `UploadFile` spools to disk automatically for large files — safe for 10 MB
- `await file.read()` returns `bytes`; decode to `str` before passing to `parse_adi()`
- File size check AFTER read (UploadFile has no pre-read size; check `len(raw_bytes)`)
- Accept both `.adi` and `.adif` extensions — validate by trying to parse, not by filename

### Pattern 2: Per-Record Import Loop (Duplicate Detection)

```python
accepted = []
duplicates = []
errors = list(parse_errors)  # parse errors from parse_adi()

for idx, record in enumerate(records):
    # Validate required fields
    if not all(k in record for k in ("CALL", "QSO_DATE", "TIME_ON", "BAND", "MODE")):
        errors.append({"record_index": idx, "error": "Missing required field(s)"})
        continue

    try:
        qso_dict = build_qso_dict(record, operator)
    except (ValueError, KeyError) as exc:
        errors.append({"record_index": idx, "error": str(exc)})
        continue

    dup = await find_duplicate(
        operator=operator,
        call=qso_dict["CALL"],
        band=qso_dict["BAND"],
        mode=qso_dict["MODE"],
        qso_date_utc=qso_dict["qso_date_utc"],
    )

    if dup is not None:
        duplicates.append({
            "record_index": idx,
            "call": qso_dict["CALL"],
            "existing_id": str(dup.id),
        })
        # Do NOT insert — operator reviews report
        continue

    qso = QSO(**qso_dict)
    await qso.insert()
    accepted.append({"record_index": idx, "call": qso_dict["CALL"], "id": str(qso.id)})
```

**Critical:** Do not use `insert_many()` for import — it bypasses per-record `find_duplicate()`. The spec requires duplicate report per record.

### Pattern 3: Streaming Export (StreamingResponse)

```python
# Source: https://www.starlette.io/responses/#streamingresponse
from fastapi.responses import StreamingResponse

@router.get("/export")
async def export_adif(
    operator: str = Depends(get_current_operator_callsign),
):
    async def adif_generator():
        header = f"<ADIF_VER:5>3.1.4\n<PROGRAMID:5>ollog\n<CREATED_TIMESTAMP:15>{...}\n"
        yield header + "<EOH>\n\n"

        qsos = await QSO.find({"_operator": operator, "_deleted": False}).to_list()
        for qso in qsos:
            record = _qso_to_adif_dict(qso)
            yield serialize_adi([record])  # one record at a time

    filename = f"{operator}_logbook.adi"
    return StreamingResponse(
        adif_generator(),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

**Note:** `serialize_adi()` expects a list; pass `[record]` to get one record's ADIF text. Yield the header once, then yield each serialized record.

**Alternative for small logbooks:** Load all QSOs, call `serialize_adi(all_records)`, return as `Response(content=..., media_type="text/plain")`. Simpler but loads everything into memory. Streaming is safer for large logbooks.

### Pattern 4: QSO to ADIF Record Dict (Export)

The QSO Beanie document stores fields in `model_extra` (via `extra="allow"`). Reconstruct the ADIF dict for export:

```python
def _qso_to_adif_dict(qso: QSO) -> dict:
    """Convert QSO document back to uppercase ADIF field dict for serialization."""
    # Start with declared fields
    d = {}
    if qso.CALL:
        d["CALL"] = qso.CALL
    if qso.BAND:
        d["BAND"] = qso.BAND
    if qso.MODE:
        d["MODE"] = qso.MODE

    # Pull all extra ADIF fields (QSO_DATE, TIME_ON, FREQ, RST_SENT, RST_RCVD,
    # APP_ fields, USERDEF fields, etc.)
    extra = qso.model_extra or {}
    for key, val in extra.items():
        # Skip internal non-ADIF keys
        if key in ("qso_date_utc",):
            continue
        if val is not None:
            d[key] = str(val)

    return d
```

**Critical for round-trip:** `QSO_DATE` and `TIME_ON` are stored in `model_extra` (see `build_qso_dict()` which keeps them verbatim). `qso_date_utc` is an internal datetime field — must NOT be exported as an ADIF field.

### Anti-Patterns to Avoid

- **Bulk insert for import:** `insert_many()` skips `find_duplicate()` per record — violates ADIF-02
- **Loading all QSOs into memory for export then returning `bytes`:** Use StreamingResponse instead
- **Relying on file extension for format detection:** `.adi` and `.adif` are the same format; validate by parsing
- **Silent record drops:** Every parse error and every duplicate must appear in the import report — ADIF-01 explicitly requires no silent drops
- **Exporting `qso_date_utc` as ADIF field:** This is an internal datetime field. Export `QSO_DATE` + `TIME_ON` from `model_extra`

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ADIF parsing | Custom parser | `app.adif.parser.parse_adi` (Phase 1) | Already tested, handles edge cases |
| ADIF serialization | Custom formatter | `app.adif.serializer.serialize_adi` (Phase 1) | Round-trip tested, correct UTF-8 byte counting |
| Multipart upload | Manual MIME parsing | FastAPI `UploadFile` | Handles spooling, temp files, async reads |
| Duplicate detection | Custom window query | `app.qso.service.find_duplicate` (Phase 3) | Already implements ±2 min fuzzy window |
| QSO dict building | Inline field mapping | `app.qso.service.build_qso_dict` (Phase 3) | Handles BAND/MODE normalization, datetime parsing |
| Streaming | Buffer all then send | `StreamingResponse` with generator | Memory-efficient for large logbooks |

**Key insight:** Phase 4 is almost entirely composition of existing pieces. The new code is the import loop, the export generator, and the UI templates.

---

## Common Pitfalls

### Pitfall 1: Exporting qso_date_utc as ADIF Field

**What goes wrong:** The internal `qso_date_utc` datetime ends up in the exported ADIF as `<QSO_DATE_UTC:...>` or similar, breaking parsers and violating round-trip.

**Why it happens:** `model_extra` is iterated naively; `qso_date_utc` is a declared field, not in `model_extra`, but other internal fields might leak.

**How to avoid:** In `_qso_to_adif_dict()`, explicitly skip `qso_date_utc` (and any other non-ADIF internal keys). Use an explicit blocklist: `{"qso_date_utc"}`.

**Warning signs:** Round-trip test (ADIF-04) produces different records on re-import because the field doesn't exist in the original.

### Pitfall 2: UploadFile.size Not Available Before Reading

**What goes wrong:** Checking `file.size` to reject oversized files before reading — `UploadFile.size` may be `None` if the Content-Length header is absent.

**Why it happens:** HTTP clients may not send Content-Length for streaming uploads.

**How to avoid:** Read the file first (`raw_bytes = await file.read()`), then check `len(raw_bytes)`. Return 413 after the fact. Acceptable since 10 MB reads fast.

**Warning signs:** `if file.size > MAX` returns `False` when `file.size is None`.

### Pitfall 3: UTF-8 Decode Errors Abort Import

**What goes wrong:** Calling `bytes.decode("utf-8")` raises `UnicodeDecodeError` on Latin-1 encoded files (common in old ADIF exports from Windows logging software).

**Why it happens:** ADIF spec says UTF-8 but real-world files may be ISO-8859-1.

**How to avoid:** Use `raw_bytes.decode("utf-8", errors="replace")` — already the fallback in `parse_adi()` for individual values, but the file-level decode also needs a fallback.

**Warning signs:** Import fails entirely on valid-looking .adi files from older software.

### Pitfall 4: Records Missing Required Fields Crash build_qso_dict

**What goes wrong:** `build_qso_dict()` calls `parse_adif_datetime(result["QSO_DATE"], result["TIME_ON"])` — raises `KeyError` if `QSO_DATE` or `TIME_ON` absent.

**Why it happens:** ADIF spec technically requires these fields, but real-world files may omit them.

**How to avoid:** Validate required fields (`CALL`, `QSO_DATE`, `TIME_ON`, `BAND`, `MODE`) before calling `build_qso_dict()`. Append to `errors` list, continue to next record. Never let one bad record abort the import.

**Warning signs:** Import returns 500 instead of import report with errors.

### Pitfall 5: Import Report Missing Record Context

**What goes wrong:** Errors/duplicates report record count but operator can't identify which QSO caused the problem.

**Why it happens:** Report only includes `record_index` (0-based position in file).

**How to avoid:** Include `CALL`, `QSO_DATE`, `TIME_ON` (when available) in every report entry — enough for the operator to locate the QSO in their original file.

### Pitfall 6: Export Includes Soft-Deleted QSOs

**What goes wrong:** Export includes QSOs where `_deleted: true`.

**Why it happens:** Forgetting to filter `_deleted: False` in the export query.

**How to avoid:** Always filter `{"_operator": operator, "_deleted": False}` in export query — same as all other operator-scoped queries in the codebase.

---

## Code Examples

### Import Endpoint Skeleton

```python
# Source: FastAPI docs + project patterns
@router.post("/import", status_code=200)
async def import_adif(
    file: Annotated[UploadFile, File()],
    operator: str = Depends(get_current_operator_callsign),
) -> dict:
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")

    text = raw.decode("utf-8", errors="replace")
    records, parse_errors = parse_adi(text)

    accepted, duplicates, errors = [], [], list(parse_errors)

    for idx, record in enumerate(records):
        if not {"CALL", "QSO_DATE", "TIME_ON", "BAND", "MODE"} <= set(record):
            errors.append({"record_index": idx, "error": "Missing required fields",
                           "call": record.get("CALL", "?")})
            continue
        try:
            qso_dict = build_qso_dict(record, operator)
        except (ValueError, KeyError) as exc:
            errors.append({"record_index": idx, "error": str(exc),
                           "call": record.get("CALL", "?")})
            continue

        dup = await find_duplicate(
            operator=operator,
            call=qso_dict["CALL"],
            band=qso_dict["BAND"],
            mode=qso_dict["MODE"],
            qso_date_utc=qso_dict["qso_date_utc"],
        )
        if dup:
            duplicates.append({"record_index": idx, "call": qso_dict["CALL"],
                               "existing_id": str(dup.id)})
            continue

        qso = QSO(**qso_dict)
        await qso.insert()
        accepted.append({"record_index": idx, "call": qso_dict["CALL"], "id": str(qso.id)})

    return {
        "total_records": len(records),
        "accepted": accepted,
        "duplicates": duplicates,
        "errors": errors,
    }
```

### Export Endpoint Skeleton

```python
# Source: Starlette StreamingResponse + project patterns
INTERNAL_FIELDS = {"qso_date_utc"}
BEANIE_FIELDS = {"operator_callsign", "is_deleted", "id"}

def _qso_to_adif_dict(qso: QSO) -> dict:
    d = {}
    if qso.CALL: d["CALL"] = qso.CALL
    if qso.BAND: d["BAND"] = qso.BAND
    if qso.MODE: d["MODE"] = qso.MODE
    for k, v in (qso.model_extra or {}).items():
        if k not in INTERNAL_FIELDS and v is not None:
            d[k] = str(v)
    return d

@router.get("/export")
async def export_adif(
    operator: str = Depends(get_current_operator_callsign),
):
    async def generate():
        yield f"<ADIF_VER:5>3.1.4\n<PROGRAMID:5>ollog\n<EOH>\n\n"
        qsos = await QSO.find({"_operator": operator, "_deleted": False}).to_list()
        for qso in qsos:
            yield serialize_adi([_qso_to_adif_dict(qso)])

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{operator}_logbook.adi"'},
    )
```

### Round-Trip Integration Test Skeleton (04-04)

```python
# Source: project test patterns (tests/test_adif_roundtrip.py)
async def test_export_import_roundtrip(async_client, auth_headers):
    # 1. Import a known ADIF file with APP_ and USERDEF fields
    with open("tests/fixtures/sample.adi", "rb") as f:
        resp = await async_client.post("/api/adif/import",
            files={"file": ("sample.adi", f, "text/plain")},
            headers=auth_headers)
    assert resp.status_code == 200
    report = resp.json()
    assert report["accepted"] > 0

    # 2. Export
    resp = await async_client.get("/api/adif/export", headers=auth_headers)
    assert resp.status_code == 200
    exported_text = resp.text

    # 3. Parse exported ADIF
    exported_records, errors = parse_adi(exported_text)
    assert errors == []

    # 4. Re-import (all should be duplicates — no new inserts)
    resp2 = await async_client.post("/api/adif/import",
        files={"file": ("reimport.adi", exported_text.encode(), "text/plain")},
        headers=auth_headers)
    report2 = resp2.json()
    assert report2["accepted"] == 0
    assert len(report2["duplicates"]) == report["accepted"]

    # 5. APP_ and USERDEF fields preserved
    app_record = next((r for r in exported_records if "APP_MYLOGGER_SCORE" in r), None)
    assert app_record is not None
    assert app_record["APP_MYLOGGER_SCORE"] == "100"
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| adif-io (PyPI) | Custom `parse_adi()` from Phase 1 | Already committed — no external dep |
| Celery for background jobs | Synchronous import within request | No operational overhead; fits logbook scale |
| FileResponse with temp file | StreamingResponse with generator | Memory-efficient; no temp file management |

---

## Open Questions

1. **UI integration depth for import**
   - What we know: HTMX + Jinja2 pattern is established
   - What's unclear: Should import be a dedicated page or a modal/panel on the log view page?
   - Recommendation: Dedicated `/log/import` page with upload form and full-page report; simplest to implement and test

2. **Export filter options (ADIF-03)**
   - What we know: Plan 04-03 says "optional filters"
   - What's unclear: Which filters are needed (date range? band? mode?)
   - Recommendation: Mirror the existing list endpoint filters (date_from, date_to, band, mode) — the get_qso_page() service already supports them

3. **Duplicate handling in import report UI**
   - What we know: Spec says "operator reviews" — no auto-deletion
   - What's unclear: Does the UI allow force-inserting individual duplicates from the report?
   - Recommendation: Phase 4 shows the report; force-import of individual duplicates is a stretch goal. The API endpoint can accept `force=True` for a follow-up call.

4. **USERDEF field header parsing**
   - What we know: `parse_adi()` passes USERDEF fields in records through verbatim
   - What's unclear: ADIF spec defines USERDEF field names in the header — current parser skips the header. Are USERDEF definitions needed for correct value parsing?
   - Recommendation: Current parser behavior is correct — USERDEF values are just strings; no type coercion needed. Header-defined USERDEF metadata (field type, min/max) is advisory only for import/export purposes.

---

## Sources

### Primary (HIGH confidence)
- FastAPI official docs (https://fastapi.tiangolo.com/tutorial/request-files/) — UploadFile, multipart upload patterns
- FastAPI official docs (https://fastapi.tiangolo.com/tutorial/background-tasks/) — BackgroundTasks behavior, Celery comparison
- FastAPI official docs (https://fastapi.tiangolo.com/advanced/custom-response/) — StreamingResponse, FileResponse, Content-Disposition
- Starlette docs (https://www.starlette.io/responses/#streamingresponse) — generator-based streaming
- PyMongo docs (https://pymongo.readthedocs.io) — insert_many ordered=False behavior
- Beanie ODM docs (https://beanie-odm.dev/tutorial/inserting-into-the-database/) — insert_many usage
- Project source: app/adif/parser.py, app/adif/serializer.py, app/qso/service.py, app/qso/router.py

### Secondary (MEDIUM confidence)
- PyMongo insert_many ordered=False: multiple source corroboration — continue-on-error behavior confirmed
- Typical ADIF logbook size estimates: derived from known field sizes and typical amateur radio activity levels (LOW-MEDIUM — no official benchmark found)

### Tertiary (LOW confidence)
- Per-record insert throughput (~5 ms/QSO estimate): derived from first principles; actual performance depends on MongoDB configuration, hardware, network. Validate with a timing test during implementation.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use in the project; patterns from official FastAPI/Starlette docs
- Architecture: HIGH — composition of Phase 1/3 components; import loop pattern is straightforward
- Blocker resolution (sync vs async): HIGH — BackgroundTasks docs are clear; Celery complexity is well-documented; logbook scale analysis is sound reasoning
- Pitfalls: HIGH — derived from code inspection of existing parser, serializer, and service layer
- Performance estimates: MEDIUM — first-principles estimate, not benchmarked

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (stable libraries; no fast-moving ecosystem concerns)
