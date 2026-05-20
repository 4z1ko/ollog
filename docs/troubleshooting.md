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
3. If accounts are disabled or passwords are unknown, reset them via the admin API (`POST /admin/users/{username}/reset-password`).

## ADIF Import Returns All Duplicates

**Symptom:** Importing an ADIF file reports every record as a duplicate.

**Cause:** The file was already imported previously. ollog's duplicate detection matches on CALL + BAND + MODE + operator within a +/- 2 minute window, so re-importing the same file will flag every record.

**Fix:**

- If you intentionally want to re-import, delete the existing records first (via the UI or API) and then import again.
- The import endpoint does not support `?force=true`. Force override is only available on single QSO creation (`POST /api/qsos/?force=true`). For bulk re-import, delete first then import.

## UDP Socket Not Binding

**Symptom:** The API container exits on startup with an error, or the UDP listener never starts. No QSOs sent over UDP are received.

**Cause:** Two possible causes:

1. **Port already in use.** Another process on the host is listening on port 2399/UDP.
2. **UDP_BIND_HOST mismatch.** The default `UDP_BIND_HOST` is `127.0.0.1`, which binds to localhost only. Inside a Docker container this means the listener is unreachable from outside the container. All UDP traffic is silently dropped.

**Fix:**

1. Confirm the listener started successfully by checking the logs:
   ```
   docker compose logs api | grep -i udp
   ```
   A successful start shows:
   ```
   UDP listener bound to 0.0.0.0:2399
   ```
2. If the port is in use, identify and stop the conflicting process, or change `UDP_PORT` to an available port in your `.env` file and update the `ports` mapping in `docker-compose.yml` to match.
3. For Docker deployments, set `UDP_BIND_HOST=0.0.0.0` in your `.env` file so the listener accepts datagrams from outside the container:
   ```
   UDP_BIND_HOST=0.0.0.0
   UDP_PORT=2399
   ```
4. Restart the stack after any change:
   ```
   docker compose down && docker compose up -d
   ```

## UDP_OPERATOR Callsign Issue

**Symptom:** QSOs sent over UDP are either silently discarded or accepted but not attributed to an operator profile.

**Cause:** Two distinct sub-cases with different behavior:

1. **`UDP_OPERATOR` is not set at all.** Every incoming datagram is discarded with a WARNING. No QSOs are inserted.
2. **`UDP_OPERATOR` is set but the callsign is not found in the database.** A WARNING fires at startup, but QSOs are still inserted — they are just not linked to an operator profile (no profile stamping).

**Fix:**

1. Tail the logs and look for the relevant warning:
   ```
   docker compose logs -f api | grep -i udp
   ```
   If you see:
   ```
   UDP_OPERATOR not configured — datagram from ('192.168.1.10', 54321) discarded
   ```
   `UDP_OPERATOR` is missing from your environment. Add it to `.env`:
   ```
   UDP_OPERATOR=W1AW
   ```
   If you see:
   ```
   UDP_OPERATOR callsign 'W1AW' not found in DB — profile stamping disabled
   ```
   The variable is set but the callsign does not match any operator account.
2. Log in to ollog and verify an operator account exists with exactly the callsign set in `UDP_OPERATOR`. Callsigns are case-sensitive — `w1aw` and `W1AW` are different values.
3. If the account does not exist, create it via the admin interface or the API (`POST /admin/users`), then set the operator's callsign field to match `UDP_OPERATOR` exactly.
4. Restart the stack for the new environment variable to take effect:
   ```
   docker compose down && docker compose up -d
   ```

## QSOs Arrive but Do Not Appear in the Log

**Symptom:** The API receives UDP datagrams (traffic visible in logs) but no new QSOs appear in the log view or via `GET /api/qsos/`.

**Cause:** Two possible causes:

1. **Missing required ADIF field.** The datagram is rejected during parsing because a mandatory field (`CALL`, `QSO_DATE`, `TIME_ON`, `BAND`, or `MODE`) is absent or empty.
2. **Duplicate QSO.** A QSO with the same `CALL + BAND + MODE` and operator already exists within a ±2 minute window and the datagram is flagged as a duplicate.

**Fix:**

1. Tail the logs to identify the disposition of incoming datagrams:
   ```
   docker compose logs -f api | grep -i udp
   ```
2. A rejection due to a missing field looks like:
   ```
   UDP datagram src=192.168.1.10:54321 disposition=rejected reason="missing required field: BAND"
   ```
   Check the ADIF output your logging software sends and confirm all five required fields are populated: `CALL`, `QSO_DATE`, `TIME_ON`, `BAND`, `MODE`.
3. A duplicate looks like:
   ```
   UDP datagram src=192.168.1.10:54321 call=W1AW disposition=duplicate
   ```
   This is expected behavior if the same QSO is transmitted more than once within two minutes (for example, because your logging software retransmits on save). No action is needed unless you need to force an insert, in which case delete the existing record first and retransmit.
4. A successfully accepted datagram looks like:
   ```
   UDP datagram src=192.168.1.10:54321 call=W1AW disposition=accepted id=6614a2b3e4f5c6d7e8f90123
   ```
   If you see `accepted` but the QSO still does not appear in the UI, check whether the live feed is connected (see "SSE Station Feed Not Updating" above) or apply a page refresh.

## No UDP Activity in Logs

**Symptom:** No UDP-related log lines appear at all, even after sending datagrams. The listener never starts.

**Cause:** `UDP_ENABLED` is not set or is set to `false`. The UDP listener is disabled by default and must be explicitly enabled.

**Fix:**

1. Check your `.env` file for the `UDP_ENABLED` variable:
   ```
   grep UDP_ENABLED .env
   ```
   If the variable is absent or set to `false`, the listener will not start.
2. Set `UDP_ENABLED=true` in your `.env` file:
   ```
   UDP_ENABLED=true
   UDP_PORT=2399
   UDP_BIND_HOST=0.0.0.0
   UDP_OPERATOR=W1AW
   ```
3. Restart the stack:
   ```
   docker compose down && docker compose up -d
   ```
4. Confirm the listener is running:
   ```
   docker compose logs api | grep -i udp
   ```
   You should see:
   ```
   UDP listener bound to 0.0.0.0:2399
   ```
