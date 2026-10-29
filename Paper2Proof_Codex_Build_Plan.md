# Paper2Proof — Codex build plan and SRS implementation addendum

Prepared 29 October 2026. Planning document, not an implemented or validated application.

Read alongside `Paper2Proof_SRS_v1.docx`. This document narrows the hackathon delivery, records architectural changes, and supplies staged instructions for Codex. The original SRS remains the full product specification; any unmet requirement must be disclosed rather than marked complete.

## 1. The decision

Build a claim-level experimental verification tool for one small numerical-algorithm paper first. A user uploads a PDF, selects a sourced claim, reviews an experiment specification, runs generated Python in an isolated environment, and receives measurements with downloadable evidence.

Use Meta models for claim extraction, planning, implementation, and bounded repairs. Use ordinary deterministic code for validation, metric calculation, and verdict rules. Use Modal for experiment execution. Start with one inference provider; add another only after the complete workflow works.

This is an agent application using existing models. Training or fine-tuning a new foundation model is not required for this MVP. Codex can help build the application while the application itself calls Meta models at runtime.

The demonstration should answer: “What exactly did this paper claim, what conditions did we test, and what does the execution evidence show?”

## 2. What to do first — today

1. **Finish Modal setup and its credit application.** Create an account, record the exact workspace name and account email, and select Sandboxes as the primary use. Do not select GPU training or fine-tuning unless you actually plan to do it.
2. **Check credit status in provider dashboards.** Submitted applications are not approved credits. Record each provider as pending, approved, redeemed, or usable. Do not assume a rate-limit grant is a spending credit.
3. **Choose one working Meta-model endpoint.** Prefer the Meta Model API when your access and billing are ready. Baseten is a suitable alternative if its hackathon access arrives first. Do not integrate three providers on day one.
4. **Create a public `paper2proof` repository.** Add a README, `.gitignore`, `.env.example`, this plan under `docs/`, a readable requirements checklist, and `HACKATHON_CONTRIBUTIONS.md`. Keep real keys and uploaded PDFs outside Git.
5. **Run two smoke tests:** one small Meta-model response and one isolated Modal Python command. Record success or the real error; mocks are not proof of integration.
6. **Build an experiment without an LLM first:** fixed inputs → sandbox solver → trusted numeric evaluator → saved report. This establishes the evidence path before adding autonomous generation.
7. **Then add paper extraction and model-driven code generation.** Do not spend the first day on a polished dashboard.

End-of-day target: a real sandbox run with a saved numeric result, plus a working model call or an explicitly documented access blocker.

### Credit-application notes

Suggested Modal one-liner:

> Paper2Proof turns research-paper claims into executable experiments and evidence-backed reproducibility reports.

Suggested Modal use-case text:

> We are building Paper2Proof, an AI research engineer that uses Meta models to extract experimental claims and generate Python implementations. We will use Modal Sandboxes to execute small numerical experiments with time and resource limits, capture logs and outputs, and rerun bounded repairs. A separate evaluator will compare observed measurements with a frozen experiment specification and produce a downloadable reproducibility package.

Choose an honest compute estimate. `$50–100` is a reasonable planning envelope if that is your intended total; it is not a measured requirement or a guarantee that credits will be granted. Leave account-specific fields for your actual details.

The pasted Modal guide and form disagree: the guide says “first 1,000 participants,” while the form says selected teams and not first-come. Treat approval as conditional and follow the application instructions; ask the organizers if eligibility affects your submission. Baseten credits in the guide are individual; do not pool them contrary to its terms.

If all credits remain pending, continue with local unit tests and a fake provider for development, prominently labeled. Real sandbox execution and real Meta inference are still required before claiming the integrated demo works. Any paid calls depend on your own configured billing authorization.

## 3. Scope and product requirements

### Required hackathon slice

