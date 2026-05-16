# Patch Approval Audit Trail

Every manual approval and patch apply action must be logged.

## Required fields
- `event`: `approve_clicked` | `patch_applied`
- `actor`: user id / operator id
- `timestamp_utc`: ISO-8601 UTC time
- `patch_id`: unique patch identifier
- `patch_sha256`: sha256 digest of applied patch payload
- `files`: list of touched files
- `result`: `approved` | `rejected` | `applied` | `failed`

## Example line-delimited JSON log entries
```json
{"event":"approve_clicked","actor":"maintainer@example","timestamp_utc":"2026-05-16T12:34:56Z","patch_id":"patch-017","patch_sha256":"abc123...","files":["README.md"],"result":"approved"}
{"event":"patch_applied","actor":"maintainer@example","timestamp_utc":"2026-05-16T12:35:01Z","patch_id":"patch-017","patch_sha256":"abc123...","files":["README.md"],"result":"applied"}
```

## Enforcement notes
- `patch_applied` without a preceding valid `approve_clicked` for same `patch_id` is invalid.
- Timestamps must be generated server-side in UTC.
- Log entries must be append-only.
