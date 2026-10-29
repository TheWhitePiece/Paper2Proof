# Worker boundary

Reserved for the Redis/RQ worker and durable run controller. No worker runs yet.
Jobs must persist state in PostgreSQL and reconcile runner IDs before retrying.
Do not execute generated code in FastAPI, an in-memory background task, or a
local subprocess as a substitute for a verified isolated runner.