| Capability | Minimum implementation | Evidence of completion |
|---|---|---|
| Paper input | Text PDF, size/page limits, immutable PDF hash | Valid PDF succeeds; corrupt, encrypted and unsupported scans get clear errors |
| Provenance | Page, text span and bounding box linked to each claim | Clicking a citation opens the actual source passage |
| Claim selection | One measurable claim selected per run | Claim includes metric, unit, direction, reported value where present, and source |
| Specification | Dataset/generator, baseline, parameters, seeds, metric, tolerance and assumptions | Versioned JSON approved before execution |
| Code generation | Meta-generated implementation for one supported experiment interface | Model and prompt versions, code digest and generation events saved |
| Execution | Disposable isolated job, bounded time/resources, explicit network policy | Real job ID, exit reason, logs and output artifacts |
| Repair | Up to three repairs after the initial attempt | Every attempt retained; no editing evaluator or acceptance criteria |
| Evaluation | Trusted metric calculation plus method-fidelity checks | Incorrect implementation and forged “success” output cannot pass |
| Report | Outcome, measurements, uncertainty, deviations and limitations | Report numbers reconcile with stored measurements |
| Export and rerun | Code, dependencies, configuration, logs, metrics, hashes and rerun instructions | Fresh rerun reproduces a deterministic fixture |
| Hackathon disclosure | Public repo and explicit upstream/new-work inventory | Reviewers can identify event-built features |

Keep a second paper optional. A missing-information case can come from the same paper. Deliberately removing a required setting is a labeled test fixture, not evidence that the real paper omitted it.

Exclude from this deadline: arbitrary scientific disciplines, OCR, large GPU training, self-hosting large models, fine-tuning, automatic web dataset discovery, importing arbitrary repositories through the UI, and continuous scheduled paper verification.

### Verdict policy

Store execution state separately from scientific outcome. A crash is an execution failure, not a failed scientific claim.

- `reproduced_within_tolerance`: declared checks pass under sufficiently comparable conditions.
- `not_reproduced_in_this_run`: a valid comparable run falls outside the predeclared acceptance rule.
- `inconclusive`: missing information, insufficient trials, failed fidelity checks, or ambiguous comparisons prevent a supported conclusion.

For adapted experiments, display `experiment_mode=adapted` and report whether the adapted target was met; do not display an unqualified reproduction of the original claim. Do not infer that a paper is false from one mismatch. Finite experiments also do not prove a mathematical theorem.

Freeze the tolerance, seed list, stopping rules and aggregation method before execution. A change creates a new specification and run, preserving the old evidence. For stochastic claims, use repeated trials and a declared uncertainty rule; overlap with an acceptance boundary is inconclusive under the SRS policy.

## 4. Architecture and providers

| Component | Initial choice | Responsibility |
|---|---|---|
| Dashboard | Next.js | Upload, source viewer, spec review, progress, report and export |
| API | FastAPI + Pydantic | Validation, ownership, run creation and artifact access |
| Durable state | PostgreSQL | Papers, claims, spec versions, attempts, verdicts and events |
| Job execution control | Redis + RQ, one worker initially | Durable jobs, cancellation, retry reconciliation and concurrency limits |
| PDF parser | PyMuPDF | Source text, page positions and document hashes |
| Reasoning/code generation | Meta model through one provider adapter | Structured extraction, implementation and repair proposals |
| Experiment runtime | Modal Sandbox | Run generated code without application credentials |
| Evaluator | Separate trusted Python module/process | Validate bounded data outputs and compute metrics |
| Artifacts | Private local storage during development; private object storage for deployment | Immutable per-attempt files, controlled access and exports |

Use an explicit state machine before introducing a general agent framework. No vector database is necessary for a short-paper MVP. Long jobs must not depend on FastAPI request lifetime or in-memory background tasks.

Suggested modules: `apps/web`, `services/api`, `services/worker`, `paper2proof/schemas`, `paper2proof/providers`, `paper2proof/pdf`, `paper2proof/planning`, `paper2proof/runner`, `paper2proof/evaluation`, `paper2proof/artifacts`, `tests`, `docs`.

