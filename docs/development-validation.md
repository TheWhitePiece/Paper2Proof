# Development foundation validation

Validated 29 October 2026 on the existing Windows workspace with Python 3.11.7,
Node.js 20.10.0, and npm 10.9.0. All results below concern the foundation only.

| Check | Command / evidence | Result |
|---|---|---|
| Python installation | Project `.venv`; `pip install -e '.[dev]'` | Passed |
| Dependency consistency | `.venv/Scripts/python.exe -m pip check` | No broken requirements |
| Editable setup using installed build tools | `pip install --no-deps --no-build-isolation -e .` | Passed |
| Python lint | `.venv/Scripts/python.exe -m ruff check .` | Passed |
| Python format | `.venv/Scripts/python.exe -m ruff format --check .` | 11 files already formatted |
| Foundation tests | `.venv/Scripts/python.exe -m pytest` | 12 passed |
| Real local backend startup | Uvicorn app factory, loopback port 8000 | Passed |
| Real local HTTP health/status | `GET /api/v1/health`, `GET /api/v1/status` | Healthy; offline provider; runner disabled; integration flags false |
| Frontend dependency install | `npm install --no-fund`, generated `package-lock.json` | Passed; npm reported 0 vulnerabilities at installation |
| TypeScript | `npm run typecheck` | Passed |
| Frontend production build | `npm run build` | Passed; `/` and `/_not-found` prerendered |
| Built frontend and API proxy | `GET http://127.0.0.1:3000/` and `/api/v1/status` | HTTP 200; expected heading/pending labels; proxy returns offline status |
| Setup/check script syntax | PowerShell AST parser | Both scripts parse successfully |
| SRS preservation | Extracted requirement IDs and exact plan-copy byte comparison | FR-01 through FR-39, AT-01 through AT-17 preserved; 17 acceptance rows |
| Secret exclusion | `git check-ignore .env .venv apps/web/node_modules` | All ignored |
| SRS acceptance | `docs/acceptance.md` | All 17 not run |

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
