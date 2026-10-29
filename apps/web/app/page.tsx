"use client";

import { useEffect, useState } from "react";

type Status = {
  stage: string;
  provider: string;
  runner: string;
  live_inference_available: boolean;
  sandbox_execution_available: boolean;
  persistence_available: boolean;
  message: string;
};

const stages = [
  ["01", "Paper & provenance", "Upload a text PDF and inspect the exact source passage."],
  ["02", "Claim & specification", "Select a measurable claim and review its assumptions."],
  ["03", "Experiment", "Run a bounded implementation against frozen settings."],
  ["04", "Evidence", "Inspect measurements, limitations, and a reproducible export."],
];

export default function Home() {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function refresh(signal?: AbortSignal) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/v1/status", {
        cache: "no-store", signal: signal
          ? AbortSignal.any([signal, AbortSignal.timeout(5000)])
          : AbortSignal.timeout(5000),
      });
      if (!response.ok) throw new Error("API unavailable");
      const data = await response.json();
      if (data.stage !== "foundation" || typeof data.provider !== "string"
        || typeof data.runner !== "string" || typeof data.message !== "string"
        || typeof data.live_inference_available !== "boolean"
        || typeof data.sandbox_execution_available !== "boolean"
        || typeof data.persistence_available !== "boolean") {
        throw new Error("Unexpected API response");
      }
      setStatus(data);
    } catch {
      if (signal?.aborted) return;
      setStatus(null);
      setError("The local API is unavailable. Start the backend and check again.");
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal);
    return () => controller.abort();
  }, []);

  return (
    <main>
      <header><a className="brand" href="/">Paper2Proof<span> / research workspace</span></a><span className="tag">Local development</span></header>
      <section className="intro">
        <p className="eyebrow">FROM CLAIM TO EVIDENCE</p>
        <h1>What does the<br />experiment show?</h1>
        <p className="lede">Trace a research claim to its source, define the test, and inspect the evidence. The application foundation is ready for development.</p>
      </section>
      <section className="status-panel" aria-labelledby="status-heading">
        <div><p className="eyebrow">WORKSPACE STATUS</p><h2 id="status-heading">{loading ? "Checking local API…" : status ? "API connected" : "API not connected"}</h2></div>
        <button onClick={() => void refresh()} disabled={loading}>{loading ? "Checking…" : "Check connection"}</button>
        <div className="status-message" role="status" aria-live="polite">
          {error || status?.message || "Waiting for the local backend."}
        </div>
        {status && <dl>
          <div><dt>Configured provider</dt><dd>{status.provider}</dd></div>
          <div><dt>Live inference</dt><dd>{status.live_inference_available ? "Available" : "Pending"}</dd></div>
          <div><dt>Sandbox execution</dt><dd>{status.sandbox_execution_available ? "Available" : "Pending"}</dd></div>
          <div><dt>Saved experiments</dt><dd>{status.persistence_available ? "Available" : "Pending"}</dd></div>
        </dl>}
      </section>
      <section aria-labelledby="workflow-heading">
        <div className="section-heading"><h2 id="workflow-heading">The verification workflow</h2><span>Planned · not available yet</span></div>
        <ol className="workflow">{stages.map(([number, title, description]) => <li key={number}><span className="step">{number}</span><h3>{title}</h3><p>{description}</p><span className="pending">Pending implementation</span></li>)}</ol>
      </section>
      <footer>No paper has been evaluated. Development fixtures are not scientific results.</footer>
    </main>
  );
}