Persist at least: `Paper`, `SourceSpan`, `Claim`, `ExperimentSpecVersion`, `Run`, `Attempt`, `Measurement`, `Artifact`, `Event`, and `UsageRecord`. Each verdict links to a spec hash, code hash, input hash, evaluator version, and actual attempt. Duplicate run-start requests must share an idempotency key.

### Provider configuration

| Provider | Base URL | Model selection | When to use |
|---|---|---|---|
| Meta | `https://api.meta.ai/v1` | Current quickstart uses `muse-spark-1.3`; keep configurable | Default when access is usable |
| Baseten | `https://inference.baseten.co/v1` | Participant guide explicitly specifies `meta-models/muse-spark-open-1026` | Alternative when your hackathon account is enabled |
| Fireworks | `https://api.fireworks.ai/inference/v1` | Copy an available Meta-model identifier from your account; do not guess a slug | Later adapter if needed |
| Modal | SDK sandbox API | No inference model needed for execution | Experiment compute |

The API bases are documented in the providers’ quickstarts [S2, S5, S6]. The special Baseten slug comes from your supplied participant guide, not a verified call to your account. Model access, credentials, credits and live compatibility have not been tested here.

The adapter should expose structured generation and usage accounting, with a capability map for JSON schema, tool calling, reasoning options and token limits. OpenAI-compatible APIs are not identical in every parameter. Validate returned JSON with Pydantic and allow bounded schema repair. Do not silently change providers midway through a run.

Use application environment variables such as `P2P_PROVIDER`, `P2P_MODEL`, `P2P_BASE_URL`, and the relevant secret variable. Keep keys server-side. Store provider/model/usage in the evidence, but redact secrets and avoid publishing private prompt contents. Unknown cost is unknown, not zero.

### Minimal setup sequence

Commands below assume Bash on Linux, macOS, or WSL; adapt activation for other shells.

```bash
mkdir paper2proof
cd paper2proof
git init
python3 -m venv .venv
source .venv/bin/activate
python -m pip install openai modal python-dotenv pydantic
modal setup
modal token info
```

These are smoke-test dependencies, not the final lockfile. After the smoke tests, resolve and lock application dependencies and commit those locks. Use your existing Codex environment; no change to Codex’s own model configuration is needed to build an app that calls Meta.

Create `.gitignore` before adding files: exclude `.env`, `.venv/`, credentials, local PDFs, datasets, run artifacts, caches and the reference checkout. Commit only a secret-free `.env.example`. Load local secrets using `python-dotenv` or your environment, and never print their values.

Example Meta smoke test, based on its documented Responses API [S2]:

```python
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.environ["MODEL_API_KEY"],
    base_url="https://api.meta.ai/v1",
    timeout=30.0,
    max_retries=0,
)
response = client.responses.create(
    model=os.getenv("P2P_MODEL", "muse-spark-1.3"),
    input="Reply with the single word READY.",
    max_output_tokens=128,
)
print(response.output_text)
```

This is a proposed smoke test, not a completed API check. For another provider, use its supported endpoint and settings rather than only changing the URL. A reasoning model may need a higher output budget.

Example Modal smoke test [S3, S4]:

```python
import modal

app = modal.App.lookup("paper2proof-smoke", create_if_missing=True)
sb = modal.Sandbox.create(
    "python", "-c", "print(2 + 2)",
    app=app,
    image=modal.Image.debian_slim(python_version="3.11"),
    cpu=(0.5, 1.0),
    memory=(256, 512),
    timeout=60,
    block_network=True,
)
try:
    print(sb.stdout.read())
    sb.wait()
    assert sb.poll() == 0
finally:
    sb.terminate()
```

Expected output is `4`. This checks connectivity and basic execution; it does not validate every security or resource requirement. Build an approved dependency image before creating network-blocked experiment jobs. Do not let generated code install packages at runtime.

