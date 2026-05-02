# Phase 53: Live Clock, Lock/Unlock, and Post-Submit Behavior - Pattern Map

**Mapped:** 2026-04-29
**Files analyzed:** 1 (single modified file)
**Analogs found:** 1 / 1 (the target file itself is the primary analog — all new JS is added to the existing IIFE)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `templates/log/form.html` | component (form + inline JS) | event-driven (HTMX hooks, setInterval, DOM events) | `templates/log/form.html` (existing IIFE) | exact — extend in place |

There is only one file. All new code is inserted into the existing `<script>` IIFE at the bottom of `templates/log/form.html`. Secondary analogs are drawn from elsewhere in the template tree for the sub-patterns below.

---

## Pattern Assignments

### `templates/log/form.html` — all six sub-patterns

---

#### Sub-pattern A: Existing IIFE shell (the container for all new code)

**Analog:** `templates/log/form.html` lines 169–257 (the entire existing `<script>` block)

**Key points the planner must preserve:**

- Everything lives inside `(function () { ... })();` — no globals leak out except through `window.*` or element IDs.
- `var form = document.getElementById('qso-form');` is already declared at line 171 — do not redeclare.
- `var submitAttempted = false;` is already declared at line 172.
- The module-scoped `var timeInterval = null;` must be declared at the top of the IIFE, alongside `form` and `submitAttempted`.

**Existing IIFE opening** (lines 169–172):
```javascript
<script>
(function () {
  var form = document.getElementById('qso-form');
  var submitAttempted = false;
```

**Pattern to add at top of IIFE** (new variable, alongside existing ones):
```javascript
  var timeInterval = null;  // stores setInterval id for the live UTC time clock
```

---

#### Sub-pattern B: Heroicons inline SVG style

**Analog:** `templates/base_app.html` line 24 and `templates/log/profile.html` line 151
**Also:** `templates/log/form.html` lines 116–119 (the existing submit button SVG, stroke-width="2")

The sidebar icons and profile submit button use `stroke-width="1.5"`. The form submit button uses `stroke-width="2"`. Per CONTEXT.md D-05, padlock icons must use `stroke-width="1.5"` (Heroicons outline standard).

**Canonical SVG wrapper pattern** (from `templates/base_app.html` line 24):
```html
<svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
  <path stroke-linecap="round" stroke-linejoin="round" d="..." />
</svg>
```

**Padlock icon size** (from CONTEXT.md D-05 / RESEARCH.md): `w-4 h-4` (same as the submit button icon at line 116).

**Lock-closed SVG** (Heroicons 24/outline, path from RESEARCH.md):
```html
<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
  <path stroke-linecap="round" stroke-linejoin="round"
        d="M16.5 10.5V6.75C16.5 4.26472 14.4853 2.25 12 2.25C9.51472 2.25 7.5 4.26472 7.5 6.75V10.5M6.75 21.75H17.25C18.4926 21.75 19.5 20.7426 19.5 19.5V12.75C19.5 11.5074 18.4926 10.5 17.25 10.5H6.75C5.50736 10.5 4.5 11.5074 4.5 12.75V19.5C4.5 20.7426 5.50736 21.75 6.75 21.75Z" />
</svg>
```

**Lock-open SVG** (Heroicons 24/outline, path from RESEARCH.md):
```html
<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
  <path stroke-linecap="round" stroke-linejoin="round"
        d="M13.5 10.5V6.75C13.5 4.26472 15.5147 2.25 18 2.25C20.4853 2.25 22.5 4.26472 22.5 6.75V10.5M3.75 21.75H14.25C15.4926 21.75 16.5 20.7426 16.5 19.5V12.75C16.5 11.5074 15.4926 10.5 14.25 10.5H3.75C2.50736 10.5 1.5 11.5074 1.5 12.75V19.5C1.5 20.7426 2.50736 21.75 3.75 21.75Z" />
</svg>
```

---

#### Sub-pattern C: Padlock input wrapper HTML (relative + absolute button)

**Analog:** No exact match exists in the codebase — no password show/hide toggle exists. The closest structural analog is `templates/log/log.html` lines 106–116 (a `div` containing a sibling inline SVG badge). However, the password-show/hide `relative` + `absolute inset-y-0 right-0` pattern is industry-standard and is called out explicitly in CONTEXT.md D-04.

