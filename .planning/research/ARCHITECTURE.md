# Architecture Patterns

**Domain:** Multi-operator ham radio QSO logbook
**Researched:** 2026-04-03
**Confidence:** MEDIUM (training data; external verification blocked — flag for validation)

---

## Recommended Architecture

A layered, service-oriented monolith is the right shape for this project. It is not a microservices system (premature for a self-hosted ham radio log), but it has clean internal component boundaries so pieces can be extracted later. Three tiers:

```
[Web UI]  ←→  [REST API / Auth layer]  ←→  [MongoDB]
                       |
               [ADIF Parser / Serializer]
                       |
               [Import / Export Service]
```

The API tier owns all business logic. The UI is a thin client. ADIF parsing is a pure library with no database dependency — this keeps it testable and reusable by both the REST endpoints and the import/export service.

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **ADIF Library** | Parse `.adi`/`.adif` text → Python dicts; serialize Python dicts → ADIF text | API layer, Import/Export service |
| **Auth Service** | JWT or session issuance, callsign-to-account binding, admin role check | API layer only |
| **QSO API** | CRUD endpoints for QSOs; enforces operator isolation; validates ADIF fields | MongoDB, ADIF Library, Auth Service |
| **Import Service** | Accept multipart `.adi`/`.adif` upload; batch-write QSOs under authenticated operator | QSO API (or MongoDB directly with operator context), ADIF Library |
| **Export Service** | Query QSOs for operator, serialize to ADIF, stream file download | MongoDB, ADIF Library |
| **Admin API** | User/account management (create, disable, reset); no QSO logic | MongoDB (users collection), Auth Service |
| **Web UI** | Form-based QSO entry, log view/search, import/export triggers, admin panel | REST API only |
| **MongoDB** | Persistent storage: QSOs collection, users collection | API layer only (never from UI) |

The UI never touches MongoDB directly. The ADIF Library never touches MongoDB. These two constraints keep the architecture clean.

---

## Data Flow: QSO Entry (Manual)

```
Operator fills web form
  → POST /api/qsos  (JSON body: ADIF field names as keys)
    → Auth middleware validates JWT, extracts callsign
      → QSO API validates required fields (CALL, QSO_DATE, TIME_ON, BAND or FREQ, MODE)
        → ADIF Library normalizes field names (uppercase) and types
          → MongoDB insert into `qsos` collection with operator field injected
            → Return created document (with _id)
              → UI appends to log view
```

---

## Data Flow: ADIF File Import

```
Operator selects .adi/.adif file in UI
  → POST /api/import  (multipart/form-data)
    → Auth middleware validates JWT, extracts callsign
      → Import Service streams/reads file
        → ADIF Library parses into list of QSO dicts
          → For each QSO dict:
              - Inject operator_callsign field
              - Validate required fields (skip or accumulate errors)
              - Bulk-insert to MongoDB (ordered=False for concurrency resilience)
            → Return summary: {accepted: N, rejected: M, errors: [...]}
```

Using `ordered=False` on bulk inserts means one bad QSO does not abort the whole batch — critical for real-world ADIF files that may contain edge-case records.

---

## Data Flow: ADIF File Export

```
Operator clicks "Export Log" in UI
  → GET /api/export  (query params: optional date range, band, mode filters)
    → Auth middleware validates JWT, extracts callsign
      → Export Service queries MongoDB for operator's QSOs (with filters)
        → ADIF Library serializes each document to ADIF record
          → Streaming HTTP response with Content-Disposition: attachment
            → Browser saves .adi file
```

Streaming the response (generator pattern in Python) avoids loading thousands of QSOs into memory at once.

---

## MongoDB Document Structure

### Collection: `qsos`

One document per QSO. Field names follow ADIF standard (uppercase strings) with two system fields prefixed with underscore.

```json
{
  "_id": "ObjectId(...)",
  "_operator": "W1AW",
  "_imported_at": "2026-04-03T14:32:00Z",
  "CALL": "K9XYZ",
  "QSO_DATE": "20260403",
  "TIME_ON": "1430",
  "BAND": "20M",
  "FREQ": "14.225",
  "MODE": "SSB",
  "RST_SENT": "59",
  "RST_RCVD": "57",
  "NAME": "Bob",
  "QTH": "Chicago, IL",
  "COMMENT": "Good signal, slight QSB",
  "GRIDSQUARE": "EN61",
  "DXCC": "291",
  "COUNTRY": "United States",
  "STATE": "IL",
  "CONT": "NA",
  "IOTA": "",
  "TX_PWR": "100",
  "ANT_AZ": "",
  "NOTES": ""
}
```

**Key design decisions:**

- `_operator` is the single multi-tenancy discriminator. All queries filter on this field first.
- ADIF field names stored verbatim (uppercase). No translation layer needed on read — ADIF export is trivial.
- `_imported_at` is server-assigned on write. Not an ADIF field so prefixed with `_`.
- No nested documents. ADIF is flat; keep MongoDB documents flat. Avoids projection complexity.
- Flexible schema: operators may log non-standard ADIF fields (contest software extensions, app-defined fields). Store them as-is. MongoDB handles this naturally.

