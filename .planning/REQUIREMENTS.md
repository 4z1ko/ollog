# Requirements: ollog v1.7

**Defined:** 2026-04-09
**Core Value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss

## v1.7 Requirements

### Token Management

- [ ] **TOK-01**: Operator can create a named API token with a label (required) and optional expiry date from the Profile Settings page
- [ ] **TOK-02**: Plaintext token is shown exactly once immediately after creation — it cannot be retrieved again
- [ ] **TOK-03**: Operator can view their active tokens showing: label, creation date, expiry (if set), and token prefix (first 8 chars) for identification
- [ ] **TOK-04**: Operator can revoke any of their tokens individually

### REST API Auth

- [ ] **API-01**: All QSO REST API endpoints accept `X-API-Key: <token>` header as an alternative to JWT Bearer
- [ ] **API-02**: A valid `X-API-Key` resolves operator identity and enforces identical QSO isolation as JWT auth
- [ ] **API-03**: Invalid, expired, or missing credentials return HTTP 401

### UDP Auth

- [ ] **UDP-01**: UDP datagrams containing `APP_OLLOG_TOKEN` field are authenticated by token — operator identity resolved from token value
- [ ] **UDP-02**: UDP datagrams without `APP_OLLOG_TOKEN` fall back to `UDP_OPERATOR` config with no regression
- [ ] **UDP-03**: App maintains an in-memory HMAC-hash → callsign cache, refreshed when tokens are created or revoked

## Future Requirements

*(None identified for v1.8 at this stage)*

## Out of Scope

| Feature | Reason |
|---------|--------|
| Token scopes / permissions | All operations already operator-scoped; read/write scopes add UI complexity for zero security benefit |
| Token rotation / auto-refresh | Unattended rigs have no back-channel; named tokens that never expire (unless revoked) are the correct pattern |
| Admin token management | Admins manage operators, not their tokens — operator owns their own credentials |
| Query-param token (`?api_key=`) | URLs appear in logs and referrer headers; header-only enforces transport security |

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| HMAC-SHA256 for token hashing | Argon2 adds 200-500ms per request — unacceptable for API tokens validated on every call |
| Separate `api_tokens` Beanie collection | Avoids bloating every `User.find_one()` call; cleaner indexes and revocation queries |
| Per-datagram in-memory cache for UDP | Startup-pin delivers nothing `UDP_OPERATOR` doesn't already provide; cache gives per-operator token resolution with sub-ms lookup |
| `APP_OLLOG_TOKEN` ADIF field name | ADIF spec APP_ prefix for application-specific fields; field name is fixed, not parameterised by token label |
| `X-API-Key` header (not `Authorization: Bearer`) | Clean separation from JWT session auth; recognized convention for long-lived API credentials |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TOK-01 | — | Pending |
| TOK-02 | — | Pending |
| TOK-03 | — | Pending |
| TOK-04 | — | Pending |
| API-01 | — | Pending |
| API-02 | — | Pending |
| API-03 | — | Pending |
| UDP-01 | — | Pending |
| UDP-02 | — | Pending |
| UDP-03 | — | Pending |

**Coverage:**
- v1.7 requirements: 10 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 10 ⚠️

---
*Requirements defined: 2026-04-09*
*Last updated: 2026-04-09 after initial definition*
