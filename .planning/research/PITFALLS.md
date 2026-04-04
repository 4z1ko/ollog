# Pitfalls Research

**Domain:** Ham radio QSO logbook — callsign entity lookup and country flag display (v1.2)
**Researched:** 2026-04-04
**Scope:** Pitfalls specific to adding ITU prefix lookup, ISO country mapping, and flag icon rendering to the existing ollog stack (FastAPI + Beanie/MongoDB + HTMX 2.x + Jinja2).
**Confidence note:** Findings draw from direct codebase inspection (`app/qso/ui_router.py`, `templates/log/qso_row.html`, `templates/log/log_table.html`), ITU prefix data research (WebSearch + ITU.int), pycountry behavior (WebSearch + GitHub issues), HTMX SVG rendering behavior (WebSearch + htmx GitHub issues), and training data. Confidence levels are assigned per-finding.

---

## How This File Is Organized

Pitfalls 1–11 are **new** — specific to adding callsign entity lookup and flag display in v1.2.
Pitfalls 12–32 are **carried forward** from v1.0 / v1.1 research and remain relevant to any continued work.

---

## Critical Pitfalls (v1.2 specific)

Mistakes that produce wrong entity resolutions, broken rendering, or silent data corruption.

---

### Pitfall 1: Range Comparison on Raw Strings Instead of Character-Position Logic

**What goes wrong:**
The ITU data format `WAA - WAZ,United States of America` implies that a range like `3DA–3DM` means "all callsigns whose prefix starts with 3D and whose third character falls between A and M inclusive." A naive implementation does lexicographic string comparison (`"3DA" <= prefix <= "3DZ"`) which breaks down as soon as the range boundary and the callsign have different lengths. For example, comparing a 4-character prefix extract like `"3DA0"` against the 3-character bound `"3DM"` will produce wrong results depending on collation.

**Why it happens:**
Python's `<=` operator on strings does lexicographic comparison by Unicode code point. `"3DA0" <= "3DM"` is `True` (correct), but `"3DN0" <= "3DM"` is `False` (correct), and edge cases like `"3DM9"` against the upper bound `"3DM"` are `True` (which may be wrong depending on interpretation). The real complexity comes when the range format uses 2-character tails (`AA–AZ`), 3-character tails (`3DA–3DM`), or mixed-length sub-ranges. A developer who tests only the happy path (matching clearly inside a range) never discovers the edge-case failures.

**How to avoid:**
Normalize the comparison: extract exactly N characters from the callsign's prefix (where N is the length of the range boundary), then compare. For `3DA–3DM`, extract the first 3 characters of the callsign before the structural digit (the number separating prefix from suffix in a typical amateur callsign). Apply the range test only on that extracted segment. Separately, use longest-prefix-match: if `3DA` and `3D` both have entries, `3DA` wins for callsign `3DA9XY`.

**Warning signs:**
- A callsign known to be in Eswatini (`3DA9RS`) resolves to Fiji, or vice versa.
- Any callsign whose prefix ends in a digit immediately before the range boundary letter is misclassified.
- Unit tests that only test clean 2-character prefix cases pass while 3-character sub-range cases are untested.

**Phase to address:** ITU prefix data seeding and resolver implementation (the first v1.2 phase).

**Confidence:** HIGH — based on direct analysis of the range format and Python string comparison semantics.

---

### Pitfall 2: Using Lexicographic String Sort to Resolve Overlapping Sub-Ranges (3DA–3DM vs 3DN–3DZ)

**What goes wrong:**
Both `3DA–3DM` (Eswatini) and `3DN–3DZ` (Fiji) share the common 2-character stem `3D`. A lookup that scans all ranges in insertion order and returns on first match will return whichever entry was inserted first, regardless of which range actually applies. The longer/more-specific range must always win — this is the longest-prefix-match principle.

**Why it happens:**
A developer builds a flat list of `(lower, upper, country)` tuples and iterates from the top. If `3D,Fiji` is stored as a catch-all and `3DA–3DM,Eswatini` is stored as a sub-range below it, calls to Eswatini are silently misidentified. The ITU data includes many of these sub-range overlaps and they are not a corner case — they are the rule for the 3D, 4U, and similar blocks.

**How to avoid:**
Structure the lookup as a trie or, more practically, sort candidate ranges by specificity (length of common prefix prefix, then range width) before matching. The correct rule: always match the most specific (longest matching prefix) range that contains the callsign prefix. Store ranges keyed by their common prefix characters so only plausible candidates are checked.