## 5. How to use Paper2Code

Repository: https://github.com/going-doer/Paper2Code

Inspected commit: `ba9169978043d5799c8d4f4a0963e6b66a24c2e1`.

I inspected the actual scripts and license at that revision. I did not execute its model calls or reproduce its benchmark results. Its public repository uses the Apache 2.0 license. Preserve its license, copyright notices, any applicable notices, and mark modifications when distributing adapted code. Record the source commit and copied files. This is attribution guidance, not a guarantee of hackathon eligibility; the event separately requires clear disclosure of original contributions.

Use a separate reference checkout:

```bash
git clone https://github.com/going-doer/Paper2Code.git ../Paper2Code-reference
git -C ../Paper2Code-reference checkout ba9169978043d5799c8d4f4a0963e6b66a24c2e1
```

Do not run its default pipeline as the Paper2Proof starting point. `scripts/run.sh` uses an OpenAI model and a Transformer example; it runs preprocessing, planning, analysis and coding, but does not run a complete experiment in that script. The repository also has debugging and evaluation components, so “we added execution” alone is an insufficient differentiation claim.

| Upstream file | Useful material | Paper2Proof treatment |
|---|---|---|
| `codes/1_planning.py` | Planning prompts, file/task breakdown | Adapt prompt logic into pure functions over a selected claim and frozen spec; replace direct OpenAI setup |
| `codes/2_analyzing.py` | Dependency-aware implementation analysis | Use selectively for a small implementation; do not generate a whole repository unnecessarily |
| `codes/3_coding.py` | Ordered file generation | Adapt bounded generation; validate file paths, schema, size and allowed file types before writing |
| `codes/4_debugging.py` | Repair proposals from failed code and logs | Reimplement safe bounded repairs; retain attempts and reject ambiguous/out-of-scope patches |
| `codes/0_pdf_process.py` | JSON cleanup | Do not use as canonical parser: it removes citation/equation/reference metadata needed for provenance |
| `codes/1.1_extract_config.py` | Config extraction concept | Replace positional conversation parsing and regex extraction with typed structured output |
| `codes/1.2_rag_config.py` | Dataset/model lookup ideas | Defer; use explicit versioned dataset manifests instead of automatic name substitution |
| `codes/3.1_coding_sh.py` | Generated shell launcher | Skip for the MVP; use a fixed reviewed runner entrypoint |
| `codes/eval.py` | Model-based implementation assessment | Optional advisory review only; never the authority for empirical verdicts |
| `codes/utils.py` | Logging and token-cost helpers | Replace pricing assumptions and add provider-aware usage records |
| `*_llm.py` and vLLM setup | Self-hosted model paths | Skip for the hosted-inference MVP |

The planning/coding scripts contain command-line and client initialization at module scope. Do not directly import them into FastAPI. Extract only the specific logic you use, preserve attribution, and put it behind your own tested interfaces. Remove assumptions such as “the authors released no code” unless supported by the source.

Generated paths must remain under the attempt directory after resolution. Reject absolute paths, traversal, symlinks and unsupported extensions. A model’s proposed patch cannot edit the evaluator, runner policy, dataset manifest, tolerance or prior attempts.

Do not blindly install upstream `requirements.txt`: it includes self-hosting dependencies such as vLLM and Transformers that are unnecessary for this hosted approach.

Create `THIRD_PARTY_NOTICES.md` with columns: upstream URL, commit, license, copied files, adaptations, and purpose. Initially say “reference only” if no code has been copied. Keep `HACKATHON_CONTRIBUTIONS.md` separate, listing actual event-built features with commits and demo locations. Do not count untouched upstream code as new work.

## 6. First experiment and trusted evaluation

Candidate paper: **A randomized Kaczmarz algorithm with exponential convergence**, Thomas Strohmer and Roman Vershynin, arXiv:math/0702226 [S8]. Its linear-system solver is a plausible CPU-first candidate. Pin the exact PDF version and inspect its numerical section before committing to a replication target. The title and abstract alone do not define a complete experiment.

