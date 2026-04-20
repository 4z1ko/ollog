# Feature Research

**Domain:** Sortable log table columns + entry timestamp for a server-rendered HTMX ham radio logbook
**Milestone:** v2.5 QSO Sorting & Entry Timestamp
**Researched:** 2026-04-20
**Confidence:** HIGH — grounded in direct codebase inspection plus verified UX research

---

## Current State Snapshot

The existing `log_table.html` already implements sortable column headers for three columns:

| Column | Sort key | Status |
|--------|----------|--------|
| Date / Time UTC | `qso_date_utc` | Already sortable (asc/desc toggle) |
| Callsign | `CALL` | Already sortable |
| Band | `BAND` | Already sortable |
| Mode | `MODE` | Header exists but not sortable |
| Freq (MHz) | `FREQ` | Header exists but not sortable |
| RST S/R | (composite) | Header exists, not applicable |
| Actions | (buttons) | Not applicable |

Default sort: `-qso_date_utc` (most recent first).

The `auto-refresh-ok` sentinel in `log_table.html` already gates SSE auto-refresh on `sort == '-qso_date_utc'`, so any new sort value (including `_created_at`) automatically suppresses SSE auto-refresh with no additional logic.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Visual sort indicator on active column | Every sortable table shows which column is sorted and in which direction | LOW | Already done for date/call/band using filled chevron SVGs. Must be extended to MODE. |
| Clickable header triggers sort | Standard interaction — clicking a column header sorts by that column | LOW | Already implemented via `hx-get` on `<a>` wrappers in `<th>`. Pattern is established. |
| Sort state preserved through pagination | Page 2 must remain sorted the same way | LOW | Already works: `sort` param threaded through all pagination `hx-get` URLs in `log_table.html`. |
| Sort state preserved through filter changes | Applying a band filter must not reset the sort | LOW | Already works: filter form has `<input type="hidden" name="sort" value="{{ sort }}">` in `log.html`. |
| Default sort is most recent QSO first | Ham operators always want chronological reverse order by default | NONE | Already `-qso_date_utc`. No change needed. |
| `_created_at` field auto-set on all insert paths | System timestamp recording when the record entered the database; user must never set it | LOW | New `Optional[datetime]` field on `QSO` Beanie document with `default_factory=lambda: datetime.now(timezone.utc)`. Beanie sets it on `.insert()` — no change to `build_qso_dict()` required. |
| `_created_at` invisible in table display | It is system metadata, not an ADIF field that belongs in the log view | LOW | Do not add it as a `<td>` in `qso_row.html`. |
| Dedicated sort icon for `_created_at` in header | Users need a way to sort by insertion order without an explicit table column | MEDIUM | A small clock or stack icon in the `<thead>` row. Not a `<th>` with a data column below it — instead placed at the end of the existing header row as a standalone sortable icon. Cycles `-_created_at` (newest insert first) ↔ `_created_at` (oldest insert first). |
| `asc → desc` cycle on clicking the same column | Users expect a second click on the active column to reverse direction | LOW | Already implemented for date/call/band. Pattern: `if sort == '-FIELD'` then go to `FIELD`; else go to `-FIELD`. Extend to MODE. |
| Sort state visible in URL | Deep-linkable; browser back button returns to previous sort | LOW | Already works via `hx-push-url="true"` on all sort-triggering links. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Hollow/outline double-chevron on sortable-but-unsorted columns | Makes it immediately obvious which columns can be sorted, reducing discovery friction. W3C ARIA Authoring Practices recommend a visually distinct unsorted icon (e.g. outline double-chevron) vs the active sort icon. | LOW | Apply to all sortable columns (date, call, band, mode, `_created_at` icon) when they are not the active sort. Currently the template shows nothing on unsorted columns — adding the hollow icon is a small, impactful improvement. Requires adding one SVG variant to existing `{% if sort == ... %}` blocks. |
| `aria-sort` attribute on active `<th>` | WCAG 2.2 AA accessibility compliance; European Accessibility Act 2025 mandates this for EU-served digital products. Screen readers announce sort state. | LOW | `aria-sort="ascending"` or `aria-sort="descending"` on the active `<th>`. Omit attribute entirely on unsorted columns (W3C recommendation: do not use `aria-sort="none"` as it generates verbose screen reader output). |
| MODE column sortable | Third most-useful sort for ham operators (after date and callsign). Lets operators review all FT8, all CW, all SSB QSOs grouped together. | LOW | Identical pattern to CALL/BAND. One additional `<a hx-get="...">` wrapper in the MODE `<th>`. MongoDB string sort on `MODE` is semantically correct (FT8, CW, SSB, etc. are comparable strings). |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Three-state sort cycle (asc → desc → reset-to-default) | Some table libraries (TanStack, Tabulator) support this tristate toggle | For a personal logbook, "reset to default" is already handled by the existing Clear button in the filter bar. Third state adds URL parameter ambiguity (must distinguish "no sort specified" vs "sort=-qso_date_utc") and triple-click muscle memory is unusual. | Keep two-state toggle (asc ↔ desc). Clear button already resets everything to default. |
| Multi-column sort (shift+click secondary sort) | Power users in spreadsheet tools expect secondary sort keys | Significant URL parameter complexity, server-side sort complexity in `get_qso_page()`, and confusing UX without persistent sort-key indicators. Single-column sort covers all practical ham log review needs. | Single-column sort only. |
| Client-side sort (JavaScript, no server round-trip) | Feels faster for small datasets | Breaks for large logs (500+ QSOs), breaks pagination, breaks filter interaction, creates a second source of truth separate from MongoDB's sort. This app is server-rendered HTMX — client-side sort fights the architecture fundamentally. | Server sort via `get_qso_page(sort_by=...)` using Beanie's `.sort()`. Already works. |
| Freq (MHz) sortable | FREQ is a visible column; users might expect it | `FREQ` is stored in `model_extra` as a string (ADIF verbatim: "14.074", "144.200"). MongoDB string sort is lexicographic, not numeric: "9.0" sorts after "144.200". Correct sort requires either a `FREQ_numeric: float` derived field stored on insert, or an aggregation pipeline — significant complexity for low operational value. Band filter already groups by frequency range. | Not sortable. Users who want frequency-oriented views use the Band filter. |
| RST S/R sortable | RST is a visible column | RST values are signal reports (e.g. "599", "59"). No ham operator has ever needed to review their log sorted by signal quality. Zero practical value. | Not sortable. RST column keeps its current plain `<th>RST S / R</th>`. |
| Actions column sortable | N/A | Actions column contains edit/delete buttons, not data. Conceptually nonsensical. | Remains a plain non-interactive header. |
| Sticky column header (frozen `<thead>` on scroll) | Long log tables require scrolling; sticky header makes column context visible | Log table has no horizontal scroll. Vertical scroll is handled by page-level browser scroll. Adding `position: sticky` to `<thead>` adds CSS complexity with minimal benefit at personal-log scale (50 rows per page). | Pagination at 50 rows per page keeps tables short. Not needed. |
| Sort preference persisted in localStorage | Sort choice survives a hard page reload | Adds JS complexity and creates confusion when URLs (bookmarks, shared links) override localStorage. URL-based sort state is already persistent via `hx-push-url="true"` and survives hard reloads. | URL state is sufficient and shareable. |