**Warning signs:**
- Eswatini callsigns (`3DA9RS`) resolve as Fiji.
- The data is stored as an ordered list without explicit priority or sorted by insertion order.

**Phase to address:** ITU prefix resolver design — must be settled before data seeding, not after.

**Confidence:** HIGH — 3DA/3DM vs 3DN/3DZ sub-range is a documented real-world example; the longest-prefix-match principle is standard for prefix-range lookups.

---

### Pitfall 3: Treating the Structural Digit as Part of the Prefix

**What goes wrong:**
An amateur callsign has the structure `[prefix][digit][suffix]` where the prefix is 1–3 letters (sometimes leading with a digit), the structural digit separates prefix from suffix, and the suffix is 1–4 letters. When extracting the "prefix" to look up in the ITU table, the structural digit must be excluded — the ITU table contains letter-only prefix blocks (`WAA–WAZ`, `3DA–3DM`). A lookup that includes the structural digit extracts `W1` from `W1AW` and finds no match in a table that stores `WAA–WAZ`.

**Why it happens:**
The "prefix" in the ITU table is defined as the characters up to but not including the structural digit, while in common ham radio parlance "prefix" sometimes refers to the `[letters][digit]` portion (e.g., "W1" is the prefix of `W1AW`). These two usages collide. Code that naively strips the last characters or looks for the first digit without understanding the two-meaning problem will build a wrong extraction.

**How to avoid:**
For ITU range lookup, extract only the leading alpha characters before the structural digit: `W` from `W1AW`, `3D` from `3DA9RS`, `4X` from `4X4DQ`. The structural digit and the suffix are irrelevant to the ITU range comparison. Use a regex like `^([A-Z0-9]{1,3}[A-Z])` (ITU prefix = up to 3 characters ending in a letter, preceding the structural digit) and strip the structural digit before the lookup. Note that `4X` starts with a digit followed by a letter — this is valid and the leading digit is part of the ITU prefix, not the structural digit.

**Warning signs:**
- `4X4DQ` (Israel) returns no match or matches the wrong country.
- `VK2ABC` (Australia) extracts `VK2` instead of `VK` and fails to match `VKA–VKZ`.

**Phase to address:** Prefix extraction utility — implement and test before data seeding.

**Confidence:** HIGH — ITU prefix structure and structural digit convention verified via WebSearch (Wikipedia: Amateur radio call signs, ARRL international call sign series).

---

### Pitfall 4: Portable and Operating Suffixes Passed to the Resolver Without Stripping

