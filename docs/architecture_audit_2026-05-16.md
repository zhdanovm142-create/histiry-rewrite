# Browser Automation Dashboard Audit (Qwen + DeepSeek)

Date: 2026-05-16
Scope: `backend/*`, `project/*`, provider adapters, queue, browser session orchestration, patch pipeline.

## Stage 1 — Architecture Audit
### Current Architecture Analysis
- Core modules split by concern (`browser`, `providers`, `queue`, `patching`, `orchestration`) but boundaries are partially duplicated by parallel "base" APIs. 
- `backend/queue/base.py` and `backend/queue/base_task_queue.py` both define `BaseTaskQueue` with incompatible contracts.

### Detected Problems
- Duplicate abstractions with same class name for queue base interface.
- Orchestration and service contracts are partially disconnected (`orchestration/prompt_pipeline.py` not aligned with async service abstraction).

### Risk Assessment
- High chance of hidden coupling and incorrect imports.
- Refactor cost rises because type names are ambiguous.

### Refactor Proposal
- Keep one canonical queue interface; deprecate or rename the legacy one.
- Align orchestration pipeline with async runtime contract.

### Minimal Patch Plan
1. Convert prompt pipeline runtime to async-safe queue and async adapter calls.
2. In next patch: rename one of duplicate queue base contracts and add compatibility alias.

### Targeted Code Changes
- Implemented Step 1 in this patch (`backend/orchestration/prompt_pipeline.py`).

---

## Stage 2 — Async Audit
### Current Architecture Analysis
- Async Playwright and async queue exist, but prompt pipeline previously used blocking `queue.Queue` and sync adapter method.

### Detected Problems
- Blocking queue call (`queue.get(block=True)`) in orchestration layer.
- Missing `task_done()` semantics.

### Risk Assessment
- Event-loop stalls, WebSocket starvation, and deadlocks under load.

### Refactor Proposal
- Use `asyncio.Queue`; make adapter contract async.

### Minimal Patch Plan
- Replace blocking queue with `asyncio.Queue` and convert public methods to async.

### Targeted Code Changes
- Done in `backend/orchestration/prompt_pipeline.py`.

---

## Stage 3 — Browser Automation Audit
### Current Architecture Analysis
- `ManagedBrowserSession` cleanly isolates context/page per session.
- `SessionManager` owns lifecycle and reconnect.

### Detected Problems
- No bounded reconnect/backoff policy.
- No explicit stale-page recovery hooks beyond manual reconnect.

### Risk Assessment
- Browser instability can cascade under CDP disconnects.

### Refactor Proposal
- Add retry/backoff wrapper around `connect`/`restart_context` and expose health metrics.

### Minimal Patch Plan
- Add configurable reconnect attempts + jittered backoff in a small follow-up patch.

### Targeted Code Changes
- No code changes in this stage (analysis only).

---

## Stage 4 — Provider Isolation Audit
### Current Architecture Analysis
- Qwen and DeepSeek adapters are separated but structurally near-duplicate.

### Detected Problems
- Duplicate markdown/code extraction logic.
- Repeated error classification patterns.

### Risk Assessment
- Drift and subtle cross-provider bugs when only one adapter gets fixes.

### Refactor Proposal
- Extract shared response parsing + common error categories to provider base helpers while preserving selector isolation.

### Minimal Patch Plan
- Introduce small utility module for parsing; migrate both adapters with no behavior change.

### Targeted Code Changes
- No code changes in this stage.

---

## Stage 5 — Config Audit
### Current Architecture Analysis
- Several hardcoded constants (CDP url, retry delays, selectors) inside classes.

### Detected Problems
- Inline operational config with code.
- No single config source for timeouts/retries.

### Risk Assessment
- Unsafe prod tuning and inconsistent runtime behavior.

### Refactor Proposal
- Centralize runtime config dataclasses (timeouts, retry, queue limits, cdp).

