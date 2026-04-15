# Phase 41: Multi-Operator UDP Routing — Research

**Researched:** 2026-04-14
**Domain:** asyncio UDP routing, in-memory caching, ADIF field parsing, FastAPI lifespan wiring
**Confidence:** HIGH — all findings grounded in direct code inspection of the actual codebase

---

## Summary

Phase 41 adds an in-memory operator cache that maps callsign → User, enabling `_handle_datagram` to route each incoming UDP datagram to the correct operator's personal log based on the ADIF OPERATOR field. The architecture pattern is already established by `token_cache.py`; the implementation is a near-exact structural mirror.

The critical discovery is that **operator CRUD does not live in `app/auth/service.py`** — it lives inline in two separate routers: `app/admin/router.py` (REST API) and `app/admin/ui_router.py` (HTMX UI). The ROADMAP's reference to "auth/service.py hooks" was aspirational naming, not a description of existing functions. The `notify_refresh()` calls must be inserted directly into the router endpoint functions in both files. There are no existing `create_operator`/`enable_operator` abstraction functions to hook — the hooks go into the Beanie `insert()` and `set()` call sites in the routers.

The ADIF parser `parse_adi()` already preserves every field verbatim, including OPERATOR, as uppercase keys. `_handle_datagram` already calls `parse_adi()` and has access to `record` as a plain dict — `record.get("OPERATOR")` will retrieve the value if present. No parser changes are needed.

**Primary recommendation:** Create `app/udp/operator_cache.py` as a structural copy of `token_cache.py` with callsign-keyed lookup; insert `notify_refresh()` calls in `app/admin/router.py` and `app/admin/ui_router.py` at the three mutation sites each; expand the `_handle_datagram` routing logic to check `record.get("OPERATOR")` before falling through to the existing UDP_OPERATOR path.

---

## Standard Stack

### Core (all already in the project — no new dependencies)

| Component | Version/Location | Purpose |
|-----------|-----------------|---------|
| `asyncio.Lock` | stdlib | Thread safety for cache dict swap |
| `asyncio.DatagramProtocol` | stdlib | UDP transport base class |
| `beanie` (Beanie ODM) | existing dep | `User.find(User.enabled == True)` async query |
| `app/auth/models.User` | existing | Callsign and enabled fields |

No new packages are needed. The implementation reuses patterns already present.

---

## Architecture Patterns

### Recommended File Layout (new/changed files only)

```
app/udp/
├── operator_cache.py    # NEW — mirrors token_cache.py exactly
├── token_cache.py       # unchanged
└── server.py            # modified — OPERATOR-field routing added

app/admin/
├── router.py            # modified — notify_refresh() at 2 mutation sites
└── ui_router.py         # modified — notify_refresh() at 3 mutation sites (create, toggle, reset omitted — password reset doesn't affect routing)

app/main.py              # modified — operator_cache.load() alongside token_cache.load()

docs/admin-guide/deployment.md         # modified
docs/operator-guide/udp-adif.md        # modified
docs/reference/environment-variables.md # modified (UDP_OPERATOR description)
site/                                   # rebuilt
```

### Pattern 1: operator_cache.py — Mirror of token_cache.py

The structural contract of `token_cache.py` is:
- `__init__`: `asyncio.Lock`, `dict`, `bool _dirty = True`
- `load()`: async, queries DB, swaps cache under lock, clears dirty flag
- `resolve(key)`: async, reloads if dirty, looks up under lock
- `notify_refresh()`: sync, sets `_dirty = True`
- Module-level singleton: `operator_cache = UDPOperatorCache()`

The operator cache differs only in:
- Cache type: `dict[str, User]` keyed by uppercase callsign (not hashed token)
- Load query: `User.find(User.enabled == True).to_list()` (no ApiToken join)
- Resolve key: the callsign string from the OPERATOR field (uppercased before lookup)
- No hash step — callsigns are plaintext

```python
# Source: app/udp/token_cache.py (verified structure)
class UDPOperatorCache:
    def __init__(self) -> None:
        self._lock: asyncio.Lock = asyncio.Lock()
        self._cache: dict[str, "User"] = {}
        self._dirty: bool = True

    async def load(self) -> None:
        from app.auth.models import User
        users = await User.find(User.enabled == True).to_list()  # noqa: E712
        new_cache = {u.callsign.upper(): u for u in users}
        async with self._lock:
            self._cache = new_cache
            self._dirty = False
        logger.info("UDP operator cache loaded: %d enabled operators", len(new_cache))

    async def resolve(self, callsign: str) -> "User | None":
        if self._dirty:
            await self.load()
        async with self._lock:
            return self._cache.get(callsign.upper())

    def notify_refresh(self) -> None:
        self._dirty = True
        logger.debug("UDP operator cache marked dirty — will reload on next resolve")

operator_cache = UDPOperatorCache()
```

