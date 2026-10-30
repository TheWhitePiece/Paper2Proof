# SRS acceptance checklist

Updated 30 October 2026. All **full release checks remain unverified**. Partial
coverage below is evidence for the offline development profile, not release acceptance.
Original acceptance conditions and IDs come from SRS section 15.

| Test | Acceptance condition | Requirement | Offline evidence | Status | Remaining limitation |
|---|---|---|---|---|---|
| AT-01 | Valid PDF extracts source spans; encrypted, corrupt, and oversized PDFs fail clearly | FR-01–03 | PDF provenance and invalid-input tests | Partial | Production hostile-input isolation and reference-host validation |
| AT-02 | Every selected claim resolves to a real page and passage; invented citations are rejected | FR-04–08 | Exact quote/span checks and extraction/planning contracts | Partial | Actual Meta extraction and real-paper evaluation |
| AT-03 | Missing dataset or critical parameter blocks a direct reproduction; adapted run is labeled | FR-09–16 | Review blockers, missing-target fixture, adapted labels | Partial | Real dataset/comparability assessment |
| AT-04 | Editing a tolerance after a run produces a new version and preserves the previous result | FR-12–14 | Immutable spec versions and hash approvals | Partial | Complete real-paper run history |
| AT-05 | Known import bug is repaired within budget; history retains patch and failure evidence | FR-17–20 | Bounded repair tests and preserved diffs | Partial | Real model repair using isolated runtime diagnostics |
| AT-06 | Infinite loop, memory flood, and oversized output terminate with distinct reason codes | FR-21–23 | Reviewed worker timeout/output bounds; bounded PDF parser | Partial | Generated-code memory/process/disk isolation |
| AT-07 | Cancel stops child processes; duplicate Start requests produce one runner job | FR-23–24 | Process cancellation and durable idempotency/capacity tests | Partial | Modal cancellation and runner reconciliation |
| AT-08 | Wrong algorithm fails reference checks even if it prints the expected target value | FR-25–26 | Forged log, wrong update and invalid trace tests | Partial | Generated code and real-paper adapter |
| AT-09 | Known metric fixtures produce exact numeric results and correct unit interpretation | FR-27–29 | Independent relative error/residual fixtures | Partial | Other metric adapters and real-paper units |
| AT-10 | Inside, outside, and overlapping acceptance-band fixtures produce the specified verdicts | FR-30–32 | Independent verdict-policy fixtures | Partial | Real uncertainty estimates/comparability gates |
| AT-11 | Report values match stored measurements; ZIP hashes validate and rerun reproduces a fixture | FR-33–38 | Report agreement, ZIP integrity/tamper checks, deterministic CLI rerun | Partial | Fresh-machine and real-paper rerun |
| AT-12 | Injected HTML or prompt instructions cannot change evaluator policy or execute in UI | FR-39; OR-04 | Frozen policy/hash, path/AST guards and escaped React text | Partial | Adversarial live-model and sandbox validation |
| AT-13 | Worker restart reconciles active execution without launching a duplicate | OR-01–03 | Durable queue, renewable leases, interrupted-job tests | Partial | Actual external runner job-ID reconciliation |
| AT-14 | Other owner IDs cannot access artifacts; deletion revokes access and schedules removal | DATA; SEC-01 | Local session expiry, protected artifacts, deletion cleanup tests | Partial | Multi-user ownership, deployment and backup deletion |
| AT-15 | Sandbox cannot reach network, secrets, host paths, or evaluator files | SEC-02–05 | No generated code runs locally | Not run | Modal sandbox implementation and escape tests |
| AT-16 | Reference-host latency, cancellation, budget, and recovery checks meet stated targets | NFR-01–12 | Development budget/cancellation/recovery tests | Partial | Reference-host benchmarks, real usage and costs |
| AT-17 | Distribution includes upstream license, applicable notices, change markers, and inventory | LIC-01–03 | THIRD_PARTY_NOTICES.md and contribution inventory | Partial | Full dependency/data/distribution license audit |

Evidence lives in `tests/test_experiment.py`, `tests/test_workspace.py`, and
`apps/web/tests/e2e/workspace.spec.ts`. Actual outcomes are recorded in
[development-validation.md](development-validation.md); implementation/release
gaps are maintained in [pending-steps.md](pending-steps.md).
