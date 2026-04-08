# Phase 19: Deployment Guide — UDP Configuration - Research

**Researched:** 2026-04-08
**Domain:** Technical documentation — Markdown, Docker Compose
**Confidence:** HIGH

## Summary

This phase is a pure documentation task: update `docs/deployment.md` to include the four UDP-related environment variables and add a Docker Compose snippet showing how to enable the UDP listener. There is no code to write and no libraries to install.

All source-of-truth values were read directly from `app/config.py` and `docker-compose.yml`. The requirements document cited port 2237 as the default, but the actual default in `app/config.py` and `docker-compose.yml` is **2399**. The planner must use 2399.

The existing `docker-compose.yml` already maps `2399:2399/udp` and already contains inline comments explaining how to enable UDP. The documentation simply needs to surface this for operators in a readable, consistent form alongside the existing env var table.

**Primary recommendation:** Insert four rows into the existing Environment Variables table in `docs/deployment.md` and add a new "Enabling the UDP Listener" section with a minimal Docker Compose snippet.

---

## Confirmed Facts (HIGH confidence — read from source files)

### UDP env vars from `app/config.py`

| Python attribute | Env var name (uppercase) | Type | Default | Notes |
|-----------------|--------------------------|------|---------|-------|
| `udp_enabled` | `UDP_ENABLED` | bool | `false` | pydantic-settings maps bool False to the string `false` |
| `udp_port` | `UDP_PORT` | int | `2399` | NOT 2237 — requirements doc is wrong |
| `udp_bind_host` | `UDP_BIND_HOST` | str | `127.0.0.1` | Must be set to `0.0.0.0` inside Docker |
| `udp_operator` | `UDP_OPERATOR` | str | (none) | Required when UDP is enabled; sets the operator callsign |

### Existing env var table in `docs/deployment.md`

The table is at line 47–55, under the `## Environment Variables` heading. Columns are:

```
| Variable | Required | Default | Description |
```

The four UDP variables should be appended after the existing `ADMIN_CALLSIGN` row. They should use `No` for Required (none are required for the app to start; UDP is opt-in).

### Existing `docker-compose.yml` structure

The `api` service already contains:
- Port mapping: `"2399:2399/udp"` (line 23)
- Inline comment explaining UDP_BIND_HOST override and UDP_ENABLED activation (lines 32–33)

The compose snippet in the documentation should show the operator what to add to their own compose file or `.env` to enable UDP. It should not duplicate the full `docker-compose.yml` — a targeted snippet is sufficient.

---

## Architecture Patterns

### Where to insert in `docs/deployment.md`

1. **Env var table rows** — append after `ADMIN_CALLSIGN` row (currently line 55). Keep the same four-column format.

2. **New section** — add a `## Enabling the UDP Listener` section after the `## Bootstrap Admin Account` section (after line 71) and before `## Verification Steps`. This keeps the document flow: prerequisites → env vars → bootstrap → optional features → verification.

### Env var table rows to add

```markdown
| UDP_ENABLED | No | `false` | Set to `true` to start the UDP ADIF listener. |
| UDP_PORT | No | `2399` | UDP port the listener binds to. |
| UDP_BIND_HOST | No | `127.0.0.1` | Address the UDP socket binds to. Inside Docker, set to `0.0.0.0` so host traffic reaches the container. |
| UDP_OPERATOR | No | (none) | Operator callsign assigned to QSOs received via UDP. Required when `UDP_ENABLED=true`. |
```

### Docker Compose snippet to add

The snippet should show the minimal additions to the `api` service: the port mapping and the three env vars that need to be set. It does not need to show the full compose file.