**Confidence: HIGH** — derived directly from reading the source file.

### Pattern 2: _handle_datagram OPERATOR routing order

Current `_handle_datagram` signature (verified):
```python
async def _handle_datagram(
    data: bytes,
    addr: tuple[str, int],
    operator: str | None,   # from QSODatagramProtocol._operator (UDP_OPERATOR)
    user: "User | None",    # from QSODatagramProtocol._user (startup-resolved)
) -> None:
```

Current flow after `parse_adi()`:
1. Pop `APP_OLLOG_TOKEN` → if present, resolve token → override `operator` and `user`
2. Check `operator is None` → drop+WARN

New routing order to insert **after** token resolution and **before** the `operator is None` guard:
1. `token_value = record.pop("APP_OLLOG_TOKEN", None)` → existing token path (unchanged)
2. **NEW:** `op_field = record.pop("OPERATOR", None)` → if present, resolve via `operator_cache.resolve(op_field)` → if resolved user found, override `operator` and `user`; if not found, drop + WARNING with callsign and addr
3. Existing: `if operator is None:` → covers UDP-06 (no OPERATOR field + no UDP_OPERATOR)

The OPERATOR field must be **popped** (not just `.get()`), same pattern as APP_OLLOG_TOKEN, so it does not propagate into the QSO document stored in MongoDB.

**Why pop:** `build_qso_dict(record, operator, profile=user)` receives the record dict. If OPERATOR is left in the dict it would attempt to persist as a QSO field. The token field already establishes the precedent of `record.pop()`.

**Confidence: HIGH** — derived from reading server.py lines 67-80.

### Pattern 3: notify_refresh() injection sites

The ROADMAP names "auth/service.py" but that file contains only JWT/password utilities (verified). The actual operator mutation sites are:

**`app/admin/router.py`** (REST API):
- `POST /admin/users/` → `create_user()` — after `await user.insert()` (line 59)
- `PATCH /admin/users/{username}/enabled` → `set_user_enabled()` — after `await user.set(...)` (line 94)
- `POST /admin/users/{username}/reset-password` — does NOT affect callsign or enabled status; skip

**`app/admin/ui_router.py`** (HTMX UI):
- `POST /admin/ui/users/create` → `create_user()` — after `await new_user.insert()` (line 144)
- `POST /admin/ui/users/{username}/toggle` → `toggle_user()` — after `await user.set(...)` (line 187)
- `POST /admin/ui/users/{username}/reset-password` — does NOT affect routing; skip

Both files currently import nothing from `app/udp/`. The injection requires:
```python
from app.udp.operator_cache import operator_cache
# ... after mutation:
operator_cache.notify_refresh()
```

No `await` — `notify_refresh()` is synchronous (verified from token_cache.py line 81).

**Confidence: HIGH** — derived from reading both router files in full.

### Pattern 4: main.py startup wiring

Current startup block (lines 34-56, verified):
```python
if settings.udp_enabled:
    from app.udp.token_cache import token_cache
    await token_cache.load()
    from app.auth.models import User as UserModel
    from app.udp.server import start_udp_listener
    # ... resolve udp_op and udp_user ...
    udp_transport, _ = await start_udp_listener(...)
```

Addition: insert `operator_cache.load()` alongside `token_cache.load()`:
```python
if settings.udp_enabled:
    from app.udp.token_cache import token_cache
    from app.udp.operator_cache import operator_cache
    await token_cache.load()
    await operator_cache.load()
    # ... rest unchanged ...
```

`operator_cache` does not need to be passed to `start_udp_listener` or stored on `QSODatagramProtocol` — it is imported directly inside `_handle_datagram` via lazy import (same pattern as `token_cache` import at line 70).

**Confidence: HIGH** — verified pattern in server.py line 70-71.

### Anti-Patterns to Avoid

- **Don't pass operator_cache as constructor param to QSODatagramProtocol.** The token_cache is already imported lazily inside `_handle_datagram`; operator_cache follows the same lazy import pattern to avoid circular imports.
- **Don't call `notify_refresh()` on password reset.** Password changes don't affect callsign or enabled status — no routing impact.
- **Don't leave OPERATOR in the record dict.** Must `record.pop("OPERATOR", None)` — not `.get()` — to prevent the field from reaching `build_qso_dict()` and MongoDB.
- **Don't use `record.get("OPERATOR")` then pop separately.** Combine into a single `pop()` call to avoid race conditions on the dict.
- **Don't change QSODatagramProtocol's constructor.** The `_operator` and `_user` instance vars remain as the UDP_OPERATOR fallback — they are still needed for requirement UDP-05.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Cache invalidation on write | Custom event bus / Redis pub-sub | dirty-flag + lazy reload (already established pattern) |
| Callsign normalization | Custom normalization logic | `.upper()` — callsigns are already stored uppercased (verified: router.py line 56, ui_router.py line 143) |
| Async-safe dict access | Thread locks from `threading` module | `asyncio.Lock` (matches token_cache pattern; single-threaded asyncio app) |

