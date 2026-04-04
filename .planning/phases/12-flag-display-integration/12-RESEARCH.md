# Phase 12: Flag Display Integration - Research

**Researched:** 2026-04-04
**Domain:** FastAPI/Jinja2 template injection, SVG flag assets, HTMX partial swaps, Python country lookup
**Confidence:** HIGH

---

## Summary

Phase 12 adds country flag icons to the QSO log table by (1) moving 271 SVG flag files to
the served static directory, (2) enriching the single view-dict injection point with flag
metadata, and (3) rendering a conditional `<img>` tag in `qso_row.html`. No JavaScript is
required and no third-party library needs to be added: `pycountry` (already a declared
dependency in `pyproject.toml`) provides human-readable country names for the `title`
tooltip attribute directly from the ISO alpha-2 code returned by `lookup_prefix()`.

The only infrastructure work is resolving the static-file path mismatch. The 271 SVG files
currently live at `app/static/flags/` but the `StaticFiles` mount in `app/main.py` serves
from `static/` (the root-level directory), so `/static/flags/*.svg` URLs return 404 today.
The fix is a `git mv app/static/flags static/flags` — one command, no code changes, no
Dockerfile changes (Dockerfile already copies `static/` to the image).

Because `_qso_to_view_dict()` is the single injection point consumed by all four template
render paths (log view, paginated partial, edit-row cancel, post-update), adding `flag_iso`
and `flag_country` there propagates automatically to every row render without touching any
route handler.

**Primary recommendation:** Move flags with `git mv`, enrich `_qso_to_view_dict()` with
two new keys, render a conditional `<img>` in `qso_row.html` only. Edit mode
(`qso_row_edit.html`) does not need the flag.

---

## Standard Stack

### Core (already in project)
| Component | Version/Location | Purpose | Notes |
|-----------|-----------------|---------|-------|
| `lookup_prefix()` | `app/callsign/prefixes.py` | ISO alpha-2 from callsign | Returns `str \| None`; already handles all edge cases |
| `pycountry` | `>=26.2.16` (in `pyproject.toml`) | Country name from ISO code | `pycountry.countries.get(alpha_2='US').name` |
| Flag SVGs | `app/static/flags/*.svg` (271 files) | Flag images | `viewBox="0 0 640 480"` — natural 4:3 ratio |
| `StaticFiles` mount | `app/main.py` line 115 | Serves `/static/*` from `static/` | Root `static/` dir currently empty except `.gitkeep` |
| Jinja2 | via FastAPI | Conditional rendering | `{% if qso.flag_iso %}` pattern |

### Supporting
| Component | Purpose | Notes |
|-----------|---------|-------|
| HTMX 2.0.4 | Partial swap of table rows | `<img>` tags survive swap; inline SVG does NOT |
| `git mv` | Relocate flag assets | Preserves git history; preferred over copy+delete |

