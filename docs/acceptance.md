# SRS acceptance checklist

All release checks remain **not run**. Foundation unit tests do not satisfy the
complete end-to-end acceptance conditions. Original wording and requirement IDs
below come from SRS section 15. See `pending-steps.md` for implementation order.

| Test | Acceptance condition | Requirement | Automated/manual check | Evidence path | Status | Limitation |
|---|---|---|---|---|---|---|
| AT-01 | Valid PDF extracts source spans; encrypted, corrupt, and oversized PDFs fail clearly | FR-01–03 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-02 | Every selected claim resolves to a real page and passage; invented citations are rejected | FR-04–08 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-03 | Missing dataset or critical parameter blocks a direct reproduction; adapted run is labeled | FR-09–16 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-04 | Editing a tolerance after a run produces a new version and preserves the previous result | FR-12–14 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-05 | Known import bug is repaired within budget; history retains patch and failure evidence | FR-17–20 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-06 | Infinite loop, memory flood, and oversized output terminate with distinct reason codes | FR-21–23 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-07 | Cancel stops child processes; duplicate Start requests produce one runner job | FR-23–24 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-08 | Wrong algorithm fails reference checks even if it prints the expected target value | FR-25–26 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-09 | Known metric fixtures produce exact numeric results and correct unit interpretation | FR-27–29 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-10 | Inside, outside, and overlapping acceptance-band fixtures produce the specified verdicts | FR-30–32 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-11 | Report values match stored measurements; ZIP hashes validate and rerun reproduces a fixture | FR-33–38 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-12 | Injected HTML or prompt instructions cannot change evaluator policy or execute in UI | FR-39; OR-04 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-13 | Worker restart reconciles active execution without launching a duplicate | OR-01–03 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-14 | Other owner IDs cannot access artifacts; deletion revokes access and schedules removal | DATA; SEC-01 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-15 | Sandbox cannot reach network, secrets, host paths, or evaluator files | SEC-02–05 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-16 | Reference-host latency, cancellation, budget, and recovery checks meet stated targets | NFR-01–12 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
| AT-17 | Distribution includes upstream license, applicable notices, change markers, and inventory | LIC-01–03 | Pending implementation and validation | None | Not run | Full workflow/integration absent |
