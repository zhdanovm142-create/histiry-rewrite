# histiry-rewrite

## Runtime & Security Policy

### 1) Backend binding: localhost only
- Backend services in this project **must bind only to `127.0.0.1` / `localhost`**.
- Binding to `0.0.0.0`, public interfaces, or externally routable addresses is prohibited by default.

### 2) No remote execution / no hidden autonomous background jobs
- **Remote execution is prohibited** (no implicit execution of untrusted remote commands, scripts, or payloads).
- Hidden or unattended autonomous job modes are prohibited.
- Any long-running job must be started explicitly by a user in foreground or clearly visible managed process context.

### 3) Explicit manual approval gate before patch application
- Any patch application must pass a **manual explicit approval gate**.
- Approval must be a positive user action (e.g., `approve` command or equivalent UI action), not inferred from context.
- Without approval, patch application must be rejected.

### 4) Prohibited-use banner (docs + runtime)
The project explicitly disallows:
- anti-bot bypass;
- captcha bypass;
- mass automation.

These restrictions must be shown in:
- documentation (this README and related docs);
- runtime banner / startup notice visible to operator.

### 5) Mandatory audit trail for approvals
For each approved patch event, store:
- who approved (actor id / username);
- when approved (UTC timestamp);
- which patch was applied (patch id + hash or full digest);
- target scope/files changed.

Recommended minimal record format:
```json
{
  "event": "patch_approved",
  "actor": "user@example",
  "approved_at_utc": "2026-05-16T00:00:00Z",
  "patch_id": "patch-001",
  "patch_sha256": "<digest>",
  "targets": ["path/to/file.ext"]
}
```
