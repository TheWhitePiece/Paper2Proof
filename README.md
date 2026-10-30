# Paper2Proof

Claim-level experimental verification of research papers. The **single-owner offline
workspace** now supports source review, approved specifications, durable jobs, staged
code previews, and measured engineering fixtures. Live Meta inference, Modal execution
and a real-paper reproduction remain pending. No API keys or credits are required for
the local workflow.

## Run locally

Requires Python 3.11+ and Node.js 20.9+ with npm. Install locked dependencies once:

```powershell
.\scripts\setup.ps1
```

The setup preserves an existing `.env`. Defaults are `P2P_PROVIDER=offline`,
`P2P_RUNNER=disabled`, and `P2P_DATA_DIR=data`. Package installation needs internet;
using the offline workflow does not call a model or cloud compute service.

Start three terminals from the repository root:

```powershell
# API
.\.venv\Scripts\python.exe -m uvicorn services.api.main:create_app --factory --host 127.0.0.1 --port 8000
```

```powershell
# Separate worker: required for PDF extraction and experiment jobs
.\.venv\Scripts\python.exe -m services.worker.main
```

```powershell
# Dashboard
npm.cmd --prefix apps/web run dev
```

Open <http://127.0.0.1:3000>. Read the local access code from **`data/access-code.txt`**
locally and use it to sign in. Do not share or commit that file. This is local
single-owner authentication; the application is not ready for public hosting.
API documentation is at <http://127.0.0.1:8000/docs>.

Choose **Use demonstration PDF** to try the full offline flow. Select a passage,
save a claim, review the JSON specification, explicitly set a target and rationale,
then approve the saved version. Stage an offline code preview or run the reviewed
engineering fixture, inspect events/results, and download the evidence ZIP.

On Linux/macOS use `python3 -m venv .venv`, `.venv/bin/python` instead of the Windows
Python path, and `npm` instead of `npm.cmd`. Linux acceptance remains unverified.
If PowerShell blocks scripts, install manually:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
npm.cmd --prefix apps/web ci
```

## What works offline

- PDF byte/page validation, immutable hashes, page/span/bounding-box provenance,
  bounded parser processes, and clear rejection of unsupported inputs.
- Manual source-linked claims, settings with origins/rationales, missing-information
  gates, immutable specification versions, and exact-hash approval.
- SQLite development persistence, a separate worker, renewable leases, idempotent
  start requests, queue caps, persisted events/SSE, and cancellation.
- Provider-neutral extraction/planning/generation contracts and bounded code repairs.
  The UI preview uses a labeled fixture template and never executes generated code.
- A deterministic 128x32 numerical fixture, independently calculated measurements,
  full iterate checks, negative cases, and repeatable evidence.
- Authenticated local access, artifact integrity checks, bounded ZIP export excluding
  PDFs/credentials, and deletion with immediate access revocation plus worker cleanup.

This does not claim full SRS acceptance. SQLite/local leases are a development
profile; PostgreSQL/Redis, deployment security, backups/retention, actual Meta calls,
isolated generated-code execution and real-paper comparability still need validation.
Detailed limits and commands: [offline workflow](docs/offline-workflow.md).

## How paper-to-code generation works

PDF source spans → cited claim → proposed experiment → human review and frozen
specification → Meta-generated `src/solver.py` → isolated execution → trusted
measurements and evidence. Repairs can fix implementation defects, but cannot change
the accepted target, data, seeds or evaluator. See the
[generation design](docs/offline-workflow.md#how-live-code-generation-will-work).

The current code preview is **not Meta inference**. The current numerical run uses
the fixed reviewed solver, **not staged/generated code**, and is **not a paper reproduction**.

## Standalone engineering fixture

```powershell
.\.venv\Scripts\python.exe -m paper2proof.cli fixture
.\.venv\Scripts\python.exe -m paper2proof.cli fixture --case wrong_update
.\.venv\Scripts\python.exe -m paper2proof.cli fixture --case missing_setting
```

The CLI prints an evidence directory under ignored `artifacts/`. Use that path with
`python -m paper2proof.cli verify <directory>` or `rerun <directory>`.
[Fixture contract and limits](docs/offline-experiments.md).

## Validation

```powershell
.\scripts\check.ps1
```

The browser test is `npm.cmd --prefix apps/web run test:e2e`; it requires Chrome
and the three services using `data/e2e` as the API/worker data directory.
[Validation record](docs/development-validation.md).

## Credentials later

Put future keys in the ignored root `.env`. Keep offline/disabled modes until the
live adapters and sandbox policy are implemented and tested. Adding credentials
alone neither activates a service nor completes the integration. Never put keys in
browser variables, source files, logs or evidence exports.

## Project map

| Path | Responsibility |
|---|---|
| `apps/web` | Source review, approval, job progress and evidence UI |
| `services/api`, `services/worker` | Local authenticated API and durable worker |
| `paper2proof/pdf`, `review.py`, `schemas` | Provenance and reviewed experiment contracts |
| `paper2proof/agents`, `providers` | Bounded model-facing contracts and offline previews |
| `paper2proof/runner`, `evaluation`, `artifacts` | Reviewed fixture execution and trusted evidence |
| `paper2proof/store.py`, `workspace.py`, `auth.py` | Local persistence, lifecycle and sessions |
| `tests`, `apps/web/tests/e2e` | Backend and browser verification |
| `data/`, `artifacts/` | Private local state; Git ignores both |

See [pending steps](docs/pending-steps.md), [SRS acceptance](docs/acceptance.md),
[hackathon alignment](docs/hackathon-alignment.md), [build plan](docs/Paper2Proof_Codex_Build_Plan.md),
[SRS text](docs/Paper2Proof_SRS_v1.txt), [third-party inventory](THIRD_PARTY_NOTICES.md),
and [contribution record](HACKATHON_CONTRIBUTIONS.md).
