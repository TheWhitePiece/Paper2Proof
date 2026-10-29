# Pending implementation and deferred setup

Updated 29 October 2026. Owner instruction: skip step #2/account-credit/API work,
skip repository creation because it exists, set up the coding environment and start
the build plan. This pass implements prompt 1's offline foundation only. The plan's
original text is preserved; this file records the authorized adjustment.

## Completed coding foundation

- [x] Inspect existing repository, build plan, and SRS; preserve original files/license.
- [x] Create project-local Python environment and Python/TypeScript structure.
- [x] FastAPI skeleton, health/status, structured errors and request IDs.
- [x] Pydantic settings, secret-free example and ignored local `.env`.
- [x] Provider contracts and explicitly labeled offline fixture responses.
- [x] Next.js frontend skeleton with actual backend connectivity.
- [x] Dependency locks, local check/setup commands and foundation tests.
- [x] AT-01 through AT-17 tracked without claiming release acceptance.
- [x] Upstream reference inventory and contribution disclosure.

## Deferred by request: accounts, APIs and repository creation

- [ ] Build-plan section 2: account setup, credit applications/status checks,
  endpoint selection, billing/access validation. Owner will supply credentials later.
- [ ] Implement one real Meta-model provider after access/provider selection;
  check actual SDK and structured-output capabilities, usage, retry and pricing semantics.
- [ ] Implement separate opt-in model and Modal smoke-test scripts. Deferred with
  API code, rather than publishing untested SDK calls or calling services now.
- [ ] Install/integrate Modal and verify an actual sandbox run; record real job IDs.
- [ ] Test isolation/resources: network denial, secret absence, filesystem isolation,
  timeout, cancellation, memory/output limits, evaluator protection; document SRS deviations.
- Repository initialization/creation: **skipped — already exists**.
- Public-repository visibility check and publishing: deferred to release; no commits,
  pushes, repository creation, account changes or credit applications done by this pass.

## Next coding milestones (no credits required to start)

1. **Trusted experiment path (prompt 2, offline portion):** deterministic synthetic
   128x32 linear system; reviewed solver contract; independent metric/fidelity checks;
   bounded numeric JSON; hash-linked reports and negative fixtures. Engineering data,
   not a paper reproduction. Modal portion remains deferred.
2. **PDF, claims and specs (prompt 3):** bounded PyMuPDF processing with page/span/bbox
   provenance and immutable hashes; source validation; typed claims; versioned frozen
   specs; setting origins, blockers and adapted-mode rules. Fixture/manual claims can
   develop the interface; live extraction requires the deferred provider.
3. **Persistence and worker:** PostgreSQL models/migrations for projects, papers,
   spans, claims, specs, runs, attempts, measurements, artifacts, events and usage;
   Redis/RQ delivery; idempotency, leases and restart reconciliation. Neither Docker
   nor database/Redis services were installed in this pass.
4. **Selective prompt adaptation (prompt 4):** inspect pinned Paper2Code revision;
   audit before copying; pure prompt functions; generated-file path/type/size checks.
5. **Autonomy and verdicts (prompt 5):** durable state transitions; immutable attempts;
   at most three repairs; time/call/token/cost reservations; frozen acceptance rules;
   uncertainty outcomes; distinguish execution failures from scientific assessments.
6. **Workflow and export (prompt 6):** upload/source view/spec review/progress/report;
   cancellation; ownership/authentication; safe ZIP/hash manifest; clean rerun;
   deletion, retention, backup and recovery.
7. **Real demo and submission (prompt 7):** choose/pin a feasible sourced numerical
   claim and PDF; inspect rights and settings; actual model plus sandbox evidence;
   fault/missing-information demo; full acceptance/performance/security checks;
   license inventory, recording and submission checklist.

## Known limits

Configured budgets are validated defaults, not enforced runtime accounting yet.
Enums are contracts, not a persisted state machine. `/health` proves API liveness
only. No DB, queue, worker, PDF parser, authentication, sandbox or live inference is
present. Adding `.env` credentials alone does not complete those integrations.
No full SRS acceptance test passes solely because foundation tests pass.