**What goes wrong:**
Callsigns logged as `W1AW/P`, `G3XYZ/MM`, `VK2ABC/QRP`, or `W1AW/KH6` are valid ADIF values. If the CALL field value is passed directly to the prefix resolver without stripping the portable suffix, the resolver either finds no match (because `W1AW/P` doesn't match any ITU block) or — worse — tries to resolve `/P` as a callsign and throws an error or returns a garbage entity.

Additionally, `W1AW/KH6` is a special case: the `/KH6` suffix indicates the station is operating from Hawaii, so the correct entity is the suffix, not the base callsign prefix. The ITU resolver must decide: is this a portable suffix (`/P`, `/MM`, `/QRP`) to strip, or a geographic modifier (`/KH6`, `/VK3`) that overrides the base entity?

**Why it happens:**
The QSO entry UI strips nothing — it stores the CALL exactly as logged. This is correct for ADIF fidelity. The prefix resolver that consumes the CALL must do its own normalization. Developers who test only clean callsigns without suffixes build a resolver that silently misbehaves on the majority of DX contest or portable operation logs.

**How to avoid:**
Before the prefix lookup, apply a two-step normalization:
1. If the CALL contains `/`, split on `/` and inspect each segment.
2. If any segment after the slash is a known operating suffix (`P`, `M`, `MM`, `AM`, `QRP`, `QRPP`, `A`, `B`), discard it and use the base callsign.
3. If the segment after the slash looks like a country prefix (2+ alpha characters or a geographic callsign block), use that segment as the callsign to resolve instead of the base.
4. After normalization, apply the structural-digit extraction from Pitfall 3.

This is the known-correct behavior for cty.dat-based resolvers (e.g., N1MM+, CQRLOG) and is the industry standard.

**Warning signs:**
- A `/P` or `/MM` suffix causes a resolver exception or returns `None`.
- `W1AW/KH6` resolves as the United States instead of Hawaii (if Hawaii is treated as a separate entity in your data).
- Log views with imported ADIF data (which frequently contains portable suffixes) show no flag for many rows.

**Phase to address:** Prefix extraction utility — must handle suffixes before any entity lookup.

**Confidence:** HIGH — operating suffix conventions are documented in ADIF spec and ham radio call sign standards (Wikipedia: Amateur radio call signs). The geographic-override rule for `/KH6`-style suffixes is well-established in DX logging software behavior (MEDIUM confidence — multiple community sources, not formally specified in ADIF).

---

### Pitfall 5: ITU Non-Country Entities Have No ISO 3166-1 Code — Lookup Must Gracefully Return None

**What goes wrong:**
Several ITU callsign allocations are assigned to international organizations, not sovereign states:
- `C7A–C7Z` → World Meteorological Organization (WMO)
- `4U1ITU` → International Telecommunication Union
- `4U1UN` → United Nations (New York)
- `HV` → Vatican City (has ISO code `VA`, but is a DXCC entity in its own right)

A lookup that resolves the ITU country name to ISO alpha-2 via pycountry will fail or return a wrong result for these entities. If the code raises an exception or returns a fallback value without null-guarding, the flag rendering code will attempt to display a flag for an organization (e.g., WMO), which either renders broken or shows the wrong country's flag.

**Why it happens:**
Developers test with the 200+ sovereign nation codes and never encounter `C7A`-range callsigns in testing. The first time a WMO callsign appears in a log (rare, but real — WMO operates weather observation stations), the resolver blows up at the ISO lookup step.

**How to avoid:**
The resolver must return a structured result: `{"country_name": str | None, "iso_alpha2": str | None}`. The `iso_alpha2` field is explicitly `None` for non-country entities — this is not an error condition. The flag rendering template must check `if qso.iso_alpha2` before attempting to render an `<img>` tag. No ISO code → no flag → no error.

Maintain a hardcoded override table for known non-country ITU allocations: `{"C7": None, "4U": None}`. These are never going to have ISO codes; treating them as lookup failures to be retried is wasteful and incorrect.

**Warning signs:**
- Any exception in the ISO lookup step for a callsign beginning with `C7` or `4U1`.
- A flag renders for an organization callsign (means a wrong ISO code was substituted).
- The fallback path for `iso_alpha2 = None` was never tested.

**Phase to address:** ISO country mapping layer — design the None path first, test it explicitly.

**Confidence:** HIGH — C7/WMO allocation confirmed via ITU and WebSearch. 4U1/UN/ITU allocations confirmed via WebSearch (eham.net, ITU.int). ISO 3166-1 explicitly covers sovereign states only.

---

### Pitfall 6: Country Name Normalization Fails on ITU Parenthetical Forms

**What goes wrong:**
The ITU data uses official UN-style country names, many of which include parenthetical descriptors: `Germany (Federal Republic of)`, `Korea (Republic of)`, `United Kingdom of Great Britain and Northern Ireland`. These names will not match pycountry's `.lookup()` directly. `pycountry.countries.lookup("Germany (Federal Republic of)")` raises `LookupError` — it expects `"Germany"` or `"Federal Republic of Germany"`.

The `search_fuzzy()` method is not a reliable substitute: it has documented failures where `search_fuzzy("Niger")` returns Nigeria, `search_fuzzy("Russia")` fails (must use "Russian Federation"), and the function returns all countries on empty input. Using it without verifying the top result is the correct country is unsafe.

**Why it happens:**
Developers see that `pycountry.countries.search_fuzzy("United States")` returns `US` and assume the library handles all their input formats. The ITU parenthetical forms are not tested because they don't appear in developer-written unit tests — they appear in production data from the ITU table.

**How to avoid:**
Build a static normalization lookup table keyed by exact ITU name strings, mapping to ISO alpha-2 codes. This table covers all ITU names that do not directly match pycountry's lookup. For names that do match pycountry after simple stripping of parentheticals (e.g., strip ` (Federal Republic of)`, ` (Republic of)`, ` (Democratic People's Republic of)`), apply the stripping before the pycountry call and verify the result. The override table should be the primary lookup; pycountry should be a fallback only for names not in the override table.

Do not rely on fuzzy matching in production path — it is non-deterministic in its error cases and produces plausible-but-wrong results silently.

**Warning signs:**
- `LookupError` from pycountry at runtime when processing ITU names from the table.
- Germany, Korea, Russia, or UK callsigns show no flag when the resolver reaches the ISO step.
- Unit tests only test `"United States"` and `"Canada"` without testing the actual ITU name strings.

**Phase to address:** ISO country name normalization — implement the override table before wiring up pycountry.

**Confidence:** HIGH — pycountry lookup behavior verified via WebSearch (PyPI, GitHub issues #126, #129, #242). ITU parenthetical name format confirmed via ITU table inspection.

---

### Pitfall 7: Inline SVG in HTMX-Swapped Partials Breaks Due to Namespace Handling

**What goes wrong:**
HTMX parses all content it receives as `text/html` with the HTML namespace (`http://www.w3.org/1999/xhtml`). SVG elements require the SVG namespace (`http://www.w3.org/2000/svg`). When HTMX swaps in a partial response that contains inline `<svg>` elements (e.g., an inline flag SVG), the SVG nodes are created in the HTML namespace and do not render correctly. The SVG appears in the DOM but is invisible or renders as a broken element.

