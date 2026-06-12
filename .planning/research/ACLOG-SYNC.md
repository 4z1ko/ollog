# ACLog Sync Research

**Date:** 2026-06-12
**Milestone:** v3.3 ACLog QSO Sync

## Relevant ACLog API Finding

The N3FJP ACLog TCP API can return all logged records through the `LIST` command. For this milestone, the relevant all-record, all-populated-field request is:

```xml
<CMD><LIST><INCLUDEALL></CMD>
```

`INCLUDEALL` returns every field whose value length is greater than zero. The response is ACLog's XML-like API format, not ADIF text, so ollog should reuse and extend the v3.2 ACLog full-record parser rather than expecting a raw `.adi` stream.

## Implementation Implications

- Manual sync should request all records from the selected bridge, not only the recent-record `<VALUE>N</VALUE>` variant used after live `ENTEREVENT` enrichment.
- The parser should handle multi-record `LIST` responses and preserve safe uppercase ADIF-like keys.
- Missing-record detection should rely on existing rowHash/duplicate logic where possible so sync behaves like the rest of the QSO ingest surface.
- Sync should be additive only. Existing local QSOs should be reported as skipped/already present, not overwritten.
- The operator report should distinguish remote records received, imported/missing records, already-present records, and errors.

## Sources

- N3FJP API documentation: `https://www.n3fjp.com/help/api.html`
- N3FJP File > Export ADIF documentation: `https://www.n3fjp.com/help/filemenu.html`