---

## Common Pitfalls

### Pitfall 1: Searching for non-existent service layer functions

**What goes wrong:** The ROADMAP says "auth/service.py calls notify_refresh() after create_operator, enable_operator, disable_operator, update_operator" — these function names do not exist. Searching for them wastes time and leads to creating an unnecessary abstraction layer.

**Why it happens:** The ROADMAP was written prescriptively (naming the desired end state) before the functions existed.

**How to avoid:** The hooks go directly into the router endpoint functions. No service layer abstraction is needed — the Beanie calls (`insert()`, `set()`) are already the mutation points.

**Warning signs:** If you find yourself creating `create_operator()`, `enable_operator()` etc. functions in `app/auth/service.py`, stop — that is unnecessary indirection that the existing codebase does not use.

### Pitfall 2: Forgetting to pop OPERATOR from the record

**What goes wrong:** Using `record.get("OPERATOR")` and not removing it causes the OPERATOR field to pass through to `build_qso_dict()` and be stored as an extra field in the QSO MongoDB document.

**Why it happens:** The APP_OLLOG_TOKEN precedent is clear (line 68: `record.pop(...)`), but it's easy to overlook when writing new routing logic.

**How to avoid:** Always `record.pop("OPERATOR", None)` — use pop, not get.

### Pitfall 3: Treating OPERATOR routing as a replacement for the token path

**What goes wrong:** Adding OPERATOR routing before the APP_OLLOG_TOKEN resolution, so a datagram with both fields gets OPERATOR routing, then the un-popped token causes a second resolution.

**Why it happens:** Unclear ordering of the routing logic.

**How to avoid:** Keep the routing order strictly: (1) pop and handle APP_OLLOG_TOKEN, (2) pop and handle OPERATOR field, (3) fall through to UDP_OPERATOR. If APP_OLLOG_TOKEN is present, it already overrides operator+user and OPERATOR field would be popped after that with no further effect.

**Note:** The ROADMAP does not explicitly address datagrams that contain both APP_OLLOG_TOKEN and OPERATOR. The safe behavior is: APP_OLLOG_TOKEN wins (it already set operator+user), then OPERATOR is popped and discarded. This is consistent with "OPERATOR field present → resolve via operator_cache" being checked after token resolution has already set the values.

### Pitfall 4: Callsign case mismatch

**What goes wrong:** OPERATOR field value "w1aw" does not match cache key "W1AW" → unexpected cache miss → datagram dropped.

**Why it happens:** Logging software may send the OPERATOR field in any case.

**How to avoid:** `.upper()` the callsign from the OPERATOR field before calling `resolve()`. The cache is already keyed by uppercase (callsigns stored uppercase at insert time).

### Pitfall 5: operator_cache.load() not called at startup

**What goes wrong:** First datagram triggers a dirty reload against a cold DB — this is fine functionally, but the startup logs won't confirm how many operators are in cache, making debugging harder.

**Why it happens:** Omitting `await operator_cache.load()` from main.py startup block.

**How to avoid:** Add `await operator_cache.load()` immediately after `await token_cache.load()` in the `if settings.udp_enabled:` block.

---

## Code Examples

### operator_cache.py load query

```python
# Source: verified against token_cache.py pattern + User model fields
async def load(self) -> None:
    from app.auth.models import User
    users = await User.find(User.enabled == True).to_list()  # noqa: E712
    new_cache: dict[str, "User"] = {u.callsign.upper(): u for u in users}
    async with self._lock:
        self._cache = new_cache
        self._dirty = False
    logger.info("UDP operator cache loaded: %d enabled operators", len(new_cache))
```

Note: Unlike token_cache which filters by token expiry, the operator cache only filters by `enabled == True`. Disabled operators must not receive UDP QSOs — disabling an operator must immediately (lazily, within one datagram) remove them from the routing table.

### _handle_datagram OPERATOR routing block

```python
# Insert after token resolution block, before the `if operator is None:` guard
# Source: derived from server.py lines 67-81 pattern
_OPERATOR_FIELD = "OPERATOR"
op_field_value = record.pop(_OPERATOR_FIELD, None)
if op_field_value is not None:
    from app.udp.operator_cache import operator_cache
    resolved_op_user = await operator_cache.resolve(op_field_value)
    if resolved_op_user is None:
        logger.warning(
            "UDP datagram src=%s:%s disposition=rejected reason=unknown-operator callsign=%s",
            addr[0], addr[1], op_field_value,
        )
        return
    operator = resolved_op_user.callsign
    user = resolved_op_user
```

### notify_refresh injection (admin/router.py example)