Start with an engineering fixture: a deterministic synthetic overdetermined system, for example a 128×32 matrix with a known solution. These dimensions are our proposed development settings, not attributed to the paper. Use this fixture to test the pipeline, then implement a precisely sourced numerical experiment from the selected PDF. If original settings exceed budget or are missing, label the adapted run clearly.

The first candidate’s acceptance gate:

1. A real numerical claim or figure is identified with page and passage.
2. Dataset generation, metric and baseline can be specified without invented details.
3. A reference implementation finishes within the execution budget.
4. An evaluator can compute the relevant measure from bounded outputs independently.
5. All unresolved assumptions are recorded before the run. If no suitable claim meets this gate, choose another small numerical paper before integrating its generation prompts.

For solver experiments, generated code can return iterate vectors or final vectors in a fixed numeric format. The evaluator computes residual/error against its own frozen input data; a printed “accuracy” or “passed” string is never evidence. Reject non-finite values, unexpected shapes, missing trials and oversized data. Do not load pickles, run exported scripts, or import generated modules in the trusted evaluator process.

Method fidelity also matters: a direct solver could return the right answer while violating the claimed iterative algorithm. Use reviewed update-rule/reference checks and check iteration traces where possible. These checks are necessary but not a proof against every adversarial implementation; report their coverage. A model’s favorable code review cannot replace them.

Prefer an error-versus-iteration experiment initially. Runtime claims require equivalent work, warmups, repeated runs and controlled timing; cloud startup and queue delay must not be counted as algorithm runtime. Never choose or modify a claim just to obtain an impressive green badge.

Prepare three demo/test cases: a valid measured run; an implementation deliberately using the wrong update rule; and a missing-setting case. Label deliberately injected faults. The wrong implementation must not pass merely because its output prints the target metric.

## 7. Runner, cost and evidence requirements

Start with one active sandbox. Treat each attempt as immutable and run it in a fresh sandbox. The controller owns credentials and policy; generated code receives only the approved inputs and specification.

Modal permits outbound access by default, so explicitly use `block_network=True` [S4]. Do not inject provider secrets, attach application volumes, or expose inbound ports. Export only allowlisted bounded artifacts. Separate dependency-image preparation from execution of untrusted code.

Carry forward the SRS limits: 180 seconds per invocation, 15 minutes per run, at most 20 model calls, initial estimated model budget of $2, at most three repair attempts, 10 MiB logs and 100 MiB exported artifacts. The model budget excludes compute; track both separately. Before a model call, reserve its maximum configured estimated cost where pricing is known. Without usable pricing, require an explicit token/call cap rather than reporting monetary enforcement as complete.

For Modal, configure resource limits explicitly using request/limit pairs, and record units: its CPU setting uses physical cores. A scalar request alone is not a hard cap [S3, S4]. Begin with a conservative profile and measure the reference experiment before increasing it.

**SRS deviation requiring an explicit decision:** Modal does not automatically implement the SRS’s exact 1 GiB writable-disk, 128-process, rootless-container and dedicated-VM profile. Application output limits are not disk quotas. Either implement and test equivalent enforceable limits where supported, or document a revised runner profile and its limitations. Do not claim the original sandbox acceptance tests pass merely because Modal is enabled.

Add tests for outbound access, secret absence, filesystem isolation, timeout, cancellation, memory exhaustion, oversized output, and evaluator tampering. Distinguish provider-enforced protections from application monitoring. Public arbitrary-code uploads must not be enabled while required isolation controls remain unverified.

The verifier should consume bounded typed data in a separate trust boundary. The generator can receive diagnostic errors for repairs, but cannot alter acceptance criteria or rewrite old evidence to improve the outcome. Limit repairs to implementation defects, not target-driven parameter tuning.