---

## Feature Dependencies

```
_created_at field on QSO Beanie Document
    └──required by──> _created_at sort icon in log_table.html <thead>
                          └──requires──> sort_by='_created_at' handled in get_qso_page()
                                             └──requires──> MongoDB index on (_operator, _created_at)

Existing sort pattern (CALL, BAND, qso_date_utc in log_table.html)
    └──extended by──> MODE column sort (identical pattern, zero new dependencies)
                      └──requires nothing new beyond the template change

auto-refresh-ok sentinel in log_table.html (existing v1.6 feature)
    └──automatically gates──> any non-default sort including _created_at
       (sentinel renders only when sort == '-qso_date_utc'; all other sort values
        already suppress SSE auto-refresh with zero new logic)
```

### Dependency Notes

- **`_created_at` Beanie field must be declared before anything else:** The `QSO` document needs `_created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))`. Beanie respects `default_factory` on `.insert()`. No migration needed for existing documents — `Optional` with `None` default means old documents remain valid; sorting by `_created_at` on old documents puts `None`-valued QSOs at the low end (MongoDB treats `null` as less than all values), which is acceptable legacy-QSOs-first behavior.
- **ADIF import path behavior:** `import_qsos_from_bytes()` calls `build_qso_dict()` then `QSO(**qso_dict).insert()`. The `_created_at` field is NOT set in `build_qso_dict()` — it is set by the Beanie model's `default_factory` at document construction time. This is correct: imported historical QSOs get a `_created_at` reflecting when they were imported into this system, not the original QSO date. Do not set `_created_at` inside `build_qso_dict()`.
- **MongoDB index:** Add `(_operator, _created_at)` compound index to `QSO.Settings.indexes`. Without it, sorting by `_created_at` on large logs requires a collection scan. Low risk for personal-scale deployments, but adding the index is the correct approach.
- **MODE sort has zero backend dependencies:** `MODE` is a declared field on `QSO` (not in `model_extra`), so Beanie's `.sort('MODE')` works without any model or service changes. The only change is in `log_table.html`.
- **`_created_at` must be excluded from ADIF export:** It is an internal system field, not an ADIF field. The existing `_qso_to_adif_dict()` in `app/adif/router.py` explicitly maps known fields — `_created_at` will not be in the output unless explicitly added. Verify this to avoid ADIF spec violations.

---

## MVP Definition (for this milestone, v2.5)