This is a confirmed, open limitation in HTMX. The specific failure mode is that `<svg>` returned in a partial is transformed — `<image>` tags inside SVG become HTML `<img>` tags, and `<path>` elements do not render.

**Why it happens:**
The developer tests flag rendering on the full page load (where the browser parses the HTML document directly, preserving SVG namespace correctly) and it works. The partial swap path (HTMX request to `/log/view` returning `log_table.html`) is tested less thoroughly, and the namespace bug only manifests during the HTMX swap, not on initial load.

**How to avoid:**
Do not use inline SVG for flag icons in HTMX-swapped partials. Use `<img>` tags with a flag icon URL instead. The flag icon source can be:
- A self-hosted set of PNG/SVG files served from FastAPI's static files mount.
- A CDN URL (e.g., `https://flagcdn.com/w20/{iso_alpha2}.png` for 20px-wide flags).

The `<img>` tag approach is fully compatible with HTMX partial swaps because HTMX handles `<img>` correctly — it does not need to parse SVG namespace. The browser fetches the flag image independently after the swap.

**Warning signs:**
- Flags render on first page load but disappear after clicking pagination (Next/Previous page).
- Flags render on a sort click but show as broken images.
- Any inline `<svg>` element in `qso_row.html` or `log_table.html`.

**Phase to address:** Flag rendering template — establish the `<img>` approach before writing any template code.