Export: selected claim and source references, spec and assumptions, generated source, dependency lock/image identity, dataset source or generator and seed, per-attempt logs, validated numeric outputs, measurements, verdict rationale, versions, SHA-256 manifest, and rerun instructions. Do not redistribute a paper or dataset without the needed rights. Hashes provide integrity links, not proof that all measurements are scientifically valid.

## 8. Dated implementation schedule

The supplied guide sets submission at **4 November 2026, 9:00 PM Eastern Time**. That is **5 November, 02:00 UTC / 07:30 India Standard Time**. Set an internal target of 4 November evening IST to leave upload and submission time. The schedule below assumes a focused solo build from 29 October; move work forward if something is already done.

| Date | Work | Exit condition |
|---|---|---|
| Oct 29 | Accounts, repo, attribution, provider smoke tests, fixed experiment runner and evaluator | Real numeric artifact plus a real Meta call, or clearly recorded access blocker |
| Oct 30 | PDF spans, claim schema, selected claim and versioned experiment spec | Claim citation resolves; missing settings cannot silently become facts |
| Oct 31 | Adapt planning/code prompts, integrate provider, sandbox execution and bounded repair | One sourced claim goes from spec to code to saved execution evidence |
| Nov 1 | Trusted evaluator, method checks, seeds/uncertainty, negative cases and budgets | Incorrect code and fabricated target values cannot pass |
| Nov 2 | Dashboard, event progress, cancellation, export and clean rerun | One complete user journey; export works outside the original run directory |
| Nov 3 | Recovery, access controls, security checks, disclosure, real-paper rehearsal | Acceptance checklist records pass/fail/blocked; no fabricated completed checks |
| Nov 4 | Fix blockers, record short demo, README, public-repo check, submit | Submitted artifact and accessible links; second paper only if everything else is ready |

If behind: remove the second paper, extra provider adapters, custom UI animation and live code editing first. Preserve provenance, actual execution, trusted metrics, isolation, an honest uncertainty outcome, and export. A local single-user demonstration may be feasible before a public multi-user service; disclose any unimplemented ownership, deletion, recovery or performance requirements from the SRS.

The guide’s Oct 30 Fireworks session is at noon ET (21:30 IST). Attend if useful, but it should not block the core implementation. The last full day for support is Nov 3 according to the supplied schedule.

## 9. SRS implementation addendum and traceability

| Addendum | Existing SRS area | Implementation decision / acceptance gate |
|---|---|---|
| A01 | Scope and rollout | One supported numerical experiment first; second paper optional; unsupported papers get an explicit scope result |
| A02 | FR-01–08; AT-01–02 | Own provenance-preserving PDF parser; every selected citation validated against stored spans |
| A03 | FR-09–16; AT-03–04 | Spec versions freeze settings, assumptions and tolerances; adapted mode cannot imply exact reproduction |
| A04 | FR-17–20; AT-05 | Refactor selected upstream prompts into provider-neutral functions; bounded immutable repairs |
| A05 | FR-21–24; SEC-02–05 | Modal runner replaces dedicated-VM proposal only with a documented, tested resource/isolation profile |
| A06 | FR-25–32; AT-08–10 | Deterministic metrics plus fidelity checks; generation and verdict authority separated |
| A07 | FR-33–38; AT-11 | Evidence bundle includes provenance, manifest and clean rerun; no fabricated outputs |
| A08 | OR-01–03; AT-07,13 | Durable queue, idempotency and reconciliation of Modal job IDs after restart |
| A09 | DATA; SEC-01; AT-14 | Ownership and deletion gates before multi-user hosting; local demo limitations explicit |
| A10 | NFR-06; AT-16 | Provider-aware token/call/cost accounting; compute tracked separately; unknown price not zero |
| A11 | LIC-01–03; AT-17 | Pinned upstream provenance and event contribution log; no claim that licensed reuse alone proves eligibility |
| A12 | Delivery plan | Replace the old ten-day schedule with Oct 29–Nov 4 milestones |