**Existing QSO_DATE input** (form.html lines 39–43) — this is what gets wrapped:
```html
<!-- QSO_DATE -->
<div>
  <label class="form-label">Date (UTC)</label>
  <input type="text" name="QSO_DATE" placeholder="YYYYMMDD" required autocomplete="off"
         class="form-input font-mono">
</div>
```

**Replacement pattern** (per D-04, D-05, D-06):
```html
<!-- QSO_DATE -->
<div>
  <label class="form-label">Date (UTC)</label>
  <div class="relative">
    <input type="text" name="QSO_DATE" id="qso-date-input"
           placeholder="YYYYMMDD" required autocomplete="off"
           class="form-input font-mono pr-9 bg-gray-50 dark:bg-gray-800/50 cursor-not-allowed">
    <button type="button" id="qso-date-lock"
            class="absolute inset-y-0 right-0 flex items-center pr-2.5
                   text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
      <svg id="qso-date-lock-icon" class="w-4 h-4" fill="none" viewBox="0 0 24 24"
           stroke-width="1.5" stroke="currentColor">
        <!-- lock-closed path rendered by default (locked state on page load) -->
        <path stroke-linecap="round" stroke-linejoin="round"
              d="M16.5 10.5V6.75C16.5 4.26472 14.4853 2.25 12 2.25C9.51472 2.25 7.5 4.26472 7.5 6.75V10.5M6.75 21.75H17.25C18.4926 21.75 19.5 20.7426 19.5 19.5V12.75C19.5 11.5074 18.4926 10.5 17.25 10.5H6.75C5.50736 10.5 4.5 11.5074 4.5 12.75V19.5C4.5 20.7426 5.50736 21.75 6.75 21.75Z" />
      </svg>
    </button>
  </div>
</div>
```

The same pattern applies to TIME_ON, using `id="qso-time-input"` and `id="qso-time-lock"` and `id="qso-time-lock-icon"`.

**CRITICAL — Tailwind purge:** `bg-gray-50`, `dark:bg-gray-800/50`, and `cursor-not-allowed` must appear as complete literal strings in the template HTML. They do in the above snippet. Run `npm run build && npm run verify` after adding.

---

#### Sub-pattern D: Validation rules object and validate() function

**Analog:** `templates/log/form.html` lines 177–207 (existing `rules` object and `validate()`)

**Existing rules object** (lines 177–183):
```javascript
var rules = {
  CALL:     function (v) { return v.trim().length > 0; },
  QSO_DATE: function (v) { return /^\d{8}$/.test(v.trim()); },
  TIME_ON:  function (v) { return /^\d{4}$/.test(v.trim()); },  // MUST change to /^\d{6}$/
  BAND:     function (v) { return v.trim().length > 0; },
  MODE:     function (v) { return v.trim().length > 0; },
};
```

**Updated TIME_ON rule** (D-10 — after normalization, TIME_ON is always 6 digits):
```javascript
TIME_ON:  function (v) { return /^\d{6}$/.test(v.trim()); },
```

**Existing validate()** (lines 197–207):
```javascript
function validate() {
  var ok = true;
  Object.keys(rules).forEach(function (name) {
    var el = field(name);
    if (!el) return;
    var valid = rules[name](el.value);
    setError(el, !valid);
    if (!valid) ok = false;
  });
  return ok;
}
```

**Updated validate() with locked-field skip** (D-12):
```javascript
function validate() {
  var ok = true;
  Object.keys(rules).forEach(function (name) {
    var el = field(name);
    if (!el) return;
    if (el.readOnly) { setError(el, false); return; }  // locked = always valid
    var valid = rules[name](el.value);
    setError(el, !valid);
    if (!valid) ok = false;
  });
  return ok;
}
```

---

#### Sub-pattern E: HTMX event listeners (htmx:beforeRequest and htmx:afterSwap)

**Analog:** `templates/log/form.html` lines 237–255

**Existing htmx:beforeRequest** (lines 237–241):
```javascript
form.addEventListener('htmx:beforeRequest', function (e) {
  submitAttempted = true;
  if (!validate()) {
    e.preventDefault();
  }
});
```

**Updated htmx:beforeRequest** with HHMM normalization prepended (D-10):
```javascript
form.addEventListener('htmx:beforeRequest', function (e) {
  // Step 1: normalize HHMM → HHMM00 (TIME-04)
  var timeEl = field('TIME_ON');
  if (timeEl && !timeEl.readOnly && /^\d{4}$/.test(timeEl.value.trim())) {
    timeEl.value = timeEl.value.trim() + '00';
  }
  // Step 2: gate behind validation (existing)
  submitAttempted = true;
  if (!validate()) {
    e.preventDefault();
  }
});
```