```yaml
services:
  api:
    ports:
      - "2399:2399/udp"   # expose UDP listener port
    environment:
      - UDP_ENABLED=true
      - UDP_BIND_HOST=0.0.0.0
      - UDP_OPERATOR=N0CALL   # replace with your callsign
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Verifying env var names/defaults | Don't guess | Read `app/config.py` directly (already done) |
| Port number | Don't use 2237 from requirements | Use 2399 from `app/config.py` and `docker-compose.yml` |

---

## Common Pitfalls

### Pitfall 1: Wrong port number
**What goes wrong:** Requirements say 2237; code says 2399.
**Why it happens:** Requirements doc contains a stale or incorrect value.
**How to avoid:** Always use the value from `app/config.py` (`udp_port: int = 2399`). The docker-compose.yml also confirms 2399.
**Warning signs:** Any mention of port 2237 in the final doc is wrong.

### Pitfall 2: Missing UDP_BIND_HOST instruction for Docker
**What goes wrong:** Operator sets `UDP_ENABLED=true` but UDP never receives packets because the socket is bound to 127.0.0.1 inside the container.
**Why it happens:** The default `127.0.0.1` is correct for non-Docker use but blocks host-to-container UDP in Docker.
**How to avoid:** The env var table description for `UDP_BIND_HOST` must explicitly state the Docker override. The compose snippet must show `UDP_BIND_HOST=0.0.0.0`.

### Pitfall 3: Omitting UDP_OPERATOR from the snippet
**What goes wrong:** Operator enables UDP but QSOs arrive with no operator assigned, causing failures.
**Why it happens:** `UDP_OPERATOR` has no default and is effectively required when UDP is enabled.
**How to avoid:** Show `UDP_OPERATOR` in the compose snippet and note it is required when UDP is enabled.

---

## Exact File State Before Changes

### `docs/deployment.md` env var table (lines 47–55)

```markdown
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| SECRET_KEY | Yes | (none) | JWT signing key. ... |
| MONGODB_URI | No | `mongodb://mongodb:27017/?replicaSet=rs0` | ... |
| MONGODB_DB | No | `ollog` | Database name |
| JWT_EXPIRE_MINUTES | No | `60` | Token lifetime in minutes |
| ADMIN_USERNAME | No | (none) | Bootstrap admin username ... |
| ADMIN_PASSWORD | No | (none) | Bootstrap admin password ... |
| ADMIN_CALLSIGN | No | (none) | Bootstrap admin callsign ... |
```

Four rows are appended after `ADMIN_CALLSIGN`.

### `docker-compose.yml` api service ports (line 22–23)

```yaml
    ports:
      - "8000:8000"
      - "2399:2399/udp"  # UDP ADIF listener (UDP_ENABLED=true to activate)
```

The port mapping already exists. The documentation snippet is illustrative, not instructing the operator to modify their existing compose file — it shows what is already there and what env vars to set.

---

## Open Questions

1. **Section placement for "Enabling the UDP Listener"**
   - What we know: Current sections are Quick Start → Env Vars → Bootstrap Admin → Verification → Updating → MongoDB Replica Set.
   - What's unclear: Whether the new section should be before or after Verification Steps. "After Bootstrap Admin, before Verification" is logical since UDP is an optional feature to configure before verifying.
   - Recommendation: Place after `## Bootstrap Admin Account` section.

2. **Whether to mention UDP_PORT=2399 must match the docker-compose port mapping**
   - What we know: docker-compose.yml hardcodes `2399:2399/udp`.
   - What's unclear: If operator changes UDP_PORT, they also need to update the compose ports mapping.
   - Recommendation: Add a brief note in the description or snippet comment.

---

## Sources

### Primary (HIGH confidence)
- `/Users/royco/ollog/app/config.py` — all four UDP env var names, types, and defaults read directly
- `/Users/royco/ollog/docs/deployment.md` — existing table structure, section names, and line numbers read directly
- `/Users/royco/ollog/docker-compose.yml` — existing port mapping and inline comments read directly

---

## Metadata

**Confidence breakdown:**
- UDP env var names/types/defaults: HIGH — read from source file
- Correct port number (2399 not 2237): HIGH — confirmed in both config.py and docker-compose.yml
- Document insertion location: HIGH — existing structure read directly
- Docker Compose snippet content: HIGH — based on actual docker-compose.yml values

**Research date:** 2026-04-08
**Valid until:** Stable (no external dependencies; changes only if config.py is modified)