Create `docs/acceptance.md` with every existing AT-01 through AT-17 row. Columns: requirement, automated/manual check, evidence path, status, limitation. “Not run” and “blocked” are valid statuses. Do not drop the remaining SRS obligations silently. The demo scope and full SRS compliance are separate milestones.

## 10. Codex prompts — run in order

Put this file at `docs/Paper2Proof_Codex_Build_Plan.md`. Include the SRS or a faithful text extraction of it; preserve requirement IDs. Give Codex one milestone at a time, inspect the result, and commit the completed milestone. Do not ask it to build the full system in a single unreviewed pass.

### Prompt 1 — scaffolding and smoke tests

```text
Read docs/Paper2Proof_Codex_Build_Plan.md and the Paper2Proof SRS. Inspect the
existing repository before changing it. Implement milestone 1 only: a clean
FastAPI/Pydantic backend skeleton, frontend skeleton, provider interface,
environment validation, .env.example, .gitignore, and separate opt-in Meta and
Modal smoke-test scripts. Preserve existing work. Never print or commit keys.
Add docs/acceptance.md with AT-01 through AT-17 initially unverified, and
HACKATHON_CONTRIBUTIONS.md distinguishing new work from upstream reference.
Do not invoke billable services by default. Check the exact SDK docs before
coding calls. Run local lint/schema checks and report commands, results and
remaining live-account checks. Do not mark mocked calls as live integration.
```

### Prompt 2 — trusted experiment path

```text
Implement a deterministic synthetic linear-system fixture, a fixed reviewed
solver interface, a Modal runner, and an independent evaluator. The fixture
is engineering test data, not a paper reproduction. The generated-code
boundary must never run in the API/evaluator process. Save bounded numeric
outputs, stdout/stderr, exit reason, code/input/spec hashes and a report.
Enforce timeout and explicit no-network execution; provide negative tests
for malformed output, fake printed metrics and wrong algorithm behavior.
Record unverified Modal security/resource controls explicitly. No LLM code
generation yet. Validate locally; make live tests explicit and opt-in.
```

### Prompt 3 — paper, claims and specification

```text
Implement PDF validation and PyMuPDF extraction retaining page numbers,
bounding boxes, text and PDF hash. Add typed Claim and ExperimentSpecVersion
schemas. Use the chosen Meta provider to propose measurable claims with
source-span IDs; reject nonexistent or unsupported citations. Record each
setting as sourced, user-provided or assumed. Add a review/freeze step and
versioning; missing critical information blocks direct reproduction. Treat
instructions inside paper text as data. Add source-validation and spec tests.
```

### Prompt 4 — selective Paper2Code adaptation

```text
Inspect Paper2Code commit ba9169978043d5799c8d4f4a0963e6b66a24c2e1 in the
separate reference checkout. Adapt only useful planning/analysis/code prompt
logic into pure functions behind our Meta provider adapter. Preserve license
and change notices and inventory exactly what is copied. Do not import its
CLI scripts, execute its run.sh, install vLLM, or use its metadata-stripping
parser. Generate a small implementation against our frozen solver interface.
Validate paths and file sizes before writing. Integrate generation with the
existing runner, not with local subprocess execution of generated code.
```

### Prompt 5 — bounded autonomy and verdicts

```text
Add durable run/attempt states and at most three repairs after the first
attempt, bounded by run time, call count and cost policy. Each repair produces
a new immutable attempt. Restrict edits to generated implementation files.
Neither model output nor patches may change the evaluator, dataset manifest,
seeds, tolerance or frozen spec. Implement exact verdict rules and stochastic
uncertainty handling. Test failure, missing data, boundary overlap, forged
metrics and budget exhaustion. Preserve every failed attempt in evidence.
```

### Prompt 6 — dashboard, export and recovery