**Existing htmx:afterSwap** (lines 245–255):
```javascript
document.body.addEventListener('htmx:afterSwap', function (e) {
  if (!e.detail.target || e.detail.target.id !== 'qso-result') return;
  var result = document.getElementById('qso-result');
  if (result && result.querySelector('.success-msg')) {
    form.reset();
    clearErrors();
    submitAttempted = false;
    var callField = form.querySelector('[name="CALL"]');
    if (callField) callField.focus();
  }
});
```

**Updated htmx:afterSwap** with reset-mode branch (D-07, D-08, D-09):
```javascript
document.body.addEventListener('htmx:afterSwap', function (e) {
  if (!e.detail.target || e.detail.target.id !== 'qso-result') return;
  var result = document.getElementById('qso-result');
  if (result && result.querySelector('.success-msg')) {
    var mode = localStorage.getItem('ollog.resetMode');
    if (mode !== 'keep') {
      // "Reset to live UTC" (default when not set)
      form.reset();
      initDateTime();  // re-populate + re-lock + restart interval
    }
    // Both modes: clear errors, reset attempt flag, focus CALL
    clearErrors();
    submitAttempted = false;
    var callField = form.querySelector('[name="CALL"]');
    if (callField) callField.focus();
  }
});
```

---

#### Sub-pattern F: localStorage for user preference

**Analog:** `templates/base_app.html` lines 186–188 and `templates/base.html` lines 22–25

The theme toggle is the closest existing localStorage pattern. It uses a simple `localStorage.setItem`/`localStorage.getItem` with a plain string key. Same pattern applies for `ollog.resetMode`.

**Theme toggle pattern** (base_app.html lines 186–188 — structure to copy):
```javascript
function toggleTheme() {
  var isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  // ...
}
```

**Theme restore on load** (base.html lines 22–25):
```javascript
var theme = localStorage.getItem('theme');
if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
  document.documentElement.classList.add('dark');
}
```

**Reset-mode toggle pattern** (applying the same read/write idiom, per D-01, D-02, D-03):
```html
<!-- Tailwind peer-checked toggle — all class strings must be literals for purge -->
<div class="flex items-center gap-2">
  <input type="checkbox" id="reset-mode-toggle" class="sr-only peer">
  <label for="reset-mode-toggle"
         class="relative inline-flex items-center cursor-pointer
                w-9 h-5 bg-gray-300 dark:bg-gray-600 rounded-full
                peer-checked:bg-indigo-500
                after:content-[''] after:absolute after:top-0.5 after:left-0.5
                after:bg-white after:rounded-full after:h-4 after:w-4
                after:transition-all
                peer-checked:after:translate-x-4">
  </label>
  <span class="text-xs text-gray-500 dark:text-gray-400" id="reset-mode-label">
    Reset to live UTC
  </span>
</div>
```

```javascript
// Restore toggle state from localStorage + wire change handler
(function initResetToggle() {
  var toggle = document.getElementById('reset-mode-toggle');
  var label  = document.getElementById('reset-mode-label');
  var saved  = localStorage.getItem('ollog.resetMode');
  toggle.checked = (saved !== 'keep');  // default ON = reset mode
  label.textContent = toggle.checked ? 'Reset to live UTC' : 'Keep current date/time';
  toggle.addEventListener('change', function () {
    if (toggle.checked) {
      localStorage.setItem('ollog.resetMode', 'reset');
      label.textContent = 'Reset to live UTC';
    } else {
      localStorage.setItem('ollog.resetMode', 'keep');
      label.textContent = 'Keep current date/time';
    }
  });
})();
```

---

#### Sub-pattern G: Submit row HTML (toggle placement)

**Analog:** `templates/log/form.html` lines 114–122 (existing submit row)

**Existing submit row** (lines 114–122):
```html
<div class="flex items-center gap-3">
  <button type="submit" class="btn-primary">
    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
    Log QSO
  </button>
  <button type="reset" class="btn-ghost btn-sm">Clear</button>
</div>
```