### Launch With (required to ship v2.5)

- [ ] `_created_at: Optional[datetime]` field on `QSO` Beanie document with `default_factory`
- [ ] MongoDB compound index on `(_operator, _created_at)` in `QSO.Settings.indexes`
- [ ] `get_qso_page()` handles `sort_by='_created_at'` and `sort_by='-_created_at'` (currently only validates that the value passes through to `.sort()`; verify Beanie handles underscore-prefixed fields — the stored MongoDB field name is `_created_at`, need to confirm Beanie translates this correctly)
- [ ] MODE column header in `log_table.html` becomes sortable (same pattern as CALL/BAND)
- [ ] `_created_at` sort icon in `log_table.html` `<thead>` row — dedicated icon (clock or timestamp glyph), positioned as a non-data header element, cycles `-_created_at` ↔ `_created_at`

### Add After Core Is Working (v2.5 stretch goals)

- [ ] Hollow/outline double-chevron on all sortable-but-unsorted columns — improves discoverability; low effort once core sort is working
- [ ] `aria-sort` attributes on active `<th>` elements

### Future Consideration (v2.6+)

- [ ] Sort by FREQ with numeric coercion — requires `FREQ_numeric` derived field stored on insert, migration of existing records, potential breaking changes to `build_qso_dict()`; deferred until there is clear user demand

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `_created_at` system field | HIGH — unambiguous insert order, no QSO_DATE backdating ambiguity | LOW | P1 |
| `_created_at` sort icon | HIGH — the reason `_created_at` exists | MEDIUM | P1 |
| MODE column sortable | MEDIUM — FT8/CW/SSB review use case | LOW | P1 |
| MongoDB index on `_created_at` | HIGH (correctness for large logs) | LOW | P1 |
| Hollow icon on unsorted sortable columns | LOW-MEDIUM — discoverability | LOW | P2 |
| `aria-sort` on active `<th>` | LOW (personal tool) | LOW | P2 |
| FREQ sortable with numeric coercion | LOW | HIGH | P3 (defer) |
| Multi-column sort | LOW | HIGH | skip |
| Three-state sort cycle | LOW | MEDIUM | skip |
| RST sortable | NONE | LOW | skip |

---

## Ham Radio Domain Notes on Sort Usefulness

Based on domain research into how ham operators actually use logbooks (Ham Radio Deluxe, Log4OM, Xlog, QRZ Logbook) and the QSO confirmation matching criteria used by LoTW/eQSL:

**Most useful sorts (in priority order):**
1. **Date/Time descending** (default) — "what did I just work?" — most recent first
2. **Callsign ascending** — "have I worked this station before?" — alphabetical lookup
3. **Band ascending** — "what did I work on 20M?" — band review (or use Band filter)
4. **Mode ascending** — "show all FT8 QSOs together" — mode review
5. **Entry timestamp (`_created_at`) descending** — "which QSOs were most recently entered into this system?" — useful to verify UDP auto-logging worked, or to find QSOs inserted by import vs manual entry when `QSO_DATE` was backdated

**Confirms anti-feature decisions:**
- Frequency sorting: the Band filter is a more precise tool for frequency-range review; FREQ string sort is semantically incorrect
- RST sorting: no ham operator reviews logs sorted by signal report; zero practical use
- Secondary/multi-column sort: ham log review is always single-dimension (find contacts on a band, find contacts by callsign, etc.)

---

## Sources

- Direct codebase inspection: `templates/log/log_table.html`, `templates/log/log.html`, `app/qso/ui_router.py`, `app/qso/service.py`, `app/qso/models.py` — HIGH confidence
- HTMX table sorting pattern: https://dev.to/vladkens/table-sorting-and-pagination-with-htmx-3dh8 — MEDIUM confidence (community article, verified against existing implementation)
- W3C WAI-ARIA sortable table example: https://www.w3.org/WAI/ARIA/apg/patterns/table/examples/sortable-table/ — HIGH confidence (official spec)
- Adrian Roselli sortable table columns UX: https://adrianroselli.com/2021/04/sortable-table-columns.html — HIGH confidence (authoritative accessibility source)
- MDN aria-sort reference: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-sort — HIGH confidence (official spec)
- TanStack Table sort cycle documentation: https://tanstack.com/table/latest/docs/guide/sorting — MEDIUM confidence (confirms three-state cycle is a known anti-feature for simple use cases)
- Ham Radio Deluxe QSO fields: https://support.hamradiodeluxe.com/support/solutions/articles/51000052691-creating-and-managing-qsos — MEDIUM confidence
- Ham radio logging common sort fields: https://hamradioplayground.com/digital-modes-tech/logging-software/log-organize-qso-contacts — MEDIUM confidence (community article)

---
*Feature research for: v2.5 QSO Sorting & Entry Timestamp (ollog)*
*Researched: 2026-04-20*
