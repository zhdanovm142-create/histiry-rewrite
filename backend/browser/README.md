# Browser layer boundary

Direct Playwright calls are allowed **only** in `backend/browser/**` and provider adapter implementations.
Any upper layers (`services/`, `patching/`, `previews/`, `queue/`) must depend on browser/provider abstractions.
