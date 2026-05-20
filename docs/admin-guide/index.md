# Admin Guide

This section is for administrators responsible for deploying and maintaining an ollog instance. It covers initial deployment, the admin container, account management, and database backup.

## In This Section

- [Deployment](deployment.md) — Deploy ollog with Docker Compose; configure environment variables, MongoDB, and optional features
- [Admin Container](admin-container.md) — Start the separate admin service on port 8001 with `--profile admin`; understand the `admin_token` cookie distinction
- [Account Management](account-management.md) — Create operator accounts, enable/disable users, reset passwords
- [Backup](backup.md) — Run the backup CLI, configure `BACKUP_SCHEDULE` for automated cron backups, upload to S3

## Admin Container Note

The admin container does NOT start with plain `docker compose up`. It requires the `--profile admin` flag:

```bash
docker compose --profile admin up -d admin
```

This is intentional — port 8001 should only be exposed when you need it, not automatically on every deployment.

## Quick Reference

| Task | Where |
|------|-------|
| Create operator account | Admin container UI at port 8001, or `POST /admin/users/` |
| Reset password | `POST /admin/users/{username}/reset-password` |
| Enable/disable account | `PATCH /admin/users/{username}/enabled` |
| Manual database backup | `docker compose exec app python -m app.backup` |
| Scheduled backups | Set `BACKUP_SCHEDULE` cron expression in `.env` |
| S3 backup upload | Set `BACKUP_S3_BUCKET` and AWS credentials in `.env` |