### Minimal Patch Plan
- Create `backend/config/runtime.py`; thread config into constructors.

### Targeted Code Changes
- No code changes in this stage.

---

## Stage 6 — Patch Safety Audit
### Current Architecture Analysis
- Patching pipeline exists (`backend/patching/*`) with diff generation path.

### Detected Problems
- Need explicit pre-apply validation and rollback strategy documented per write path.

### Risk Assessment
- Corrupt patches can overwrite content if apply pipeline is used naively.

### Refactor Proposal
- Enforce dry-run diff check + checksum of original text before apply.

### Minimal Patch Plan
- Add guard function in patch utils and wire into pipeline.

### Targeted Code Changes
- No code changes in this stage.

---

## Stage 7 — Queue Audit
### Current Architecture Analysis
- Per-session worker queue is good for isolation.

### Detected Problems
- Unbounded per-session queue (`asyncio.Queue()` default maxsize=0).
- Worker lifecycle not garbage-collected for idle sessions.

### Risk Assessment
- Memory growth and starvation during bursts.

### Refactor Proposal
- Add configurable queue maxsize and idle worker cleanup.

### Minimal Patch Plan
- Add `maxsize` and session idle timeout; emit backpressure events.

### Targeted Code Changes
- No code changes in this stage.

---

## Stage 8 — Dependency Audit
### Current Architecture Analysis
- Compact dependency surface (Playwright, pydantic).

### Detected Problems
- Parallel/duplicated base abstractions indicate architectural dependency ambiguity.

### Risk Assessment
- Wrong imports and accidental circular dependency growth.

### Refactor Proposal
- Establish canonical interfaces and import lint checks.

### Minimal Patch Plan
- Add import contract tests + remove deprecated interface file in controlled migration.

### Targeted Code Changes
- No code changes in this stage.

---

## Stage 9 — Security Audit
### Current Architecture Analysis
- CDP client does not handle credentials itself (good).

### Detected Problems
- Hardcoded CDP endpoint may expose accidental remote target use if overridden unsafely.
- No visible sanitization policy for logs/errors in adapters.

### Risk Assessment
- Leakage of prompt content/tokens in logs.

### Refactor Proposal
- Add explicit safe logging utilities and redact policy.

### Minimal Patch Plan
- Introduce `security/logging.py` with redaction helper; adopt incrementally.

### Targeted Code Changes
- No code changes in this stage.

---

## Stage 10 — Maintainability Audit
### Current Architecture Analysis
- Good early modularization, but duplicates and mixed sync/async contracts reduce clarity.

### Detected Problems
- SOLID pressure points: duplicated responsibilities in providers and queue abstractions.
- Missing contract unification.

### Risk Assessment
- Future scaling increases bug rate and onboarding cost.

### Refactor Proposal
- Incremental convergence roadmap, no giant rewrite.

### Minimal Patch Plan
- Phase A: async correctness + interface de-dup.
- Phase B: provider shared utilities + centralized config.
- Phase C: queue backpressure + browser reconnect resilience.

### Targeted Code Changes
- Async prompt pipeline fix delivered in this patch.

---

## Critical Issues (P1)
1. Blocking sync queue in orchestration prompt pipeline (fixed in this patch).
2. Unbounded queue growth risk in per-session queue.
3. Missing reconnect policy/backoff in browser orchestration.

## Medium Issues (P2)
1. Duplicate queue base abstractions with same class name.
2. Provider duplication in response parsing and error mapping.
3. Inline config constants.

## Migration Strategy (Patch-by-Patch)
1. ✅ Async prompt pipeline stabilization (this patch).
2. Queue interface consolidation with compatibility alias.
3. Queue maxsize + backpressure.
4. Browser reconnect retry policy.
5. Provider shared parsing helper.
6. Central runtime config module.
7. Patch apply precondition/rollback guards.
8. Security redaction utility rollout.
