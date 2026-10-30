# Implementation status and pending work

Updated 30 October 2026. The owner requested completion of the offline workflow
while API/Modal access is pending. Repository creation and account/credit tasks
remain skipped. The original plan and SRS are preserved; these development-profile
decisions are documented rather than treated as full release acceptance.

## Implemented and available locally

- [x] Python/Next.js environment, pinned dependencies, configuration validation,
  ignored secrets/data, setup/check commands and foundation tests.
- [x] Reviewed 128x32 engineering fixture, independent metrics/fidelity checks,
  bounded local execution, negative cases, evidence manifests and exact reruns.
- [x] Durable PDF extraction with size/page/signature/encryption checks, process
  deadline/memory bounds, hashes, page/span/bounding-box provenance and warnings.
- [x] Manual claim entry and correction versions with exact source-quote validation.
- [x] Settings with provenance/rationale, missing-information gates, adapted mode,
  immutable spec versions and exact-hash approval before job creation.
- [x] Original provider-neutral claim/planning/code prompts and typed output
  contracts. Offline generation preview is explicitly labeled and never executed.
- [x] Code/path/dependency validation; bounded repair/call/token/time policies;
  one schema retry; preserved attempts, usage records, diagnostics and diffs.
- [x] Independent equivalence verdict-policy tests for inside/outside/overlap and
  failed gates. Engineering reports still have no scientific verdict.
- [x] SQLite development persistence and separate worker process; one active job,
  five queued jobs, idempotency, renewable leases, events/SSE, cancellation and
  interrupted-job handling without automatic duplicate execution.
- [x] Source viewer, claim entry, specification review/version selection, approval,
  code inspection, real progress/measurements and bounded evidence ZIP download.
- [x] Single-owner local sign-in with hashed credentials/session tokens, cookie
  expiry, browser-origin checks and protected papers/jobs/artifacts/events/exports.
- [x] Explicit paper deletion: immediate access revocation, cancellation, worker
  cleanup of active source/evidence/export files, and a content-free tombstone.
- [x] Backend and browser test suites, commands, acceptance traceability and original
  contribution records. See the validation document for actual run outcomes.

## Deferred accounts and live integrations

- [ ] Owner obtains usable Meta-model access and Modal authentication/credits.
  One inference provider is enough initially; credits are not assumed available.
- [ ] Implement the selected actual provider adapter against its current API/SDK;
  capabilities, bounded retries, structured-output repair and usage/cost reservation.
- [ ] Add and run separate explicit live model and Modal smoke tests. Keys in `.env`
  alone do not activate integration or authorize spend.
- [ ] Implement the Modal sandbox adapter and approved dependency image, then test
  network denial, secret absence, input/evaluator isolation, timeout/cancellation,
  memory/process/disk limits and oversized output. Document SRS profile deviations.
- [ ] Connect actual Meta extraction/planning/generation to human review and isolated
  execution, then evaluate real outputs. Never route generated code to the local solver.
- [ ] Reconcile actual runner job IDs on worker restart and test the full bounded
  implementation-repair loop using real sandbox diagnostics.

## Remaining release work (not all blocked by API access)

- [ ] Choose/pin one real numerical paper and inspect its method, data rights,
  settings and feasibility. The demonstration PDF is a synthetic fixture, not a paper.
- [ ] Build a sourced comparable experiment or explicitly adapted target and validate
  the domain evaluator. Current source matching validates quotations, not claim truth.
- [ ] PostgreSQL schema/migrations and Redis/RQ deployment: SQLite is an explicit local
  development substitute and does not complete DATA-03.
- [ ] Deployed authentication/ownership, TLS/secure cookies, cloud encryption,
  multi-user isolation and public-hosting review. Current identity is one local owner.
- [ ] Automatic retention, backup expiry, restore validation and deletion-tombstone
  replay. Explicit local deletion is implemented; backups are not managed yet.
- [ ] Fresh-machine/Linux rerun and reference-host latency/cancellation/cost/recovery
  benchmarks. Existing checks are Windows development tests, not release SLAs.
- [ ] Final dependency/data/PDF license audit. In particular, PyMuPDF has dual
  AGPL/commercial licensing; preserve an accurate inventory and resolve distribution terms.
- [ ] Full AT-01 through AT-17 release evidence, actual Meta usage records, real-paper
  demo, accessible public repository/product/video links, and submission checks.
- [ ] Record the required three-minute video. The pasted guide supersedes the old
  plan's wording that three minutes was only a recommendation.

## Repository history

The foundation backup was pushed to `origin/main` at `4ed01b2`. The subsequent offline
experiment/workspace milestone is prepared as a separate backup commit; use Git history
for its exact revision and the command outcome for remote-push confirmation.
No new repository, credit application, billing action or live provider call was made.