### Alternatives Considered
| Instead of | Could Use | Why NOT |
|------------|-----------|---------|
| `git mv app/static/flags static/flags` | Change `StaticFiles` mount to `app/static` | Would break convention; root `static/` is the declared serving dir |
| `pycountry` for country name | Manual dict in `prefixes.py` | `pycountry` already installed; adding a second dict is redundant |
| `pycountry` for country name | Jinja2 filter | Adds complexity; injecting in Python is simpler and testable |
| `<img>` tag | Inline SVG | Confirmed broken with HTMX partial swap (htmx issue #2761) |
| `<img>` tag | CSS sprite / `flag-icon-css` class | No CDN dependency needed; direct SVG files already present |

---

## Architecture Patterns

### What changes and where

```
app/
  callsign/
    prefixes.py          # No change — lookup_prefix() already done
  qso/
    ui_router.py         # _qso_to_view_dict(): add flag_iso + flag_country
  static/
    flags/               # REMOVE this directory (files moved out)

static/
  .gitkeep               # Remove or keep — flags directory will exist
  flags/                 # NEW: git mv app/static/flags static/flags
    us.svg
    gb.svg
    ...271 files

templates/
  log/
    qso_row.html         # Add conditional <img> before CALL text
    qso_row_edit.html    # No change — edit mode does not show flag
    log_table.html       # No change
```

### Pattern 1: Injection at the view-dict level

**What:** Add `flag_iso` (str or None) and `flag_country` (str or None) to the dict
produced by `_qso_to_view_dict()`. All four template paths call this function so no route
handler needs to be touched.

**When to use:** Any time data derived from a model field is needed across all template
renders of a row — centralise in the dict builder, not in route handlers.

**Example (in `app/qso/ui_router.py`):**
```python
from app.callsign.prefixes import lookup_prefix
import pycountry

def _qso_to_view_dict(qso: QSO) -> dict:
    d: dict = {
        "id": str(qso.id),
        "CALL": qso.CALL,
        "BAND": qso.BAND or "",
        "MODE": qso.MODE or "",
        "qso_date_utc": qso.qso_date_utc,
    }
    extra = qso.model_extra or {}
    d["FREQ"] = extra.get("FREQ", "")
    d["RST_SENT"] = extra.get("RST_SENT", "")
    d["RST_RCVD"] = extra.get("RST_RCVD", "")
    d["QSO_DATE"] = extra.get("QSO_DATE", "")
    d["TIME_ON"] = extra.get("TIME_ON", "")

    # Flag enrichment
    iso = lookup_prefix(qso.CALL) if qso.CALL else None
    d["flag_iso"] = iso.lower() if iso else None
    country_obj = pycountry.countries.get(alpha_2=iso) if iso else None
    d["flag_country"] = country_obj.name if country_obj else (iso if iso else None)
    return d
```

**Important:** `lookup_prefix()` returns uppercase (e.g. "US"). Flag filenames are lowercase
("us.svg"). Must call `.lower()` before building the path.

**Kosovo (XK) edge case:** `pycountry.countries.get(alpha_2='XK')` returns `None` because
XK is a user-assigned code not in the ISO 3166-1 standard. The `xk.svg` flag file DOES
exist. The fallback `iso if iso else None` handles this: `flag_country` becomes "XK" and
the tooltip shows "XK" rather than a full country name — acceptable behaviour.

### Pattern 2: Conditional img in template

**What:** Render `<img>` only when `flag_iso` is present. Use `title` attribute for tooltip.
No JavaScript. No broken image risk.

**Example (in `templates/log/qso_row.html`):**
```html
<tr id="qso-{{ qso.id }}">
  <td>{{ qso.qso_date_utc.strftime('%Y-%m-%d %H:%M') if qso.qso_date_utc else '' }} UTC</td>
  <td>
    {% if qso.flag_iso %}
    <img src="/static/flags/{{ qso.flag_iso }}.svg"
         width="20" height="15"
         alt="{{ qso.flag_country or '' }}"
         title="{{ qso.flag_country or '' }}"
         style="vertical-align:middle;margin-right:4px;">
    {% endif %}
    {{ qso.CALL }}
  </td>
  ...
```

### Pattern 3: Static file relocation via git mv

**What:** Move the entire flags directory from `app/static/flags/` to `static/flags/` using
`git mv` so git tracks the move as a rename, not a delete+add.

```bash
git mv app/static/flags static/flags
```

**Result:** `/static/flags/us.svg` becomes a valid URL. The Dockerfile already copies
`static/` into the image so no Dockerfile changes are needed.

### Anti-Patterns to Avoid

- **Changing the `StaticFiles` mount path:** The mount is `directory="static"` which is
  correct. Moving the flags to meet the mount is simpler than moving the mount to chase
  the flags.
- **Inline SVG in templates:** Confirmed broken with HTMX outerHTML swaps (htmx issue
  #2761). The `<img src="...">` approach works correctly.
- **Calling `lookup_prefix()` in the template:** Jinja2 cannot import Python modules.
  The lookup must happen in `_qso_to_view_dict()`.
- **Adding `flag_iso` to the feed_row path:** `feed_row.html` is rendered by
  `app/feed/manager.py` via `templates.get_template("log/feed_row.html").render(ctx)` with
  a hand-built `ctx` dict that does NOT go through `_qso_to_view_dict()`. FLAG-01 and
  FLAG-02 only specify the log table. Do not add flag rendering to `feed_row.html` in this
  phase.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Country name from ISO code | Custom dict of 200+ country names | `pycountry.countries.get(alpha_2=iso).name` | Already installed; handles 249 countries with official names |
| Flag asset delivery | Convert SVGs to base64, embed in HTML | Serve from `static/flags/*.svg` | 271 files already present; `StaticFiles` handles caching headers |
| Broken-image prevention | onerror JS handler | Jinja2 `{% if qso.flag_iso %}` | Zero JS; server determines whether flag exists before rendering |

**Key insight:** The entire feature is a data enrichment in one Python function plus a
conditional img tag in one template. No new routes, no JavaScript, no new dependencies.

---

## Common Pitfalls

### Pitfall 1: Uppercase ISO code in flag filename
**What goes wrong:** `lookup_prefix()` returns uppercase "US". Flag file is `us.svg`.
`/static/flags/US.svg` returns 404 on case-sensitive filesystems (Linux/Docker).
**Why it happens:** `lookup_prefix()` stores codes as uppercase per ISO convention; flag
filenames follow the lowercase convention of the lipis/flag-icons library.
**How to avoid:** Always call `.lower()` in `_qso_to_view_dict()`:
`iso.lower() if iso else None`
**Warning signs:** Flags work on macOS dev (case-insensitive FS) but break in Docker.

### Pitfall 2: Kosovo (XK) returns None from pycountry
**What goes wrong:** `pycountry.countries.get(alpha_2='XK')` returns `None` because XK is
not in ISO 3166-1. Accessing `.name` on None raises `AttributeError`.
**Why it happens:** Kosovo's user-assigned code is not in the official ISO standard.
**How to avoid:** Guard with `country_obj.name if country_obj else (iso if iso else None)`.
The `xk.svg` file exists so the flag still displays; tooltip shows "XK".
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'name'` in logs.

### Pitfall 3: Flags served from wrong path until git mv
**What goes wrong:** `app/static/flags/*.svg` exists but the `StaticFiles` mount serves
from `static/` (root level), so URLs like `/static/flags/us.svg` return 404.
**Why it happens:** `app/static/` is the application's internal static folder convention,
but the FastAPI mount points at the root `static/` directory.
**How to avoid:** Run `git mv app/static/flags static/flags` before any template work so
you can verify URLs work locally before templating.
**Warning signs:** Browser DevTools shows 404 for all flag img requests.

### Pitfall 4: HTMX partial swap breaks inline SVG
**What goes wrong:** If SVG is inlined into the `<td>`, HTMX outerHTML swap strips or
corrupts it on pagination/edit/cancel operations.
**Why it happens:** Confirmed HTMX bug #2761 — inline SVG within partial swap targets is
not safe.
**How to avoid:** Use `<img src="/static/flags/...svg">` exclusively. Already verified
correct approach.
**Warning signs:** Flag disappears after clicking Edit then Cancel, or after pagination.

### Pitfall 5: `qso_result.html` path — fourth render path
**What goes wrong:** After submitting a new QSO, `qso_result.html` also renders `qso.CALL`.
**Why it happens:** `_qso_to_view_dict()` is called for all four paths including the post-
submit success result. Adding keys to the dict handles this automatically.
**How to avoid:** Verify `qso_result.html` to see if it renders CALL — if it does and shows
the flag, that's fine. If not, no action needed.

---

## Code Examples

### Verified: lookup_prefix() signature
```python
# Source: app/callsign/prefixes.py line 663
def lookup_prefix(callsign: str) -> str | None:
    """Resolve callsign to ISO 3166-1 alpha-2 country code, or None."""
```
Returns `None` for unresolvable callsigns, `/MM`, `/AM`, non-country ITU entities (4U, C7).
Returns uppercase two-letter code for all resolvable callsigns.

### Verified: pycountry API (from PyPI docs, MEDIUM confidence — not runnable in this env)
```python
import pycountry
country = pycountry.countries.get(alpha_2='DE')
# country.name => 'Germany'
# pycountry.countries.get(alpha_2='XK') => None  (Kosovo, user-assigned code)
```

### Verified: StaticFiles mount (app/main.py line 115)
```python
app.mount("/static", StaticFiles(directory="static"), name="static")
```
After `git mv app/static/flags static/flags`, URL `/static/flags/us.svg` resolves.

### Verified: Flag SVG viewBox (from actual files)
```
viewBox="0 0 640 480"   # natural 4:3 ratio (640÷480 = 1.333)
```
Recommended `<img>` dimensions: `width="20" height="15"` (20÷15 = 1.333).
Alternative: `width="24" height="18"`. Both preserve ratio; 20x15 is subtler in a table.

### Verified: All inject paths use _qso_to_view_dict()
```
/log/view (GET, full page)      → _qso_to_view_dict() → log.html → log_table.html → qso_row.html
/log/view (GET, HTMX partial)   → _qso_to_view_dict() → log_table.html → qso_row.html
/log/qsos/{id}/edit (GET)       → _qso_to_view_dict() → qso_row_edit.html
/log/qsos/{id} (GET, cancel)    → _qso_to_view_dict() → qso_row.html
/log/qsos/{id} (PATCH, save)    → _qso_to_view_dict() on updated QSO → qso_row.html
```
`feed_row.html` does NOT go through `_qso_to_view_dict()` — separate data path.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|-----------------|--------|
| CSS sprite sheets for flags | Individual SVG files per flag | SVGs scale losslessly; modern browsers handle 271 separate files fine |
| JS-rendered tooltips | HTML `title` attribute | Zero JS; native browser tooltip; meets FLAG-01 requirement |
| Inline SVG in HTML | `<img src="...svg">` | HTMX-safe; no swap corruption |

---

## Open Questions

1. **Should `qso_result.html` also display the flag?**
   - What we know: `qso_result.html` exists and renders after QSO submission. `_qso_to_view_dict()` will add `flag_iso` so the data is available.
   - What's unclear: Whether the template renders CALL in a way that would benefit from a flag icon (it may just show "QSO logged successfully").
   - Recommendation: Inspect `qso_result.html` during planning; if CALL is displayed inline, add the flag img there too. If it's a success banner only, skip.

2. **What CSS sizing: 20x15 or 24x18?**
   - What we know: `td` padding is `0.6rem 0.8rem`; table uses `font-size` inherited from body (system-ui). Natural SVG ratio is 4:3.
   - What's unclear: Exact rendered line-height without running the app.
   - Recommendation: Use `width="20" height="15"` — fits neatly alongside callsign text at typical body font sizes (16px base → 1rem = 16px, line height ~24px, 15px flag leaves 4-5px margin).

3. **`git mv` vs. copy-then-delete**
   - What we know: 271 files are git-tracked at `app/static/flags/`. `git mv app/static/flags static/flags` is a single atomic rename.
   - Recommendation: Use `git mv`. It preserves history and produces a cleaner diff than 271 deletions + 271 additions.

---

## Sources

### Primary (HIGH confidence)
- Direct file reads: `app/main.py`, `app/callsign/prefixes.py`, `app/qso/ui_router.py`, all template files — ground truth on codebase state
- Direct filesystem inspection: `ls app/static/flags/` (271 SVG files), `ls static/` (empty, `.gitkeep` only), `git ls-files` (both directories tracked)
- `head -1 app/static/flags/us.svg` — confirmed `viewBox="0 0 640 480"` (4:3 ratio)
- `pyproject.toml` — confirmed `pycountry>=26.2.16` already declared

### Secondary (MEDIUM confidence)
- [pycountry PyPI page](https://pypi.org/project/pycountry/) — API confirmed: `pycountry.countries.get(alpha_2='XX').name`
- [pycountry GitHub issue #100: Adding Kosovo](https://github.com/pycountry/pycountry/issues/100) — confirmed XK returns None from pycountry

### Tertiary (LOW confidence)
- [lipis/flag-icons GitHub](https://github.com/lipis/flag-icons) — flag library origin (SVG files consistent with this library's conventions)
- HTMX issue #2761 (inline SVG + outerHTML swap breakage) — referenced in phase additional_context as already verified

---

## Metadata

**Confidence breakdown:**
- Static file path fix: HIGH — verified by direct filesystem inspection and reading `app/main.py`
- `_qso_to_view_dict()` injection point: HIGH — verified by reading all four route handlers
- `pycountry` API: MEDIUM — cannot run `import pycountry` in this environment; API confirmed via PyPI docs
- Kosovo (XK) pycountry None: MEDIUM — confirmed via GitHub issue
- Flag sizing (20x15): MEDIUM — derived from SVG viewBox + typical browser defaults

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable stack; pycountry and HTMX APIs do not change rapidly)
