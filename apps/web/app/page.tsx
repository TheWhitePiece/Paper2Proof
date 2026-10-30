"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Span = { id: string; page: number; bbox: number[]; text: string };
type Paper = { id: string; state: string; error?: string; sha256: string; pages: number; spans: Span[]; warnings: string[] };
type Claim = { id: string; statement: string; span_id: string; quote: string; version: number };
type Setting = { value: string | number | null; origin: string; rationale: string };
type Review = { mode: "adapted" | "direct"; target_relative_error: number | null; target_rationale: string; settings: Record<string, Setting>; assumptions: string[] };
type Spec = Review & { id: string; spec_hash: string; version: number; blockers: string[] };
type Result = { assessment?: string; scientific_verdict?: null; is_fixture?: boolean; execution_performed?: boolean; measurements?: { seed: number; relative_solution_error: number; relative_residual: number }[]; limitations?: string[] };
type Job = { id: string; kind: string; state: string; spec_id: string; error: string | null; result: Result | null };
type Event = { sequence: number; stage: string; message: string };

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, { cache: "no-store", ...options });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "The local API is unavailable." }));
    throw new Error(error.message || "Request failed");
  }
  return response.json();
}
const post = (body: unknown): RequestInit => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export default function Home() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [paper, setPaper] = useState<Paper | null>(null);
  const [page, setPage] = useState(1);
  const [span, setSpan] = useState<Span | null>(null);
  const [statement, setStatement] = useState("");
  const [reported, setReported] = useState("");
  const [method, setMethod] = useState("unknown");
  const [claims, setClaims] = useState<Claim[]>([]);
  const [claim, setClaim] = useState<Claim | null>(null);
  const [specs, setSpecs] = useState<Spec[]>([]);
  const [spec, setSpec] = useState<Spec | null>(null);
  const [reviewText, setReviewText] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [connected, setConnected] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [accessCode, setAccessCode] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const keys = useRef(new Map<string, string>());

  const refresh = useCallback(async () => {
    try {
      const session = await api<{ authenticated: boolean }>("/session");
      setAuthenticated(session.authenticated); setConnected(true);
      if (!session.authenticated) return;
      const data = await api<{ papers: Paper[]; jobs: Job[] }>("/workspace");
      setPapers(data.papers); setJobs(data.jobs); setConnected(true);
    } catch { setConnected(false); }
  }, []);
  useEffect(() => { void refresh(); const timer = setInterval(() => void refresh(), 2500); return () => clearInterval(timer); }, [refresh]);
  useEffect(() => {
    if (!selectedJob) return;
    const latest = jobs.find(job => job.id === selectedJob.id);
    if (latest) setSelectedJob(latest);
    void api<Event[]>(`/jobs/${selectedJob.id}/events`).then(setEvents).catch(() => {});
  // The job list changes only on polling; selection is handled separately below.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobs]);

  async function action(task: () => Promise<void>) {
    setBusy(true); setError("");
    try { await task(); await refresh(); } catch (error) { setError(error instanceof Error ? error.message : "Operation failed"); }
    finally { setBusy(false); }
  }
  async function openPaper(id: string) {
    let item = await api<Paper>(`/papers/${id}`);
    for (let attempt = 0; item.state === "queued" && attempt < 60; attempt++) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      item = await api<Paper>(`/papers/${id}`);
    }
    if (item.state === "rejected") throw new Error(item.error || "PDF extraction failed.");
    if (item.state !== "ready") throw new Error("PDF is still queued. Start the worker and select this saved paper again.");
    setPaper(item); setPage(1); setSpan(null); setStatement(""); setReported(""); setMethod("unknown"); setConfirmDelete(false);
    setClaim(null); setSpec(null); setSpecs([]); setReviewText(""); setAccepted(false);
    setClaims(await api<Claim[]>(`/papers/${id}/claims`));
  }
  async function openClaim(item: Claim) {
    setClaim(item); setAccepted(false); setSpec(null);
    const history = await api<Spec[]>(`/claims/${item.id}/specs`);
    setSpecs(history);
    const draft = await api<Review>("/review-defaults");
    setReviewText(JSON.stringify(draft, null, 2));
  }
  function openSpec(item: Spec) {
    setSpec(item); setAccepted(false); setDirty(false);
    setReviewText(JSON.stringify({ mode: item.mode, target_relative_error: item.target_relative_error,
      target_rationale: item.target_rationale, settings: item.settings, assumptions: item.assumptions }, null, 2));
  }
  async function saveReview() {
    if (!claim) return;
    const draft = JSON.parse(reviewText) as Review;
    const item = spec
      ? await api<Spec>(`/specs/${spec.id}/versions`, { ...post(draft), headers: { "Content-Type": "application/json", "If-Match": spec.spec_hash } })
      : await api<Spec>(`/claims/${claim.id}/specs`, post(draft));
    openSpec(item); setSpecs(await api<Spec[]>(`/claims/${claim.id}/specs`));
  }
  async function start(kind: string) {
    if (!spec || !accepted || dirty) return;
    await api(`/specs/${spec.id}/approve`, post({ spec_hash: spec.spec_hash, accepted: true }));
    const lookup = `${spec.id}:${kind}`;
    const key = keys.current.get(lookup) || crypto.randomUUID(); keys.current.set(lookup, key);
    const job = await api<Job>(`/specs/${spec.id}/jobs`, { ...post({ kind, spec_hash: spec.spec_hash }), headers: { "Content-Type": "application/json", "Idempotency-Key": key } });
    keys.current.delete(lookup); setSelectedJob(job); setCode("");
    setEvents(await api<Event[]>(`/jobs/${job.id}/events`));
  }
  async function exportJob() {
    if (!selectedJob) return;
    const response = await fetch(`/api/v1/jobs/${selectedJob.id}/export`, { method: "POST" });
    if (!response.ok) { const body = await response.json(); throw new Error(body.message || "Export failed"); }
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a"); link.href = url; link.download = `paper2proof-${selectedJob.id}.zip`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const currentSpans = paper?.spans.filter(item => item.page === page) || [];
  const running = selectedJob && ["queued", "running"].includes(selectedJob.state);

  if (!authenticated) return <main><header><a className="brand" href="/">Paper2Proof</a><span className="tag">{connected ? "Local API connected" : "Start the local API"}</span></header>
    <section className="intro compact"><p className="eyebrow">PRIVATE LOCAL WORKSPACE</p><h1>Open your research workspace.</h1><p className="lede">Use the local access code created when the backend first starts. No online account is needed.</p></section>
    <section className="panel"><p>Find <code>access-code.txt</code> in your configured data directory (default: <code>data/</code>). Keep it private.</p>
      {error && <p className="error" role="alert">{error}</p>}
      <form onSubmit={event => { event.preventDefault(); void action(async () => { await api("/session", post({ access_code: accessCode })); setAccessCode(""); setAuthenticated(true); }); }}>
        <label>Local access code<input type="password" autoComplete="current-password" value={accessCode} onChange={event => setAccessCode(event.target.value)} /></label>
        <button disabled={busy || !accessCode}>Sign in</button>
      </form></section></main>;

  return <main>
    <header><a className="brand" href="/">Paper2Proof<span> / research workspace</span></a><span className="tag">{connected ? "Local API connected" : "Start the local API"}</span><button className="secondary" onClick={() => void action(async () => { await api("/session", { method: "DELETE" }); setAuthenticated(false); setPaper(null); setSelectedJob(null); setPapers([]); setJobs([]); })}>Sign out</button></header>
    <section className="intro compact"><p className="eyebrow">FROM CLAIM TO EVIDENCE</p><h1>Inspect the source.<br />Define the experiment.</h1><p className="lede">An offline workspace for reviewing claims and testing the evidence pipeline. Meta inference and sandboxed code execution are pending.</p></section>
    {error && <div className="error" role="alert">{error}</div>}
    {busy && <p role="status">Working… PDF extraction requires the separate worker to be running.</p>}
    <div className="notice">Single-user local mode. Claims are entered by you. Code previews use a labeled fixture template; they are never executed. Numerical runs use only the reviewed engineering solver.</div>

    <section className="panel" aria-labelledby="paper-heading">
      <div className="section-heading"><h2 id="paper-heading">01 / Paper & source passage</h2><span>Text PDFs · up to 25 MiB / 50 pages</span></div>
      <p className="hint">No paper content is sent to a model in offline mode. Once enabled, relevant passages will be sent to your configured provider.</p>
      <div className="toolbar"><label className="upload">Upload PDF<input type="file" accept="application/pdf" disabled={busy} onChange={event => {
        const file = event.target.files?.[0]; event.target.value = ""; if (!file) return;
        void action(async () => { if (file.size > 25 * 1024 * 1024) throw new Error("PDF exceeds 25 MiB.");
          const item = await api<Paper>("/papers", { method: "POST", headers: { "Content-Type": "application/pdf" }, body: file }); await openPaper(item.id); });
      }} /></label><button className="secondary" disabled={busy} onClick={() => void action(async () => { const item = await api<Paper>("/demo-paper", { method: "POST" }); await openPaper(item.id); })}>Use demonstration PDF</button>
      <select aria-label="Saved paper" value={paper?.id || ""} onChange={event => void action(() => openPaper(event.target.value))}><option value="" disabled>Saved papers</option>{papers.map(item => <option key={item.id} value={item.id}>{item.id.slice(0, 8)} · {item.pages ? `${item.pages} page(s)` : item.state}</option>)}</select></div>
      {paper && <><p className="digest">PDF SHA-256: {paper.sha256}</p><div className="toolbar"><button className="secondary" onClick={() => setConfirmDelete(true)}>Delete paper</button>{confirmDelete && <><span className="warnings">Delete this paper, its claims, jobs and evidence?</span><button onClick={() => void action(async () => { await api(`/papers/${paper.id}`, { method: "DELETE" }); setPaper(null); setClaim(null); setClaims([]); setSpec(null); setSpecs([]); setSpan(null); setSelectedJob(null); setConfirmDelete(false); })}>Confirm delete</button><button className="secondary" onClick={() => setConfirmDelete(false)}>Keep paper</button></>}</div><div className="warnings">{paper.warnings.map(warning => <p key={warning}>{warning}</p>)}</div>
        <div className="source-grid"><div><label>Source page<select value={page} onChange={event => { setPage(Number(event.target.value)); setSpan(null); }}>{Array.from({ length: paper.pages }, (_, i) => <option key={i} value={i + 1}>Page {i + 1}</option>)}</select></label>
          <div className="passages">{currentSpans.map(item => <button className={`passage ${span?.id === item.id ? "selected" : ""}`} key={item.id} onClick={() => { setSpan(item); setStatement(item.text); }}><small>{item.id}</small>{item.text}</button>)}</div>
        </div><div><a href={`/api/v1/papers/${paper.id}/pdf#page=${page}`} target="_blank" rel="noreferrer">Open original PDF at page {page} ↗</a><iframe key={`${paper.id}-${page}`} title="Original source PDF" src={`/api/v1/papers/${paper.id}/pdf#page=${page}`} /></div></div>
      </>}
    </section>

    <section className="panel" aria-labelledby="claim-heading"><div className="section-heading"><h2 id="claim-heading">02 / Select a measurable claim</h2><span>Manual review · no AI extraction yet</span></div>
      {span ? <><blockquote>{span.text}</blockquote><p className="hint">Page {span.page}; bounding box {span.bbox.map(v => v.toFixed(1)).join(", ")}. The quotation is validated against the stored span.</p>
        <label>Claim statement<textarea value={statement} onChange={event => setStatement(event.target.value)} /></label>
        <div className="fields"><label>Reported value, if present<input type="number" step="any" value={reported} onChange={event => setReported(event.target.value)} placeholder="Unknown" /></label>
        <label>Method supported by this passage<select value={method} onChange={event => setMethod(event.target.value)}><option value="unknown">Unknown / needs information</option><option value="randomized_kaczmarz">Randomized Kaczmarz</option></select></label></div>
        <p className="hint">Current supported metric: relative L2 solution error, a dimensionless ratio; smaller is better. Other claims remain out of scope.</p>
        <button disabled={busy || statement.length < 5} onClick={() => void action(async () => {
          if (!paper || !span) return;
          const item = await api<Claim>(`/papers/${paper.id}/claims`, post({ statement, span_id: span.id, quote: span.text, metric: "relative_l2_solution_error", method, reported_value: reported === "" ? null : Number(reported) }));
          setClaims(await api<Claim[]>(`/papers/${paper.id}/claims`)); await openClaim(item);
        })}>Save sourced claim</button></> : <p className="empty">Choose a passage from the PDF above.</p>}
      <div className="cards">{claims.map(item => <button key={item.id} className={`choice ${claim?.id === item.id ? "selected" : ""}`} onClick={() => void action(() => openClaim(item))}>{item.statement}<small>User-provided · version {item.version}</small></button>)}</div>
    </section>

    <section className="panel" aria-labelledby="spec-heading"><div className="section-heading"><h2 id="spec-heading">03 / Review & freeze the specification</h2><span>Adapted experiments only</span></div>
      {claim ? <><p>Review every assumption. Supply <code>target_relative_error</code> and a <code>target_rationale</code> before approval. Defaults are engineering choices, not facts extracted from the paper.</p>
        <label>Experiment specification (JSON)<textarea className="json-editor" spellCheck={false} value={reviewText} onChange={event => { setReviewText(event.target.value); setAccepted(false); setDirty(true); }} /></label>
        <button disabled={busy} onClick={() => void action(saveReview)}>{spec ? "Save as a new version" : "Save specification"}</button>
        <div className="toolbar">{specs.map(item => <button className="secondary" key={item.id} onClick={() => openSpec(item)}>Version {item.version} · {item.id.slice(0, 6)}</button>)}</div>
        {spec && <><p className="digest">Frozen specification: {spec.spec_hash}</p>{spec.blockers.length > 0 ? <ul className="warnings">{spec.blockers.map(item => <li key={item}>{item}</li>)}</ul> : <p>Ready for your approval. New edits require a new saved version.</p>}
          {dirty && <p className="warnings">Save your changes as a new version before approval.</p>}
          <label className="check"><input type="checkbox" checked={accepted} disabled={busy || dirty || spec.blockers.length > 0} onChange={event => setAccepted(event.target.checked)} />I approve this saved version and its adapted-data assumptions.</label>
          <div className="toolbar"><button disabled={busy || !accepted} onClick={() => void action(() => start("generation_preview"))}>Stage offline code preview</button><button className="secondary" disabled={busy || !accepted} onClick={() => void action(() => start("engineering_fixture"))}>Run reviewed engineering fixture</button></div>
          <p className="hint">The preview does not execute code. The fixture tests synthetic data and cannot reproduce the selected paper claim.</p></>}
      </> : <p className="empty">Save or select a claim to review the experiment settings.</p>}
    </section>

    <section className="panel" aria-labelledby="jobs-heading"><div className="section-heading"><h2 id="jobs-heading">04 / Progress & evidence</h2><span>Persisted local events · updates every 2.5 seconds</span></div>
      <p className="hint">Queued jobs require the separate worker. Start it using the worker command in the README.</p>
      <div className="cards">{jobs.map(job => <button key={job.id} className={`choice ${selectedJob?.id === job.id ? "selected" : ""}`} onClick={() => void action(async () => { setSelectedJob(job); setCode(""); setEvents(await api<Event[]>(`/jobs/${job.id}/events`)); })}>{job.kind.replaceAll("_", " ")}<small>{job.state.replaceAll("_", " ")} · {job.id.slice(0, 8)}</small></button>)}</div>
      {selectedJob && <><h3>{selectedJob.state.replaceAll("_", " ")}</h3>{selectedJob.error && <p className="error">{selectedJob.error}</p>}
        <ol className="events">{events.map(item => <li key={item.sequence}><strong>{item.stage}</strong> — {item.message}</li>)}</ol>
        {selectedJob.result && <><p><strong>{selectedJob.result.assessment || (selectedJob.kind === "extract_pdf" ? "Source text extracted." : selectedJob.kind === "generation_preview" && selectedJob.state === "awaiting_sandbox" ? "Code staged; awaiting a verified sandbox." : "No complete assessment.")}</strong></p><p className="hint">Engineering evidence only. No scientific verdict or paper reproduction.</p>
          {selectedJob.result.measurements && <div className="table-scroll"><table><thead><tr><th>Seed</th><th>Relative solution error</th><th>Relative residual</th></tr></thead><tbody>{selectedJob.result.measurements.map(row => <tr key={row.seed}><td>{row.seed}</td><td>{row.relative_solution_error.toPrecision(6)}</td><td>{row.relative_residual.toPrecision(6)}</td></tr>)}</tbody></table></div>}
          <ul className="hint">{selectedJob.result.limitations?.map(item => <li key={item}>{item}</li>)}</ul>
        </>}
        <div className="toolbar">{running ? <button className="secondary" onClick={() => void action(async () => { await api(`/jobs/${selectedJob.id}/cancel`, { method: "POST" }); })}>Cancel job</button> : selectedJob.kind !== "extract_pdf" && <button disabled={busy} onClick={() => void action(exportJob)}>Download evidence ZIP</button>}
          {selectedJob.kind === "generation_preview" && selectedJob.result && <button className="secondary" disabled={busy} onClick={() => void action(async () => { const response = await fetch(`/api/v1/jobs/${selectedJob.id}/code`); if (!response.ok) throw new Error("Code unavailable"); setCode(await response.text()); })}>Inspect staged code</button>}</div>
        {code && <><p className="notice">OFFLINE FIXTURE TEMPLATE · not Meta-generated · not executed</p><pre className="code-view">{code}</pre></>}
      </>}
      {!jobs.length && <p className="empty">No jobs yet. Review and approve a specification above.</p>}
    </section>
    <footer>Paper2Proof supports experimental investigation. A mismatch does not prove a paper false. Single-owner local workspace; public hosting and generated-code isolation remain pending.</footer>
  </main>;
}
