# Development foundation validation

Validated 29 October 2026 on the existing Windows workspace with Python 3.11.7,
Node.js 20.10.0, and npm 10.9.0. The initial table records foundation checks;
the offline experiment milestone is recorded separately below.

| Check | Command / evidence | Result |
|---|---|---|
| Python installation | Project `.venv`; `pip install -e '.[dev]'` | Passed |
| Dependency consistency | `.venv/Scripts/python.exe -m pip check` | No broken requirements |
| Editable setup using installed build tools | `pip install --no-deps --no-build-isolation -e .` | Passed |
| Python lint | `.venv/Scripts/python.exe -m ruff check .` | Passed |
| Python format | `.venv/Scripts/python.exe -m ruff format --check .` | 11 files already formatted |
| Initial foundation tests | `.venv/Scripts/python.exe -m pytest` | 12 passed before experiment milestone |
| Real local backend startup | Uvicorn app factory, loopback port 8000 | Passed |
| Real local HTTP health/status | `GET /api/v1/health`, `GET /api/v1/status` | Healthy; offline provider; runner disabled; integration flags false |
| Frontend dependency install | `npm install --no-fund`, generated `package-lock.json` | Passed; npm reported 0 vulnerabilities at installation |
| TypeScript | `npm run typecheck` | Passed |
| Frontend production build | `npm run build` | Passed; `/` and `/_not-found` prerendered |
| Built frontend and API proxy | `GET http://127.0.0.1:3000/` and `/api/v1/status` | HTTP 200; expected heading/pending labels; proxy returns offline status |
| Setup/check script syntax | PowerShell AST parser | Both scripts parse successfully |
| SRS preservation | Extracted requirement IDs and exact plan-copy byte comparison | FR-01 through FR-39, AT-01 through AT-17 preserved; 17 acceptance rows |
| Secret exclusion | `git check-ignore .env .venv apps/web/node_modules` | All ignored |
| SRS acceptance | `docs/acceptance.md` | All 17 full checks unverified; partial fixture coverage recorded |

Tests cover offline startup, secret redaction, invalid credentials/configuration,
budget ceiling validation, environment precedence, schema validation, structured
errors, and no silent provider fallback. The installed Starlette test client emits
one deprecation warning for its httpx compatibility path; tests still pass.
Configured limits are not evidence of runtime budget enforcement.

The Python lock captures exact installed versions including build tools. It is
version-pinned, not hash-locked. Cross-platform installation, fresh-machine setup,
browser interaction/accessibility, live providers, database/queue, sandbox isolation,
scientific evaluation, and release performance remain unverified.

Package-registry installation needed elevated tool permission because the sandbox
blocked network access and npm's user-directory installation. No provider API,
credit dashboard, paid inference, or Modal job was invoked. Git's ownership warning
was handled with a per-command `safe.directory` override; global Git config was not changed.

Implementation references consulted: [Next.js installation](https://nextjs.org/docs/pages/getting-started/installation),
[Pydantic settings](https://github.com/pydantic/pydantic-settings/blob/main/docs/index.md).
No live-provider SDK snippets were implemented without validation; those remain deferred.

## Offline experiment milestone validation

- `python -m pytest`: **35 passed**, including all 12 foundation tests. The existing
  Starlette/httpx deprecation warning remains; no test failures.
- `python -m ruff check .`: passed. `python -m ruff format --check .`: 24 files formatted.
- Actual CLI `fixture` calls: reference completed with `fixture_target_met`;
  injected wrong update completed with `inconclusive`/method fidelity failure;
  missing-target case was blocked before process launch with `inconclusive`.
- CLI `verify`: all four resulting evidence directories (three cases and a rerun)
  passed SHA-256/size verification for their 12 recorded files.
- CLI `rerun` into a new directory: inputs and numeric output are byte-identical;
  report records a new attempt ID and its parent.
- Tests cover timeout, bounded output, launch failure, malformed/non-finite/overflowing
  numeric outputs, incorrect traces with perfect final answers, forged success logs,
  missing settings, path traversal, evidence mutation, and rehashed malicious solver code.
- `artifacts/` remains ignored, while `paper2proof/artifacts/` source is tracked by
  changing the ignore rule to root-only `/artifacts/`.

Actual measurements, artifact paths, hashes and case labels are saved in
[`fixture-validation.json`](fixture-validation.json). Full evidence directories are
local and ignored by Git; the CLI regenerates them. No dependencies were added.
Frontend source was unchanged; its build was not repeated for this backend/CLI milestone.

These are reviewed local subprocess experiments, not generated-code sandbox tests.
No model API or Modal call was made. Full SRS acceptance remains unverified; the
traceability table marks only the relevant fixture coverage as partial.

## Offline workspace validation — 30 October 2026

- Full Python suite: **66 passed**, with the existing Starlette/httpx deprecation
  warning. Coverage includes real PDF parsing, source citations, immutable reviews,
  approvals, durable queues, cancellation/recovery, generation contracts and repair
  limits, independent verdict policy, local authentication, exports and deletion.
- Python lint and formatting passed (41 Python files); `pip check` passed.
- After the full run, a locked-file deletion retry was added. Its targeted deletion
  suite passed **3 tests**, including access revocation while cleanup is pending and
  successful removal on retry; lint passed again. The complete suite was not repeated
  for this isolated change.
- `npm run typecheck` and `npm run build` passed after the workspace, sign-in and
  deletion UI changes. Production build used the existing webpack build command.
- Actual Chrome/Playwright browser run against the production frontend and separate
  API/worker: **1 passed**, 49.2 seconds for the scenario. It signed in, extracted the
  demonstration PDF, selected a cited claim, saved a blocked specification, created
  and approved version 2, inspected a staged offline template, ran the reviewed
  numerical fixture, checked three measured errors below 0.01, downloaded a ZIP and
  deleted the paper. No browser JavaScript errors were observed.
- Screenshot inspected at ignored `artifacts/browser-workspace.png`. Source passages,
  approval, progress and measured results render correctly. Chrome's embedded PDF
  viewer is blank in the headless screenshot; native PDF rendering is not validated
  by this test. The authenticated original-PDF endpoint is separately tested.
- The earlier development-server browser attempt exceeded its 120-second overall
  limit while concurrent backend tests were running. The persisted fixture completed;
  the serial production-server test above passed with a 240-second overall allowance.
- Parser dependency PyMuPDF and browser test dependency Playwright were added and
  locks refreshed. Earlier fixture-validation.json is historical evidence; its
  dependency snapshot predates this milestone. Fresh fixture runs use the current lock.

No Meta or Modal calls, provider costs, real-paper reproduction or sandbox isolation
were exercised. SQLite and single-owner local sessions are the development profile.
The remaining production, retention, licensing and release checks are listed in
`pending-steps.md`, including work that does not depend on API credentials.
