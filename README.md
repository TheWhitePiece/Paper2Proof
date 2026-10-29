# Paper2Proof

Claim-level experimental verification of research papers. This repository is at
the **local development foundation** milestone; no paper has been reproduced.

The existing repository and MIT license are preserved. Account setup, build-plan
section 2 credit tasks, live APIs, and Modal execution are deferred at the owner's
request. No API keys or credits are needed to run this foundation.

## What works now

- FastAPI health/status endpoints and OpenAPI documentation.
- Validated server-side environment settings, structured errors, request IDs.
- Typed provider interface and explicit, schema-validated offline fixtures.
- Next.js/TypeScript workspace showing actual API connectivity and pending features.
- Python and frontend dependency locks, setup/check scripts, local tests.

Upload, claim extraction, experiments, persistence, authentication, and reports are
not implemented yet. The frontend does not fabricate claims or numeric results.

## Local setup (Windows PowerShell)

Requires Python 3.11+ and Node.js 20.9+ with npm. Package installation needs internet;
application startup needs no provider access. Run commands from the repository root.

```powershell
.\scripts\setup.ps1
```

This creates `.venv`, installs locked dependencies, and copies `.env.example` to
`.env` only when it does not already exist. It never overwrites your keys. If your
PowerShell policy blocks scripts, run the individual commands below instead:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
npm.cmd --prefix apps/web ci
```

Defaults work without `.env`; copy the example manually if needed. Start two terminals:

```powershell
# Terminal 1, repository root
.\.venv\Scripts\python.exe -m uvicorn services.api.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2, repository root
npm.cmd --prefix apps/web run dev
```

Open <http://127.0.0.1:3000>. Backend docs are at <http://127.0.0.1:8000/docs>.
The frontend proxies `/api/v1/*` to the local backend. Both development servers
bind to loopback; this is not an authenticated deployment.

On Linux/macOS use `python3 -m venv .venv`, `.venv/bin/python` instead of the Windows
Python path, and `npm` instead of `npm.cmd`. Linux acceptance remains unverified.

## Check the foundation

```powershell
.\scripts\check.ps1
```

These checks use no live model, no sandbox, and no uploaded paper. Recorded results
are in [development validation](docs/development-validation.md).

## Credentials later

Put future credentials in the root `.env`, which Git ignores. Keep
`P2P_PROVIDER=offline` and `P2P_RUNNER=disabled` for now. There are placeholders for
`MODEL_API_KEY`, model/base URL, Modal tokens, and future database/Redis URLs.
Adding credentials does **not** activate an unfinished integration. Live adapters
and opt-in smoke scripts are explicitly pending and must be implemented and checked
against current provider documentation before use. No keys belong in browser variables.

## Project map

| Path | Responsibility |
|---|---|
| `apps/web` | Next.js development workspace |
| `services/api` | FastAPI control plane |
| `services/worker` | Reserved durable worker boundary |
| `paper2proof/config.py` | Environment validation |
| `paper2proof/schemas` | API/provider contracts and distinct state/outcome enums |
| `paper2proof/providers` | Offline provider and future live-provider boundary |
| `tests` | Foundation validation |
| `docs` | Plan, extracted SRS, acceptance and pending work |

Next coding milestone: the deterministic engineering fixture and trusted evaluator;
live sandbox integration stays deferred. Do not execute generated code locally as
a replacement for a verified isolation boundary.

See [pending work](docs/pending-steps.md), [acceptance](docs/acceptance.md),
[build plan](docs/Paper2Proof_Codex_Build_Plan.md), and the
[SRS text](docs/Paper2Proof_SRS_v1.txt). The original DOCX remains authoritative
for layout; text extraction preserves paragraphs, table-cell order, and requirement IDs.

Attribution: [third-party inventory](THIRD_PARTY_NOTICES.md) and
[contribution record](HACKATHON_CONTRIBUTIONS.md).
