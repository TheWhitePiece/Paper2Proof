# Contribution record

## Baseline

The repository, MIT license, build plan and SRS predate this implementation pass.
Their presence does not demonstrate a working application. Repository creation was
explicitly skipped. No upstream Paper2Code code has been imported.

## New work in this pass — 29 October 2026

| Work | Files / demonstration | Commit |
|---|---|---|
| Local environment, dependency definitions/locks, configuration | `pyproject.toml`, `.env.example`, `scripts/` | `4ed01b2` |
| FastAPI foundation, errors, request IDs, status | `services/api`, `/docs`, `/api/v1/status` | `4ed01b2` |
| Provider interface and labeled offline fixtures | `paper2proof/providers`, `tests/test_foundation.py` | `4ed01b2` |
| Next.js development workspace | `apps/web`, local port 3000 | `4ed01b2` |
| SRS traceability, deferred-work list and documentation | `docs/`, `README.md` | `4ed01b2` |

Implemented with Codex assistance. No live inference, sandbox job, real-paper claim,
scientific verdict or release acceptance is claimed. Update this inventory with
actual commit IDs and demo locations when those exist. Hackathon eligibility and
submission requirements remain to be checked; this log does not establish eligibility.

## Offline engineering experiment milestone

New original implementation in the offline workflow milestone (revision in Git history):

- `paper2proof/planning/fixture.py`: deterministic synthetic inputs and row schedules.
- `paper2proof/runner/`: fixed reviewed subprocess solver with bounded output/time.
- `paper2proof/evaluation/linear.py`: independent metrics and iteration fidelity checks.
- `paper2proof/artifacts/`, `experiments.py`, `cli.py`: immutable-at-write evidence,
  integrity verification, frozen-source rerun and lineage.
- `tests/test_experiment.py`: malformed outputs, forged metrics, incorrect methods,
  missing settings, process bounds, evidence tampering and deterministic reruns.
- `docs/offline-experiments.md` and `docs/fixture-validation.json`: commands, limits,
  and actual engineering-fixture measurements, not a paper reproduction.

No additional third-party source or prompts were copied. No live model or Modal
integration is claimed. The local runner is explicitly not a sandbox.

## Offline workspace milestone — 30 October 2026

New original implementation in the offline workflow milestone (revision in Git history):

- Bounded PDF processing and source geometry, original demonstration PDF generator,
  source validation, manual claim versions and approved experiment specifications.
- Provider-neutral extraction/planning/code contracts, original prompts, bounded
  generation/repair, immutable attempts, diagnostic diffs and preserved usage metadata.
- SQLite development persistence, renewable worker leases, idempotency, persisted
  progress/SSE, cancellation, local sessions and deletion lifecycle.
- Full offline dashboard for upload/source review, specification approval, staged
  code inspection, engineering measurements and evidence ZIP export.
- Backend and browser tests for the above, plus documented remaining release gates.

Paths: `paper2proof/pdf`, `agents`, `review.py`, `store.py`, `workspace.py`, `auth.py`,
`services/api/workflow.py`, `services/worker/main.py`, `apps/web/app`, and their tests.
PyMuPDF and Playwright are dependencies, not original implementations. Framework-
generated Next.js guidance is likewise not an original product contribution.

Actual Meta inference, isolated generated-code execution and real-paper reproduction
remain unimplemented/unverified. Offline fixtures must be identified as such in any demo.