```text
Build the upload -> cited claim -> spec review -> execution -> evidence report
flow. Show real persisted events and actual numeric results. Add cancellation,
idempotent run creation, worker restart reconciliation and owner-scoped artifact
access. Export a bounded ZIP with manifest and rerun instructions; reject unsafe
paths. Test a clean rerun, report/measurement agreement and unauthorized access.
Keep execution failures distinct from scientific verdicts. Update acceptance
evidence and explicitly list requirements that remain unimplemented.
```

### Prompt 7 — real demo and submission

```text
Use the selected versioned research PDF to choose one genuinely sourced
numerical experiment. Check feasibility and comparability before executing.
Run the supported workflow using actual Meta inference and sandbox execution
when account access is configured. Save real evidence, not illustrative values.
Add a clearly labeled negative or incomplete fixture. Reconcile the README,
SRS checklist, upstream attribution and hackathon contribution log with what
actually works. Prepare a three-minute demo script and submission checklist.
Never present a cached recording as a fresh live run or an adapted experiment
as exact reproduction. Report blockers plainly.
```

## 11. Demo and submission checklist

Suggested three-minute narrative: show the source claim and why checking it is difficult; review the frozen settings; show Meta generating an implementation; show the actual job and measurements; open logs/code and export; finish with an inconclusive case and an explanation of the original work.

- Public repository opens without your account and contains no secrets.
- New work is identifiable by files, commits and demonstration timestamps.
- Meta-model usage is visible in runtime records; developer tooling alone is not the integration story.
- The claim links to the exact paper version and passage.
- Charts use real measured data; fixtures and prerecorded runs are labeled.
- Export downloads and rerun instructions work from a fresh environment.
- Security controls and unmet SRS requirements are described honestly.
- Demo/submission links work; final form requirements are checked on the CV platform.
- Do not invent judging weights, guaranteed credits or a required video duration absent from the official form. Three minutes is our recommended demonstration length.

## 12. Sources and verification limits

The hackathon rules, partner-credit conditions, dates and Baseten-specific model ID above come from the participant guide and application text you supplied. They have not been independently authenticated against your participant account.

- **S1 — Paper2Code source at inspected revision:** https://github.com/going-doer/Paper2Code/tree/ba9169978043d5799c8d4f4a0963e6b66a24c2e1 — local source inspection of the files named above; license inspected. Specific file links can be formed from this immutable revision.
- **S2 — Meta API quickstart and models:** https://dev.meta.ai/docs/quickstart and https://dev.meta.ai/docs/models — provider URL, API examples and current documented model choice.
- **S3 — Modal setup and SDK:** https://modal.com/docs/guide/getting-started and https://modal.com/docs/reference/modal.Sandbox — authentication/setup and sandbox interfaces.
- **S4 — Modal execution policy:** https://modal.com/docs/guide/sandbox-networking and https://modal.com/docs/guide/sandbox-resources — outbound network default, resource requests/limits and platform disk behavior.
- **S5 — Baseten Chat Completions:** https://docs.baseten.co/reference/inference-api/chat-completions — hosted inference API configuration.
- **S6 — Fireworks quickstart:** https://docs.fireworks.ai/getting-started/quickstart — hosted inference API configuration; choose a Meta model rather than blindly copying the quickstart default.
- **S7 — Meta cookbooks:** https://github.com/meta-models/meta-model-cookbook and https://github.com/meta-models/meta-oss-cookbook — start with API fundamentals, structured outputs and tool calling; self-hosting examples are optional.
- **S8 — Candidate numerical paper:** https://arxiv.org/abs/math/0702226 — paper identity and candidate algorithm. A feasible exact experiment remains a selection gate, not a completed reproduction.

Docs were consulted on 29 October 2026. No private account was opened, no credit application was submitted by this work, and no billable experiment or model call was executed. The code snippets are setup examples to validate in your environment. The plan is ready for implementation; its acceptance checks are not claims that the product already passes them.
