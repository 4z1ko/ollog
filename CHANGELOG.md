# Changelog

All notable changes to ollog are documented here.

This project also keeps detailed internal milestone records in
[`.planning/MILESTONES.md`](.planning/MILESTONES.md).

## [v3.7] - 2026-06-20

### Added

- Added **Pause/Start** controls to the admin Application Logs Recent Logs table.
- Added a **Clear Log Messages** action with confirmation before stored application log records are deleted.
- Added a post-clear `application_logs_cleared` audit event when audit logging succeeds.
- Added admin documentation for pause/resume behavior, clear scope, retention, and audit continuity.
- Added focused tests for pause/resume UI hooks, modal safety copy, clear-route behavior, settings preservation, and audit failure isolation.

### Changed

- Recent Logs live updates can now be paused per browser tab without affecting server-side log capture, MongoDB storage, broadcasts, polling in other tabs, or future log records.
- Starting live updates immediately refreshes the Recent Logs table to reconcile records missed while paused.
- The README now documents the current shipped milestone and admin application log controls.

### Operational Notes

- No new environment variables are required.
- No public REST API changes were introduced.
- No package version fields were changed; v3.7 is the GSD milestone version.
- The clear action deletes records from the MongoDB-backed application log collection only. It does not delete QSO records, users, API tokens, backups, `ApplicationLogSettings`, retention settings, or future logging.

### Breaking Changes

- None.
