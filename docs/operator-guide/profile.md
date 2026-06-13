# Profile

Your ollog profile stores station information, display preferences, custom QSO
fields, and ACLog bridge settings. Profile fields are used when ollog stamps new
QSOs that you log through the web UI, REST API, UDP, or ACLog integrations.

## Auto-Stamping Behavior

| Field | Auto-stamped as | When |
|-------|----------------|------|
| Account callsign (OPERATOR) | `OPERATOR` ADIF field | Every QSO — cannot be overridden |
| `station_callsign` | `STATION_CALLSIGN` ADIF field | When set in profile |
| `my_gridsquare` | `MY_GRIDSQUARE` ADIF field | When set in profile |
| `my_rig` | `MY_RIG` ADIF field | When set in profile |
| `my_antenna` | `MY_ANTENNA` ADIF field | When set in profile |
| `tx_pwr` | `TX_PWR` ADIF field | When set in profile |

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
  "tx_pwr": 100.0,
  "notify_sound": true,
  "aclog_bridges": [
    {
      "id": "shack-pc",
      "name": "Shack PC",
      "host": "192.168.1.50",
      "port": 1100,
      "enabled": true
    }
  ],
  "custom_qso_fields": [
    {
      "slot": 1,
      "label": "POTA Ref",
      "adif_name": "POTA_REF",
      "enabled": true,
      "fill_behavior": "previous_same_call",
      "force_uppercase": true
    }
  ]
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
| `notify_sound` | boolean | Whether the browser should play a short tone when new QSOs arrive |
| `aclog_bridges` | array | Optional per-user ACLog TCP API bridge locations |
| `custom_qso_fields` | array | Up to 8 operator-defined fields for QSO entry, ACLog Other mapping, and Log View columns |

## Custom QSO Fields

The **Custom QSO Fields** section lets you configure up to eight operator-owned
fields. These fields are useful for ACLog `Other` slots, activator/reference
fields, contest notes, or any ADIF-like tag you want to preserve with each QSO.

Each custom field has:

| Field | Notes |
|-------|-------|
| Slot | Fixed slot number, 1 through 8 |
| Label | Human-friendly label shown in the UI |
| ADIF tag | Field name stored on the QSO, such as `POTA_REF` or `MY_SPECIAL_NOTE` |
| Fill | Whether the QSO form should prefill from a previous QSO |
| Visible | Whether the field appears in the QSO form and Log View column menu |
| Uppercase | Whether submitted values are forced to uppercase |

Custom fields also appear in the Log View column chooser when enabled. If an
ACLog bridge provides `OTHER_1` through `OTHER_8`, ollog maps those values to
your configured ADIF tags for the matching slots.

## ACLog Bridges

The **ACLog Bridges** section on the profile page lets you connect ollog to one
or more N3FJP ACLog installations through ACLog's TCP API. Each enabled bridge
listens for ACLog `ENTEREVENT` messages and logs those contacts to your ollog
account. Saved bridge rows also include a **Sync** button for manual all-record
sync from that ACLog instance.

Each bridge has:

| Field | Notes |
|-------|-------|
| Name | A local label, such as `Shack PC` or `Laptop` |
| Host | The hostname or IP address of the computer running ACLog |
| Port | ACLog API TCP port, commonly `1100` |
| Enabled | Whether ollog should keep this bridge connected |

Use **Save Bridges** after adding or editing bridge rows. The Sync button appears
only for saved bridge rows, not for the blank new row.

For setup, manual sync behavior, and troubleshooting, see [ACLog Bridges](aclog-bridges.md).

## Sound Notifications

The **Sound Notifications** setting controls whether the browser plays a short
tone when a new QSO arrives through the live feed. Browser autoplay policies may
require at least one interaction with the page before sound can play.

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
