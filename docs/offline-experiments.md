# Offline experiment milestone

The fixed fixture can now run without any API key, account, Docker service or new
dependency. This is the offline portion of build-plan prompt 2. Modal integration,
network/resource isolation, generated-code execution, and real-paper evaluation
remain deferred. The web dashboard does not launch these jobs yet.

## Run it

From the repository root after the development setup:

```powershell
.\.venv\Scripts\python.exe -m paper2proof.cli fixture
.\.venv\Scripts\python.exe -m paper2proof.cli fixture --case wrong_update
.\.venv\Scripts\python.exe -m paper2proof.cli fixture --case missing_setting
```

Each command prints the path of a new UUID-named directory under ignored
`artifacts/`. Keep the printed path for these commands:

```powershell
.\.venv\Scripts\python.exe -m paper2proof.cli verify artifacts/<attempt-id>
.\.venv\Scripts\python.exe -m paper2proof.cli rerun artifacts/<attempt-id> --output-root artifacts/reruns
```

Replace `<attempt-id>` with the actual ID. `verify` checks bounded file integrity,
not the authenticity or scientific validity of a report. `rerun` verifies input,
code, and dependency snapshots, creates a new attempt, and records parent lineage.
It never imports or executes code supplied by the bundle. Use the matching source
checkout and locked environment; snapshots are byte-sensitive. Cross-platform
floating-point equivalence and a fresh-machine installation remain unverified.

## Experiment specification

| Setting | Engineering policy |
|---|---|
| System | 128 rows by 32 columns, synthetic consistent `A x = b` |
| Input generator | Python `random.Random(2026)`, uniform values in [-1, 1] |
| Reference solution | Generated separately; held by the evaluator |
| Initialization / baseline | Zero vector, relative solution error 1 |
| Row sampling | Row-norm-squared weights; frozen schedules for seeds 7, 23, 41 |
| Update | `x_next = x + ((b_i - dot(a_i, x)) / dot(a_i, a_i)) * a_i` |
| Stop | 512 updates per trial, no target-driven early stopping or repair |
| Metric | `norm(x_final - x_reference) / norm(x_reference)` |
| Additional measurement | `norm(A x_final - b) / norm(b)` |
| Fixture target | Every declared trial has relative solution error <= 0.01 |
| Uncertainty | Descriptive fixed-seed measurements only |
| Local execution limits | 30 seconds; 8 MiB numeric stdout; 64 KiB stderr |

All these settings are our engineering choices. None are attributed to a paper.
The frozen spec includes the target's origin, baseline, metric, stopping rule,
seed list, evaluator version, and invocation timeout. Changing any setting requires
a new spec/run; application writes use exclusive file creation and never overwrite
an earlier attempt. Filesystem owners can still change files; manifest verification
detects byte changes against the recorded manifest, not malicious replacement of
both evidence and manifest.

## Evidence and evaluation

The trusted generator supplies matrix, RHS, and row schedules to the fixed reviewed
worker in a separate Python process. The worker receives an allowlisted environment
and emits JSON iterate vectors. The controller snapshots only the installed reviewed
worker and refuses a replacement file. This path cannot accept arbitrary commands,
code uploads or generated modules.

The evaluator does not import the worker. It parses bounded numeric JSON, rejects
duplicate keys, non-finite/overflowing values, wrong dimensions, unexpected fields,
missing seeds and incomplete traces. It checks zero initialization and every update
against the trusted matrix and declared row schedule before allowing a target match.
It calculates metrics itself. Printed success claims and self-reported metrics
have no authority.

Each attempt contains:

- `spec.json`, `input.json`, reviewed solver/evaluator/generator/contract snapshots,
  and the dependency lock.
- `stdout.json` with the complete numeric trace and `stderr.log` with worker text.
- `execution.json` with supervisor timestamps, wall time, exit code/reason, platform,
  interpreter version, and explicit flags showing no sandbox isolation.
- `report.json` with actual measurements, target, checks, hashes, limitations and lineage.
- `manifest.json` with SHA-256/size records, plus rerun instructions in `README.md`.

## Outcomes

| Case | Expected behavior |
|---|---|
| `reference` | Valid reviewed update; actual metrics determine `fixture_target_met` or `fixture_target_not_met` |
| `wrong_update` | Explicitly injected half-step update plus forged success log; fidelity failure yields `inconclusive` |
| `missing_setting` | Explicitly removed target; execution blocked, no measurements, `inconclusive` |
| Process failure / timeout / oversized output | Failed execution, no assessment and no scientific verdict |

Every report has `experiment_mode=engineering_fixture` and `scientific_verdict=null`.
No engineering target match becomes an unqualified paper-reproduction verdict.

## Remaining boundaries

This subprocess is **not a sandbox**: host files and network are not isolated;
there are no memory, CPU, process-count or filesystem quotas. Only the fixed reviewed
worker may use it. It has no child-process behavior; terminating arbitrary process
trees is unimplemented. Time/output checks here do not satisfy Modal/SRS security
acceptance. The isolated runner must be implemented and tested before generated
code execution is enabled.

Trace fidelity detects the supplied faulty cases; it does not prove that arbitrary
code used the claimed method internally. Hashes are unsigned integrity links.
Application authentication, ownership, persistence, queueing, retries, ZIP export,
statistical verdict rules and real-paper provenance remain future milestones.