**Updated submit row** with toggle appended (D-02 — same flex row):
```html
<div class="flex items-center gap-3 flex-wrap">
  <button type="submit" class="btn-primary">
    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
    Log QSO
  </button>
  <button type="reset" class="btn-ghost btn-sm">Clear</button>
  <!-- Reset-mode toggle (RESET-01, RESET-02, RESET-03) -->
  <div class="flex items-center gap-2 ml-auto">
    <input type="checkbox" id="reset-mode-toggle" class="sr-only peer">
    <label for="reset-mode-toggle"
           class="relative inline-flex items-center cursor-pointer
                  w-9 h-5 bg-gray-300 dark:bg-gray-600 rounded-full
                  peer-checked:bg-indigo-500
                  after:content-[''] after:absolute after:top-0.5 after:left-0.5
                  after:bg-white after:rounded-full after:h-4 after:w-4
                  after:transition-all
                  peer-checked:after:translate-x-4">
    </label>
    <span class="text-xs text-gray-500 dark:text-gray-400" id="reset-mode-label">Reset to live UTC</span>
  </div>
</div>
```

---

## Shared Patterns

### Inline SVG icon convention
**Source:** `templates/base_app.html` (sidebar nav icons, e.g. line 24) and `templates/log/profile.html` line 151
**Apply to:** All padlock SVGs in form.html
```html
fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"
```
The submit button at form.html line 116 uses `stroke-width="2"` — padlock icons must use `1.5` to match Heroicons outline standard (D-05).

### Dark mode color choices
**Source:** `static/css/input.css` component definitions
**Apply to:** All new Tailwind classes in form.html

| Purpose | Light class | Dark class |
|---------|-------------|------------|
| Locked field background | `bg-gray-50` | `dark:bg-gray-800/50` |
| Toggle pill (off) | `bg-gray-300` | `dark:bg-gray-600` |
| Toggle pill (on) | `peer-checked:bg-indigo-500` | (same — indigo reads well in both modes) |
| Toggle thumb | `after:bg-white` | (same) |
| Padlock icon default | `text-gray-400` | (inherits) |
| Padlock icon hover | `hover:text-gray-600` | `dark:hover:text-gray-300` |
| Form input base (unlocked) | `bg-white` (via .form-input) | `dark:bg-gray-800` (via .form-input) |

### HTMX event listener attachment pattern
**Source:** `templates/log/form.html` lines 237–255
**Apply to:** All new HTMX listeners in form.html

- `htmx:beforeRequest` → attach on `form` (not `document.body`)
- `htmx:afterSwap` → attach on `document.body`, gate by `e.detail.target.id === 'qso-result'`

### localStorage read/write pattern
**Source:** `templates/base_app.html` lines 186–188 and `templates/base.html` lines 22–25
**Apply to:** Reset-mode toggle and its restore-on-load IIFE
- Direct `localStorage.getItem` / `localStorage.setItem` — no abstraction layer
- Key: `ollog.resetMode` (namespaced to avoid collision with `theme`)

### `type="button"` for non-submit buttons inside forms
**Source:** `templates/log/token_created.html` lines 8 and 12; `templates/admin/restore/password_modal.html` line 28
**Apply to:** Padlock `<button>` elements
- Always `type="button"` — prevents accidental form submission on click

---

## No Analog Found

None. All patterns for Phase 53 are directly sourced from the existing codebase or from the verified RESEARCH.md code examples. The padlock input-wrapper HTML is a new structural pattern in this codebase, but it follows industry-standard `relative`/`absolute` positioning that is already used for the modal backdrop (`templates/admin/restore/password_modal.html`) and the login page layout.

---

## Metadata

**Analog search scope:** `templates/**/*.html`, `static/css/input.css`, `tailwind.config.js`
**Files scanned:** 15+ template files, input.css, tailwind.config.js
**Pattern extraction date:** 2026-04-29

**Note to planner:** This phase modifies exactly one file. All JS changes go inside the existing IIFE in `templates/log/form.html`. The implementation order that avoids merge conflicts within the single file is:
1. Add `var timeInterval = null;` at top of IIFE
2. Add `initDateTime()`, `applyLockedStyle()`, `removeLockedStyle()`, `pad2()` helper functions
3. Add padlock toggle functions `toggleDateLock()`, `toggleTimeLock()`
4. Update the `rules` object (TIME_ON regex only)
5. Update `validate()` to skip locked fields
6. Update `htmx:beforeRequest` to prepend normalization
7. Update `htmx:afterSwap` to branch on localStorage
8. Add `form.addEventListener('reset', ...)` for the Clear button
9. Add `initResetToggle()` IIFE
10. Call `initDateTime()` at the bottom of the outer IIFE (page load)
11. Update HTML: wrap QSO_DATE and TIME_ON inputs with `relative` div + padlock button
12. Update HTML: add toggle to submit row
