---
phase: 65
slug: responsive-favicon-integration
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-13
---

# Phase 65 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Browser to app static files | Public browser requests resolve committed assets under the existing `/static` mount. | Public static favicon bytes, no user data |
| Browser to guide static files | Public browser requests resolve committed guide output under `/guide`. | Public generated documentation and favicon bytes |
| Template source to rendered HTML | Shared Jinja base template emits fixed favicon metadata to authenticated and unauthenticated app pages. | Fixed literal HTML metadata, no user-controlled values |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-65-01 | Information Disclosure | Static asset serving | mitigate | Used existing `/static` and `/guide` mounts only; no broad `/favicon` source-folder mount was added. Verified `app/main.py` and `app/admin_main.py` contain no `app.mount("/favicon"`. | closed |
| T-65-02 | Injection | `templates/base.html` favicon metadata | mitigate | Added one fixed literal `<link rel="icon" href="/static/favicon/favicon.ico">`; no user-controlled template values, apple touch metadata, manifest links, or PNG variant links were introduced in app templates. | closed |
| T-65-03 | Tampering / Integrity | MkDocs guide favicon output | mitigate | Configured `mkdocs.yml` with `theme.favicon: assets/favicon.ico`, copied matching favicon bytes to docs and generated site asset paths, and verified generated guide pages reference `assets/favicon.ico` instead of the Material default favicon path. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-13 | 3 | 3 | 0 | Codex |

---

## Evidence

- `rg -n 'app\.mount\("/favicon' app/main.py app/admin_main.py` returned no matches.
- `templates/base.html` contains exactly one fixed app favicon link to `/static/favicon/favicon.ico`.
- `rg -n 'apple-touch-icon|site.webmanifest|favicon-16x16|favicon-32x32' templates` returned no matches.
- `rg -n '<head>|rel="icon"|favicon' templates/log templates/admin` returned no matches, confirming favicon metadata is inherited through the shared base template rather than duplicated in partials.
- `cmp -s favicon/favicon.ico static/favicon/favicon.ico`, `docs/assets/favicon.ico`, and `site/assets/favicon.ico` all passed.
- `site/index.html` and `site/operator-guide/index.html` reference `assets/favicon.ico` with no remaining `assets/images/favicon.png` references in generated site output.

## Residual Notes

- `uv run mkdocs build --strict` remains blocked in this shell because `uv` is not installed. This is a reproducibility/tooling limitation, not an open security threat: the committed guide output and source favicon assets were verified directly.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-13