### Collection: `users`

```json
{
  "_id": "ObjectId(...)",
  "callsign": "W1AW",
  "callsign_normalized": "w1aw",
  "email": "op@example.com",
  "password_hash": "bcrypt...",
  "role": "operator",
  "active": true,
  "created_at": "2026-01-15T10:00:00Z",
  "last_login": "2026-04-03T14:00:00Z"
}
```

`callsign_normalized` (lowercase) enables case-insensitive uniqueness index. Callsigns are case-insensitive in ham radio practice.

### Indexes

```
qsos:
  { _operator: 1, QSO_DATE: -1, TIME_ON: -1 }  // primary query pattern: operator's log sorted by date
  { _operator: 1, CALL: 1 }                     // search by contacted callsign
  { _operator: 1, BAND: 1, MODE: 1 }            // filter by band/mode
  { _operator: 1, _id: 1 }                      // pagination cursor

users:
  { callsign_normalized: 1 }  // unique index
  { email: 1 }                // unique index
```

All QSO indexes lead with `_operator`. This is the most important performance decision — without it, any query scans the entire collection as the log grows.

---

## Multi-Operator Isolation

**Recommendation: shared collection with `_operator` field — not per-operator collections.**

Rationale:
- Per-operator collections seem intuitive but cause operational problems: dynamic collection creation, inability to use collection-level indexes efficiently across operators, harder aggregation queries for admin views.
- Shared collection with a leading `_operator` in every compound index gives equivalent query isolation with none of the operational overhead.
- MongoDB handles millions of documents in a single collection without degradation when indexes are correct.
- Auth middleware injects the operator's callsign into every query — it is structurally impossible for the API to return another operator's QSOs without an explicit bug in the auth layer.

**Isolation enforcement pattern:**

```python
# In every QSO query, operator is always injected from the JWT, never from request body
def get_qsos(operator_callsign: str, filters: dict) -> list:
    query = {"_operator": operator_callsign, **filters}
    return db.qsos.find(query)
```

The operator callsign never comes from user-supplied query parameters for read/write operations. It comes only from the validated auth token.

---

## ADIF Parsing Architecture

The ADIF parser is a standalone Python module with no framework dependencies.

**ADIF format recap:**

```
<CALL:5>W1AW <BAND:3>20M <MODE:3>SSB <QSO_DATE:8>20260403 <TIME_ON:4>1430 <EOR>
```

Each field: `<FIELDNAME:LENGTH>value`. Record ends with `<EOR>`. File header ends with `<EOH>`.

**Parser responsibilities:**

1. Tokenize: scan for `<TAG:LEN>` markers, extract value by length
2. Handle header (ignore everything before `<EOH>`)
3. Build dict per record: `{"CALL": "W1AW", "BAND": "20M", ...}`
4. Normalize field names to uppercase
5. Strip leading/trailing whitespace from values
6. Accumulate records until EOF

**Serializer responsibilities:**

1. For each QSO dict, emit `<FIELDNAME:len(value)>value ` for each field
2. Skip system fields (`_operator`, `_id`, `_imported_at`)
3. Emit `<EOR>\n` to close each record
4. Prepend ADIF header block with timestamp and app name

**Parser lives at:** `app/adif/parser.py` — pure functions, no class state required.

---

## Patterns to Follow

### Pattern 1: Operator Context Injection at Auth Boundary

**What:** Auth middleware extracts callsign from JWT and attaches it to the request context object. All downstream handlers read operator identity from context, never from request data.

**When:** Every QSO read, write, import, export operation.

**Why:** Single enforcement point. If a bug later accepts a spoofed callsign in a request body, the auth boundary still prevails.

### Pattern 2: ADIF-as-Internal-Format

**What:** Store ADIF field names directly as MongoDB document keys. Do not translate to a different internal schema and back.

**When:** QSO document design.

**Why:** Eliminates a translation layer. ADIF import maps 1:1 to document fields. ADIF export maps 1:1 from document fields. Fewer bugs, faster implementation, standard field names are self-documenting.

### Pattern 3: Streaming Export

**What:** Use Python generator + Flask/FastAPI streaming response for export.

**When:** ADIF export endpoint.

**Why:** Operators with 10,000+ QSOs (common for active DX chasers) should not cause memory spikes. MongoDB cursor → generator → streaming response handles arbitrary log sizes.

### Pattern 4: Bulk Insert with ordered=False for Import

**What:** Use `pymongo` `insert_many` with `ordered=False`.

**When:** ADIF file import.

**Why:** One malformed record in a 5,000-QSO import should not abort the entire batch. Collect errors, return summary. `ordered=False` also allows MongoDB to parallelize writes internally.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Per-Operator Collections

**What:** Creating a separate MongoDB collection per callsign (e.g., `qsos_w1aw`, `qsos_k9xyz`).

