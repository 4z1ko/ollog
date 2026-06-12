# Phase 64: ACLog Bridge Manual Sync - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-12
**Phase:** 64-aclog-bridge-manual-sync
**Areas discussed:** Sync Button Placement, Sync Runtime Behavior, Report Details, Duplicate Meaning

---

## Sync Button Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Saved bridges only | Show Sync only for existing saved bridge rows. New/unsaved bridge rows must be saved first. | ✓ |
| All rows with host/port | Let users sync even an unsaved row if host/port are filled in. | |
| You decide | Agent chooses the simplest implementation that fits the existing profile form pattern. | |

**User's choice:** Saved bridges only  
**Notes:** Sync should target only stable bridge IDs already saved in the operator profile.

| Option | Description | Selected |
|--------|-------------|----------|
| Per-bridge inline report | Show the result directly under/near the bridge row that was synced. | |
| Shared ACLog Bridges report area | Show one result area at the bottom of the ACLog Bridges card. | |
| Use existing profile result area | Reuse `#profile-result` near the top of the page. | ✓ |

**User's choice:** Use existing profile result area  
**Notes:** Avoids adding new report targets and reuses the existing profile feedback pattern.

---

## Sync Runtime Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Wait and report when done | Button request stays open until ACLog sync finishes, then swaps in the report. | ✓ |
| Start background job | Button starts a background sync and page polls or refreshes for status. | |
| You decide | Agent chooses the smallest reliable approach. | |

**User's choice:** Wait and report when done  
**Notes:** Manual sync is synchronous from the operator's perspective.

| Option | Description | Selected |
|--------|-------------|----------|
| Use a fixed timeout and report failure | Timeout on offline/slow/incomplete ACLog responses and show a clear error report. | ✓ |
| Import partial records before timeout | Import records received before timeout and report partial success. | |
| You decide | Agent chooses safest behavior. | |

**User's choice:** Use a fixed timeout and report failure  
**Notes:** Clear failure is preferred over ambiguous partial imports.

| Option | Description | Selected |
|--------|-------------|----------|
| No app-side cap | Process all records returned by `<CMD><LIST><INCLUDEALL></CMD>` within timeout. | ✓ |
| High safety cap | Request all records but stop after a high app-side limit. | |
| You decide | Agent aligns with milestone requirement and documents risk. | |

**User's choice:** No app-side cap  
**Notes:** Matches the user's requirement to request and process all remote ACLog QSOs.

---

## Report Details

| Option | Description | Selected |
|--------|-------------|----------|
| Simple summary | Imported X missing QSOs, skipped Y already present, errors Z. | ✓ |
| Detailed summary | Include bridge name, remote received, imported, skipped, rejected, status, and examples. | |
| You decide | Agent chooses a useful but non-noisy report. | |

**User's choice:** Simple summary  
**Notes:** Keep the UI concise.

| Option | Description | Selected |
|--------|-------------|----------|
| Missing QSOs imported | Explicitly says imported QSOs were remote records not found locally. | ✓ |
| Imported QSOs | Shorter and familiar. | |
| Use both | Example: "Imported 12 missing QSOs." | |

**User's choice:** Missing QSOs imported  
**Notes:** Use this exact wording for the main report count.

| Option | Description | Selected |
|--------|-------------|----------|
| Count only | Keep error reporting to counts only. | |
| Count plus first few examples | Show a few rejected calls/reasons for diagnosis. | ✓ |
| You decide | Agent keeps the report consistent with simple summary. | |

**User's choice:** Count plus first few examples  
**Notes:** Show a compact sample of rejected records when errors exist.

---

## Duplicate Meaning

| Option | Description | Selected |
|--------|-------------|----------|
| Use existing duplicate logic | Same operator, call, band, mode, and QSO time window/rowHash behavior. | |
| Exact rowHash only | Only skip when canonical rowHash matches exactly. | ✓ |
| Stricter exact identity | Skip if call, date, time, band, mode, and key fields exactly match. | |
| You decide | Agent chooses app-consistent behavior. | |

**User's choice:** Exact rowHash only  
**Notes:** Exact rowHash is the preferred definition of already present for sync pre-checks.

| Option | Description | Selected |
|--------|-------------|----------|
| Import it anyway | Exact rowHash is the source of truth; if not exact, add it. | |
| Skip and count as duplicate | Loose duplicate detection can still block import. | ✓ |
| Reject and count separately | Report as near duplicate separately from exact skipped records. | |

**User's choice:** Skip and count as duplicate  
**Notes:** If current ingest/duplicate logic flags the record as duplicate, skip it and count it as duplicate/already present.

## the agent's Discretion

- Choose exact timeout value.
- Choose number of rejection examples to display.
- Choose route, helper, and template names consistent with existing code.
- Choose exact implementation mechanics for rowHash pre-check versus existing ingest result handling.

## Deferred Ideas

None.
