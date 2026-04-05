# Troubleshooting

## SSE Station Feed Not Updating

**Symptom:** You log a QSO but the live feed does not show it.

**Cause:** MongoDB is not running in replica set mode. ollog uses MongoDB change streams for the live feed, and change streams require a replica set.

**Fix:**

1. Check that MongoDB was started with `--replSet rs0` (the docker-compose.yml does this automatically).
2. Verify the replica set is initialized:
   ```
   docker compose exec mongodb mongosh --eval "rs.status()"
   ```
   The output should show a member with `stateStr: "PRIMARY"`.
3. Check that `MONGODB_URI` includes `?replicaSet=rs0` (the docker-compose.yml sets this).
4. If using an external MongoDB, ensure it is configured as a replica set.

## Login Fails After Container Restart

**Symptom:** Users cannot log in after restarting the containers, even with correct credentials.

**Cause:** The most common cause is that the browser still holds an expired or invalidated JWT cookie. This happens when `SECRET_KEY` changed between restarts — all previously issued tokens become invalid because JWT signatures are verified against `SECRET_KEY`. Note that `SECRET_KEY` is used only for JWT signing; password hashing uses Argon2 and is independent of `SECRET_KEY`. Users can still log in with their username and password to receive a new token.

If login itself fails with correct credentials (username/password rejected), the issue is different: the account may be disabled, or the password may have been changed.

**Fix:**

1. Clear browser cookies for the ollog domain and log in again to obtain a fresh token.
2. To prevent this after future restarts, set `SECRET_KEY` to a fixed value in your `.env` file so it persists across restarts:
   ```
   SECRET_KEY=your-long-random-secret-here
   ```
3. If accounts are disabled or passwords are unknown, reset them via the admin API (`POST /api/admin/users/{username}/reset-password`).

## ADIF Import Returns All Duplicates

**Symptom:** Importing an ADIF file reports every record as a duplicate.

**Cause:** The file was already imported previously. ollog's duplicate detection matches on CALL + BAND + MODE + operator within a +/- 2 minute window, so re-importing the same file will flag every record.

**Fix:**

- If you intentionally want to re-import, delete the existing records first (via the UI or API) and then import again.
- The import endpoint does not support `?force=true`. Force override is only available on single QSO creation (`POST /api/qsos/?force=true`). For bulk re-import, delete first then import.