**Why bad:** Dynamic collection creation is operationally fragile. Cross-operator admin queries require collection enumeration. Indexes cannot span collections. Collection count grows unbounded.

**Instead:** Single `qsos` collection, `_operator` field, compound indexes leading with `_operator`.

### Anti-Pattern 2: Storing ADIF-Encoded Strings in MongoDB

**What:** Storing the raw ADIF string `<CALL:5>W1AW <BAND:3>20M...` as a single document field.

**Why bad:** Loses all queryability. Cannot filter by band, mode, callsign, or date without parsing at query time. Defeats the purpose of a database.

**Instead:** Parse ADIF on ingest, store as flat document with individual fields.

### Anti-Pattern 3: Translating ADIF Field Names to Snake Case

**What:** Storing `call` instead of `CALL`, `qso_date` instead of `QSO_DATE`.

**Why bad:** Creates a translation layer that must be maintained bidirectionally. ADIF spec uses uppercase; deviating means every import and export passes through a renaming step. Subtle mismatches cause bugs.

**Instead:** Store uppercase ADIF field names verbatim. MongoDB has no issue with uppercase keys.

### Anti-Pattern 4: Accepting Operator Identity from Request Body

**What:** `POST /api/qsos` body includes `"operator": "W1AW"` and the API trusts that value.

**Why bad:** Any authenticated user could forge another operator's callsign and write to their log.

**Instead:** Operator identity flows only from the auth token. The API layer injects it; it is never read from request payloads.

---

## Suggested Build Order

Dependencies flow upward — build the foundation before what depends on it.

```
1. ADIF Library (parser + serializer)
      No dependencies. Fully testable in isolation.

2. MongoDB Schema + Indexes
      Defines the data contract. Everything else depends on this.

3. Auth Service (user model, JWT issue/validate, admin role)
      QSO API depends on auth. Build and test auth before protecting routes.

4. QSO API (CRUD endpoints, protected by auth)
      Depends on: ADIF Library (field normalization), MongoDB, Auth.

5. Import Service
      Depends on: ADIF Library (parsing), QSO API or direct MongoDB write, Auth.

6. Export Service
      Depends on: MongoDB, ADIF Library (serialization), Auth.

7. Admin API (user management)
      Depends on: Auth Service, MongoDB users collection.

8. Web UI
      Depends on: all API endpoints. Build last so the API contract is stable.
      Can build incrementally: log view → QSO entry form → import/export → admin panel.
```

**Critical path:** ADIF Library → MongoDB Schema → Auth → QSO API. These four are the skeleton everything else hangs on.

---

## Scalability Considerations

| Concern | At 100 users | At 10K users | At 1M users |
|---------|--------------|--------------|-------------|
| QSO query performance | Single-node MongoDB, default indexes sufficient | Compound indexes on `_operator` become critical | Sharding on `_operator` hash; read replicas for export |
| Import throughput | Synchronous bulk insert fine | Async task queue (Celery/RQ) for large files | Same, plus rate limiting |
| Export memory | Streaming response handles it | Same | Same |
| Concurrent writes | MongoDB document-level locking sufficient | Same | Write concern tuning, potential replica set |
| Auth | Stateless JWT scales horizontally | Same | Same |

For a self-hosted installation, the 100-user scale is the realistic target. Compound indexes on `_operator` are the single most impactful scaling decision at all sizes.

---

## Deployment Topology

```
[Nginx / Caddy]  (TLS termination, static file serving)
       |
[Python App Server]  (Gunicorn + Flask or Uvicorn + FastAPI)
       |
[MongoDB]  (single node for self-hosted; Atlas for cloud)
```

Static assets (Web UI) are served by the reverse proxy, not the Python app. This keeps the Python process free for API requests.

For self-hosted Docker deployment:
- `docker-compose.yml` with three services: `nginx`, `api`, `mongodb`
- MongoDB data volume mounted for persistence
- Environment variables for secrets (JWT secret, MongoDB URI)

---

## Sources

All findings are based on training knowledge (confidence: MEDIUM). External verification was blocked during research. The following areas should be validated before implementation:

- ADIF 3.1.4 specification field list: https://adif.org/314/ADIF_314.htm (verify current version)
- pymongo `insert_many` `ordered` parameter behavior: https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html
- MongoDB compound index leading-field constraint behavior: https://www.mongodb.com/docs/manual/core/indexes/index-types/index-compound/

**Confidence notes:**
- ADIF format structure (tag-length-value, EOR, EOH): HIGH — well-established standard, unchanged for many years
- MongoDB shared-collection vs per-collection recommendation: HIGH — standard MongoDB multi-tenancy guidance
- `ordered=False` bulk insert behavior: HIGH — core pymongo feature
- Specific ADIF field names (CALL, BAND, MODE, etc.): HIGH — defined in ADIF spec
- Streaming response pattern in Python WSGI/ASGI: HIGH — well-established
