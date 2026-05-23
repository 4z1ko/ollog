# Profile

Your ollog profile stores your station information. Fields set in your profile are auto-stamped on QSOs you log.

## Auto-Stamping Behavior

| Field | Auto-stamped as | When |
|-------|----------------|------|
| Account callsign (OPERATOR) | `OPERATOR` ADIF field | Every QSO — cannot be overridden |
| `station_callsign` | `STATION_CALLSIGN` ADIF field | When set in profile |

The `OPERATOR` field is set by the administrator at account creation. You cannot change it via the profile API. If you need a different operator callsign, contact your administrator.

`STATION_CALLSIGN` represents the station you are operating *from* — for example, a club station callsign or special event call. Set it in your profile and it will be auto-stamped on every future QSO.

## Get Profile

### GET /api/profile/

```bash
curl http://localhost:8000/api/profile/ \
  -H "Authorization: Bearer $TOKEN"
```

Response:

```json
{
  "callsign": "W1AW",
  "station_callsign": "W1AW",
  "name": "Hiram Percy Maxim",
  "email": null,
  "qth": "Hartford, CT",
  "state": "CT",
  "country": "USA",
  "my_gridsquare": "FN31pr",
  "latitude": 41.75,
  "longitude": -72.75,
  "my_rig": "Icom IC-7300",
  "my_antenna": "Dipole",
  "tx_pwr": 100.0
}
```

## Update Profile

### PATCH /api/profile/

Only the fields you include are updated. Absent fields are left unchanged.

```bash
curl -X PATCH http://localhost:8000/api/profile/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"station_callsign": "W1AW", "my_gridsquare": "FN31pr", "name": "Your Name"}'
```

### Editable Fields

| Field | Type | Notes |
|-------|------|-------|
| `station_callsign` | string or null | Auto-stamped on future QSOs as STATION_CALLSIGN |
| `name` | string or null | Your name |
| `email` | string or null | Email address |
| `qth` | string or null | Location description |
| `state` | string or null | State/province |
| `country` | string or null | Country |
| `my_gridsquare` | string or null | Maidenhead locator (4 or 6 characters, e.g. `FN31pr`). When set, `latitude` and `longitude` are auto-computed from the grid center. |
| `my_rig` | string or null | Your transceiver |
| `my_antenna` | string or null | Your antenna |
| `tx_pwr` | float or null | Transmit power in watts |
| `aclog_bridges` | array | Optional per-user ACLog TCP API bridge locations |

## ACLog Bridges

The **ACLog Bridges** section on the profile page lets you connect ollog to one
or more N3FJP ACLog installations through ACLog's TCP API. Each enabled bridge
listens for ACLog `ENTEREVENT` messages and logs those contacts to your ollog
account.

Each bridge has:

| Field | Notes |
|-------|-------|
| Name | A local label, such as `Shack PC` or `Laptop` |
| Host | The hostname or IP address of the computer running ACLog |
| Port | ACLog API TCP port, commonly `1100` |
| Enabled | Whether ollog should keep this bridge connected |

For setup steps and troubleshooting, see [ACLog Bridges](aclog-bridges.md).

### Clearing a Field

To clear `station_callsign` (stop auto-stamping it on QSOs):

```bash
curl -X PATCH http://localhost:8000/api/profile/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"station_callsign": null}'
```

## STATION_CALLSIGN Environment Variable

The `STATION_CALLSIGN` environment variable on the server is not the same as the profile field. The env var is used as a system-level default if the operator's profile has no `station_callsign` set. Consult your administrator or see [Environment Variables](../reference/environment-variables.md) for details.

## Danger Zone

The **Danger Zone** section appears at the bottom of your profile page and contains
irreversible account actions.

To clear your log:

1. Navigate to **Profile** in the navigation bar.
2. Scroll to the **Danger Zone** section at the bottom of the page.
3. Click **Clear my log**.
4. A confirmation modal opens showing the number of QSOs that will be deleted.
5. Enter your password in the **Your password** field.
6. Click **Delete N QSOs** (where N is the count shown) to confirm, or **Keep my log**
   to cancel.

!!! danger "This cannot be undone"
    Clearing your log permanently deletes all your QSOs from the database. There is no
    undo and no recovery from the UI. If you need to recover deleted QSOs, restore from
    a backup taken before the clear operation.
