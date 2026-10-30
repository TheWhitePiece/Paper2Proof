# Local worker

Run `python -m services.worker.main` from the repository root. `--once` processes
one queued job. API and worker must use the same `P2P_DATA_DIR`.

The development worker persists jobs/events in SQLite, allows one active job,
renews a 30-second lease every five seconds, handles cancellation, and cleans
explicitly deleted workspaces. It processes bounded PDF extraction, labeled offline
generation previews, and fixed reviewed engineering fixtures. Generated code is
never executed by this worker's local fixture path.

PostgreSQL/Redis/RQ and real Modal job-ID reconciliation remain release work.
Interrupted local jobs are marked failed rather than automatically duplicated.