```python
# In create_user(), after await user.insert()
# Source: admin/router.py line 59
await user.insert()
from app.udp.operator_cache import operator_cache
operator_cache.notify_refresh()
```

---

## Docs Update Scope

### Files requiring changes

| File | Change |
|------|--------|
| `docs/admin-guide/deployment.md` | Update "Enabling the UDP Listener" section — `UDP_OPERATOR` is now Optional fallback, not required; add note about OPERATOR field routing |
| `docs/operator-guide/udp-adif.md` | Add "Multi-Operator Routing" section — explain OPERATOR field, show example datagram, explain fallback to UDP_OPERATOR |
| `docs/reference/environment-variables.md` | Update UDP_OPERATOR description — "optional fallback" instead of "required when UDP_ENABLED=true" |

### Exact current text to update

In `docs/admin-guide/deployment.md` line 61, the environment variables table says:
> `UDP_OPERATOR | No | (none) | Operator callsign assigned to QSOs received via UDP. Required when UDP_ENABLED=true.`

This must change to reflect optional-fallback status post-Phase 41.

In `docs/reference/environment-variables.md` line 41:
> `| UDP_OPERATOR | No | (none) | Operator callsign assigned to QSOs received via UDP. Required when UDP_ENABLED=true. |`

Same update needed.

The `docs/operator-guide/udp-adif.md` currently says:
> "`UDP_OPERATOR` must be set to a callsign that has an existing operator account in ollog."

This needs a new "Multi-Operator Routing" section explaining the OPERATOR field takes precedence and UDP_OPERATOR is the fallback.

### mkdocs build command (verified)

From `.planning/PROJECT.md` line 100 and `.planning/REQUIREMENTS.md` line 22:
```bash
uv run mkdocs build --strict
```

The `--strict` flag is the established pattern for this project. The command is run from the project root (same directory as `mkdocs.yml`). After the build, `site/` is committed to git as part of the phase deliverable.

**Confidence: HIGH** — confirmed in REQUIREMENTS.md DOC-02 and PROJECT.md historical record.

---

## Open Questions

1. **Datagram with both APP_OLLOG_TOKEN and OPERATOR field**
   - What we know: The ROADMAP routing order shows token resolution first, OPERATOR resolution second
   - What's unclear: Should APP_OLLOG_TOKEN win and OPERATOR be silently discarded? Or should they be cross-validated?
   - Recommendation: Token wins (it already sets operator+user), OPERATOR is popped and discarded. This is the conservative interpretation — no cross-validation is specified in requirements UDP-01 through UDP-06.

2. **Callsign stored on User.callsign vs User.station_callsign**
   - What we know: QSO attribution uses `operator` (a callsign string), set to `user.callsign` in all existing token-resolution code (server.py line 79)
   - What's unclear: Should `station_callsign` ever be used for routing instead of `callsign`?
   - Recommendation: Use `u.callsign` for both cache key and `operator` value, matching the existing `resolved_user.callsign` pattern in server.py line 79.

---

## Sources

### Primary (HIGH confidence)

- `app/udp/token_cache.py` — complete UDPTokenCache implementation (structure to mirror)
- `app/udp/server.py` — complete _handle_datagram and QSODatagramProtocol (routing injection point)
- `app/main.py` — lifespan block (startup wiring pattern, lines 34-56)
- `app/admin/router.py` — all operator mutation endpoints (REST API)
- `app/admin/ui_router.py` — all operator mutation endpoints (HTMX UI)
- `app/auth/models.py` — User document fields (callsign, enabled)
- `app/auth/service.py` — confirmed: no operator CRUD functions, only JWT/password utilities
- `app/adif/parser.py` — parse_adi() confirmed to preserve all field names as UPPERCASE keys
- `app/config.py` — confirmed udp_operator: str | None = None
- `docs/admin-guide/deployment.md` — current UDP documentation (lines to update identified)
- `docs/operator-guide/udp-adif.md` — current UDP operator guide (section to expand identified)
- `docs/reference/environment-variables.md` — current env var reference (UDP_OPERATOR description to update)
- `.planning/REQUIREMENTS.md` — DOC-02 confirms `uv run mkdocs build --strict`
- `.planning/PROJECT.md` — confirms mkdocs build command and site/ commit pattern

---

## Metadata

**Confidence breakdown:**
- operator_cache.py structure: HIGH — direct mirror of reviewed token_cache.py
- _handle_datagram injection: HIGH — routing slot is clearly visible in reviewed code
- notify_refresh injection sites: HIGH — both router files read in full; no service layer exists
- OPERATOR field parsing: HIGH — parse_adi() preserves all fields verbatim as uppercase keys
- mkdocs build command: HIGH — confirmed in two planning docs
- docs update scope: HIGH — exact line numbers identified in all three docs files

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable codebase, no fast-moving dependencies)