**Confidence:** HIGH — HTMX SVG namespace limitation is a confirmed, documented issue in htmx GitHub (issue #2761) and htmx discussions (#1888). Direct inspection of the codebase confirms the paginated view uses HTMX partial swap (`HX-Request` header → return `log_table.html` only).

---

### Pitfall 8: Flag Images Requested Per Row Cause a Cascade of Image Requests on Pagination

**What goes wrong:**
The log table renders 50 rows per page (default `page_size=50`). If each row independently fetches a flag image from an external CDN (e.g., `https://flagcdn.com/w20/us.png`), a single page load triggers up to 50 simultaneous image requests to the CDN. On a self-hosted deployment with poor outbound connectivity, or if the CDN is rate-limiting, these requests stall and flags appear slowly or not at all. Each pagination click (HTMX swap) repeats this cascade.

**Why it happens:**
The developer tests with a few rows and a fast internet connection. The CDN requests are fast. The problem only manifests with a full page of 50 rows, slow connections, or rate limits. The issue is invisible in development and only surfaces in deployed environments.

**How to avoid:**
Option 1 (recommended for self-hosted): Serve flag icons from the local FastAPI static files directory. Copy the flag icon set once at deployment; no external request at page render time. This eliminates the CDN dependency entirely.

Option 2 (acceptable if CDN is reliable): Use `loading="lazy"` on flag `<img>` tags. The browser defers off-screen image loads, reducing initial cascade. For a 50-row table with uniform row heights, most rows may be off-screen. However, this does not help for print views or non-visual agents.

Option 3: Limit the unique flag set to the flags actually present in the current page, batch them into CSS background-image sprites, or use CSS `flag-icons` library via CDN (single CSS request covers all flags). This is more complex to integrate but optimal for scale.

The self-hosted static file approach (Option 1) is best for this project's self-hosted deployment model.

**Warning signs:**
- DevTools network panel shows 40–50 image requests on a single log view page load.
- Flag images appear with noticeable delay after table renders.
- Browser console shows CDN rate limit errors (HTTP 429).

**Phase to address:** Flag rendering infrastructure — decide the serving strategy before building the template.

**Confidence:** MEDIUM — cascade behavior is a known web performance pattern. The 50-row default is confirmed from codebase inspection (`page_size: int = Query(50, ...)`). CDN rate limiting specifics are environment-dependent (LOW confidence on specifics).

---

### Pitfall 9: `_qso_to_view_dict()` Does Not Include Resolver Output — Flag Data Never Reaches the Template

**What goes wrong:**
The existing `_qso_to_view_dict()` function in `ui_router.py` extracts only a fixed set of ADIF fields from the QSO document and returns a plain dict. When the flag feature is added, the country entity and ISO code must be added to this dict so Jinja2 templates can render them. If the developer adds flag rendering to `qso_row.html` without updating `_qso_to_view_dict()`, the template receives `qso.iso_alpha2 = undefined`, Jinja2 silently renders it as empty string, and no flag appears with no error.

**Why it happens:**
The template-to-dict pipeline is not obvious to a developer unfamiliar with the codebase. The template accesses `qso.CALL`, `qso.BAND`, etc. — these appear to come directly from the Beanie document. In fact, they come from the `_qso_to_view_dict()` dict. Adding a field to the template without adding it to the dict is an easy oversight.

**How to avoid:**
The resolver call must happen inside `_qso_to_view_dict()` (or in the comprehension that calls it), and the result must be written into the dict before the template renders. The call site is:
```python
qsos = [_qso_to_view_dict(q) for q in qsos_raw]
```
The `iso_alpha2` and `country_name` keys must be present in every dict returned by this function — `None` if unresolved, a string if resolved. Do not add them to `qso_row.html` as template lookups of `qso.model_extra` because model_extra is not passed through to the view dict.

**Warning signs:**
- Template renders `qso.iso_alpha2` but no flags appear and no error is raised.
- Adding `{{ qso.iso_alpha2 }}` to the template renders an empty string for all rows.
- The resolver was implemented but never wired into `_qso_to_view_dict()`.

**Phase to address:** Flag rendering integration — the first task when adding flag rendering to the view.

**Confidence:** HIGH — based on direct code inspection of `_qso_to_view_dict()` and the `qsos = [_qso_to_view_dict(q) for q in qsos_raw]` pattern in `log_view()`.

---

### Pitfall 10: Resolver Called Per-Row on Every Page Request — N+1 Lookup Pattern

**What goes wrong:**
The prefix resolver is called once per QSO row in `_qso_to_view_dict()` during every page request and every pagination HTMX swap. If the resolver hits MongoDB on each call (e.g., `await PrefixRange.find_one({"prefix_start": {"$lte": prefix}, ...})`), a page of 50 QSOs generates 50 MongoDB queries per page load. At 50 rows × average 10ms per query, a single page load takes 500ms just for entity lookups — before any other work.

**Why it happens:**
MongoDB queries are async and fast in isolation. The developer adds `await PrefixRange.find_one(...)` in the view dict builder and it works fine in development with a few rows. Under load or with a full log, the cumulative latency is unacceptable.

**How to avoid:**
Cache the full prefix range table in memory at application startup. The ITU prefix range table has fewer than 800 entries and changes only when the ITU updates its allocations (infrequently). Load the entire table into a Python dict or trie at startup (`@asynccontextmanager` lifespan event in FastAPI) and use in-memory lookup — no database round-trip per row. The lookup becomes microseconds, not milliseconds.

If caching is deferred (MVP tradeoff), at minimum batch the unique callsign prefixes from the current page and perform a single `$in` query rather than N individual queries.

**Warning signs:**
- Log view is noticeably slow for pages with many rows.
- MongoDB slow query log shows many small queries fired in rapid succession.
- Application profiling shows the log view endpoint spending most of its time in MongoDB.

**Phase to address:** Prefix resolver implementation — design for in-memory lookup from the start.

**Confidence:** HIGH — N+1 database query is a universally recognized anti-pattern. The 50-row default is confirmed. ITU table size is well-known (< 1,000 entries).

---

### Pitfall 11: Callsign With No Matching Prefix Causes Template Rendering Error if Fallback Is Absent

**What goes wrong:**
A callsign in the log cannot be resolved to any ITU prefix (special event calls like `W1AW/ARRL`, contest exchanges, or genuinely unmatched prefixes). The resolver returns `None` for `iso_alpha2`. If the Jinja2 template renders `<img src="/flags/{{ qso.iso_alpha2 }}.svg">` without checking for `None`, the resulting `<img src="/flags/None.svg">` generates an HTTP 404 request for every unresolved row and renders a broken image icon in every such row.

**Why it happens:**
The developer writes the template for the happy path and adds the null check later — or forgets it. Jinja2 does not raise an error for `None`; it renders `"None"` as a string.

**How to avoid:**
The template must guard: `{% if qso.iso_alpha2 %}<img src="...">{% endif %}`. No fallback image, no placeholder — simply no element. A broken image icon is more visually disruptive than a blank cell. This is stated as a v1.2 explicit requirement in the project spec: "Graceful fallback when no prefix match found (no flag shown, no error)."

Also guard the resolver side: the resolver must return `None` (not raise an exception) for any callsign that has no matching prefix. Any exception in the resolver path must be caught at the `_qso_to_view_dict()` level and result in `iso_alpha2 = None`, not a 500 error.

**Warning signs:**
- Network panel shows requests to `/flags/None.svg` with 404 responses.
- Rows with unrecognized callsigns show a broken image icon instead of being blank.
- Any unhandled exception in the prefix resolver causes the entire log view to fail.

**Phase to address:** Flag rendering template and prefix resolver — implement and test the None path explicitly before the happy path.

**Confidence:** HIGH — Jinja2 renders `None` as the string `"None"` is a well-known behavior. The guard pattern is standard and the project spec explicitly requires graceful fallback.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use pycountry `search_fuzzy()` without override table | No need to build/maintain mapping table | Silently wrong results for ITU parenthetical names, non-deterministic failures | Never in production path |
| External CDN for flag images | No file management, always up-to-date | CDN rate limits, outbound network dependency, CDN unavailability breaks flags for offline deployments | Only if CDN uptime guarantee matches deployment requirements |
| Per-row synchronous DB lookup for prefix resolver | Simple implementation | N+1 query cascade, slow log view at scale | MVP only if page size is very small (< 5 rows); not acceptable at 50/page default |
| Flat list scan of prefix ranges without longest-match | Easy to implement and reason about | Misclassifies sub-range callsigns (Eswatini/Fiji, etc.) | Never — correctness bug, not a performance bug |
| Store resolved entity in the QSO document | Avoids runtime resolver call | Data becomes stale when ITU updates allocations; inflates QSO documents with display-layer data | Never — entity resolution is display-only per v1.2 spec |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| pycountry ISO lookup | Call `lookup()` directly with raw ITU name string | Strip parentheticals and build an override table; use pycountry as fallback only |
| flagcdn.com CDN | Embed CDN URL directly in template, assume always available | Self-host flag PNGs in FastAPI static directory; no runtime CDN dependency |
| HTMX partial swap + flag rendering | Use inline `<svg>` in `qso_row.html` | Use `<img>` tag only; SVG namespace breaks on HTMX swap (confirmed htmx issue #2761) |
| FastAPI `StaticFiles` mount | Forget to mount `/static` for flag images | Add `app.mount("/static", StaticFiles(directory="static"), name="static")` in `main.py` — verify it exists |
| ITU prefix range table in MongoDB | Load and query at runtime per row | Load into memory at startup lifespan event; lookup is pure in-memory |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| N+1 prefix resolver queries | Log view response time proportional to page size | In-memory prefix table loaded at startup | 10+ rows in development; noticeable at default 50/page |
| 50 flag image requests per page | Slow initial render; stall on slow connections | Self-host flag files; use `loading="lazy"` | Any deployment with external CDN and > 20 rows |
| Full prefix table scan per callsign | Resolver latency > 1ms per row | Pre-sort ranges by specificity; use dict keyed by prefix | Acceptable for < 100 rows; unacceptable at 500+ rows per page |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Serving flag images from external CDN with user-supplied ISO code in URL | XSS if `iso_alpha2` is not validated and inserted into a CDN URL template | Validate that `iso_alpha2` matches `^[a-z]{2}$` before using in any URL construction |
| Storing resolved entity in QSO document via PATCH | Operator could inject arbitrary `country_name` values into their QSO records | Entity resolution is display-only; never write resolver output back to QSO documents |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Flag renders for ITU organization callsigns (wrong flag) | Confusing — WMO callsign shows flag of an unrelated country | Return `None` for non-country entities; show no flag |
| Broken image icon for unresolved callsigns | Visual noise; looks like a bug | Guard with `{% if qso.iso_alpha2 %}` — show nothing for unresolved |
| Flag too large relative to callsign text | Disrupts table layout; row height increases | Use 16×11px or 20px-wide flags; test with actual table layout |
| Flag tooltip missing country name | Operator must guess which country the flag represents | Add `title="{{ qso.country_name }}"` and `alt="{{ qso.country_name }}"` to all flag `<img>` tags |

---

## "Looks Done But Isn't" Checklist

- [ ] **Prefix resolver:** Works on clean callsigns — verify it also handles `/P`, `/MM`, `/QRP` suffixes and geographic `/KH6`-style overrides.
- [ ] **ISO mapping:** Works on `"United States"` — verify it also handles `"Germany (Federal Republic of)"`, `"Korea (Republic of)"`, `"United Kingdom of Great Britain and Northern Ireland"`.
- [ ] **Non-country entities:** Resolver returns `None` for `C7A` (WMO) and `4U1ITU` — verify no exception is raised and no wrong flag is shown.
- [ ] **HTMX pagination:** Flags render on page 1 — verify they also render after clicking Next (HTMX partial swap path, not full page load).
- [ ] **Null guard in template:** `{% if qso.iso_alpha2 %}` is present — verify that rows with unmatched callsigns render a blank flag cell, not a broken image or "None" text.
- [ ] **`_qso_to_view_dict()` updated:** Resolver is called and `iso_alpha2`/`country_name` keys are present in the returned dict — verify by inspecting the dict, not just the rendered HTML.
- [ ] **In-memory lookup:** Prefix table is loaded at startup — verify it is not re-queried per row by checking MongoDB query counts in a test with 50 rows.
- [ ] **Sub-range correctness:** `3DA9RS` resolves to Eswatini (not Fiji), `3DN1XYZ` resolves to Fiji (not Eswatini) — both must be tested explicitly.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong sub-range resolution (Pitfall 2) | LOW | Fix sort order / longest-match logic in resolver; no data migration needed (flags are display-only) |
| Inline SVG breaks on HTMX swap (Pitfall 7) | LOW | Replace `<svg>` with `<img>` in template; no backend changes |
| N+1 query cascade (Pitfall 10) | MEDIUM | Refactor resolver to in-memory; requires lifespan event and startup load |
| ISO name normalization wrong (Pitfall 6) | LOW | Add entries to override table; redeploy; no data migration |
| Flag images missing from static dir | LOW | Copy flag asset set to static directory; restart server |
| `_qso_to_view_dict()` missing keys (Pitfall 9) | LOW | Add resolver call and dict keys; template immediately starts working |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Range comparison logic (Pitfall 1) | Phase 11: Prefix range data model and resolver | Unit test: `3DA9RS` → Eswatini, `3DN1XYZ` → Fiji, boundary callsigns at both ends of each range |
| Sub-range longest-match (Pitfall 2) | Phase 11: Prefix range data model and resolver | Unit test: both sides of 3D split; verify specificity ordering |
| Structural digit extraction (Pitfall 3) | Phase 11: Prefix extraction utility | Unit test: `4X4DQ` → `4X`, `W1AW` → `W`, `VK2ABC` → `VK` |
| Portable suffix handling (Pitfall 4) | Phase 11: Prefix extraction utility | Unit test: `W1AW/P` → same as `W1AW`; `W1AW/KH6` → KH6 entity |
| Non-country entities (Pitfall 5) | Phase 11: ISO mapping layer | Unit test: `C7A1XY` → `iso_alpha2 = None`; `4U1ITU` → `iso_alpha2 = None` |
| ITU name normalization (Pitfall 6) | Phase 11: ISO mapping layer | Unit test: all ITU parenthetical name forms present in the actual data file |
| Inline SVG / HTMX namespace (Pitfall 7) | Phase 12: Flag rendering template | Manual test: paginate the log view; verify flags render on every page transition |
| CDN cascade (Pitfall 8) | Phase 12: Flag rendering infrastructure | Network panel: count image requests on page load with 50-row page |
| `_qso_to_view_dict()` not updated (Pitfall 9) | Phase 12: Flag rendering integration | Unit test: `_qso_to_view_dict()` returns dict with `iso_alpha2` key for any QSO |
| N+1 resolver queries (Pitfall 10) | Phase 11: Resolver design | Test: log view with 50 rows generates 0 prefix-range MongoDB queries (in-memory path) |
| Null guard absent (Pitfall 11) | Phase 12: Flag rendering template | Unit test: row with `iso_alpha2 = None` renders no `<img>` tag |

---

## Sources

- Direct codebase inspection: `app/qso/ui_router.py`, `templates/log/log_table.html`, `templates/log/qso_row.html`
- ITU Table of International Call Sign Series: https://www.itu.int/en/ITU-R/terrestrial/fmd/Pages/call_sign_series.aspx
- ITU prefix — Wikipedia: https://en.wikipedia.org/wiki/ITU_prefix
- Amateur radio call signs — Wikipedia: https://en.wikipedia.org/wiki/Amateur_radio_call_signs
- 3DA/3DM (Eswatini) vs 3DN/3DZ (Fiji) sub-range: confirmed via WebSearch results and ITU table PDF
- 4U1 callsigns — United Nations and ITU: https://www.eham.net/article/23104 (MEDIUM confidence); https://www.itu.int/hub/2022/06/4u1itu-ham-radio-amateur-station-60-years/ (HIGH confidence)
- C7A–C7Z / World Meteorological Organization: https://en.wikipedia.org/wiki/World_Meteorological_Organization and ITU table
- pycountry PyPI: https://pypi.org/project/pycountry/ (HIGH confidence)
- pycountry `search_fuzzy` failure cases: https://github.com/pycountry/pycountry/issues/126 (England), https://github.com/pycountry/pycountry/issues/129 (Russia), https://github.com/pycountry/pycountry/issues/242 (Czechoslovakia) (HIGH confidence — confirmed GitHub issues)
- ISO 3166-1 — Wikipedia: https://en.wikipedia.org/wiki/ISO_3166-1
- HTMX SVG namespace limitation (issue #2761): https://github.com/bigskysoftware/htmx/issues/2761 (HIGH confidence — confirmed GitHub issue)
- HTMX SVG discussion (#1888): https://github.com/bigskysoftware/htmx/discussions/1888
- flag-icons (lipis): https://github.com/lipis/flag-icons and https://flagicons.lipis.dev/
- flagcdn.com API: https://flagpedia.net/download/api
- SVG icon stress test (external img vs inline): https://cloudfour.com/thinks/svg-icon-stress-test/

---

## Carried Forward: Critical Pitfalls (v1.0/v1.1 — still relevant)

---

### Pitfall 12: Profile Endpoint Returns Another Operator's Data (Isolation Leak)

**What goes wrong:** A `GET /api/profile` endpoint resolves operator identity from a query param, path param, or request body instead of the JWT-injected callsign.

**Prevention:** Profile GET and PUT/PATCH routes MUST use `operator: str = Depends(get_current_operator_callsign)` as the sole source of the operator key. Add a cross-operator profile test.

**Phase to address:** Any new API route touching operator-scoped data.

**Confidence:** HIGH

---

### Pitfall 13: ADIF Field Length Is Byte Count, Not Character Count

**What goes wrong:** `len(str)` in Python counts Unicode code points, not UTF-8 bytes. ADIF tag length N is byte length.

**Prevention:** Always use `len(value.encode('utf-8'))` when writing ADIF tags.

**Phase to address:** Any ADIF serializer change.

**Confidence:** HIGH

---

### Pitfall 14: ADIF MY_* Field Names Must Match the Spec Exactly

**What goes wrong:** Storing profile fields with Python-friendly names and mapping incorrectly on export produces non-standard ADIF field names.

**Prevention:** Store using exact ADIF 3.1.7 uppercase field names. Verify against https://adif.org/317/ADIF_317.htm.

**Phase to address:** Any profile or QSO export change.

**Confidence:** HIGH

---

### Pitfall 15: QSO Auto-Stamp When Profile Does Not Exist

**What goes wrong:** Profile lookup returns `None`; auto-stamp logic crashes or writes `OPERATOR: null` or `OPERATOR: "None"` to the QSO.

**Prevention:** Guard all profile lookups for `None`; if profile is absent, omit the stamp entirely.

**Phase to address:** Any change to QSO creation path.

**Confidence:** HIGH

---

### Pitfall 16: Maidenhead-to-Lat/Lon Returns SW Corner, Not Center

**What goes wrong:** `maidenhead.to_location(grid)` default returns SW corner, not center. Introduces up to 80 km systematic error.

**Prevention:** Always call `maidenhead.to_location(grid, center=True)`.

**Phase to address:** Any grid/location conversion work.

**Confidence:** HIGH

---

### Pitfall 17: Lat/Lon Precision and ADIF Location Format

**What goes wrong:** ADIF defines `MY_LAT`/`MY_LON` as `XDDD MM.MMM` strings, not decimal degrees. Storing decimal degrees as-is is spec non-compliant for export.

**Prevention:** Store as decimal float internally; convert to ADIF location format on export.

**Phase to address:** Profile ADIF export.

**Confidence:** MEDIUM

---

*Pitfalls research for: ollog v1.2 — callsign entity lookup and country flag display*
*Researched: 2026-04-04*
