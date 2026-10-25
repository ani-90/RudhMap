# with get_context: how does the pipeline run get triggered and tracked

**Trigger**
- `POST /api/feed/refresh` (`refresh_feed`, `app/api/feed.py:21-52`) is the only live trigger.
- It first applies the cooldown. If the last successful run is recent, it returns `status="skipped"` with the remaining seconds (`feed.py:24-37`).
- Otherwise it generates a `uuid4` `run_id`, calls `crud.create_pipeline_run` and then `update_pipeline_run(status="running")` (`feed.py:47-48`).
- It then queues `_run_pipeline_bg` through `BackgroundTasks` (`feed.py:50`). The HTTP response returns the `run_id` right away.
- `_run_pipeline_bg` (`feed.py:55-58`) awaits `run_pipeline` (`app/pipeline/graph.py:69-83`). That builds the initial state and calls `pipeline.ainvoke`.
- `app/scheduler.py:15-40` (`_daily_refresh`) would trigger a run the same way. It isn't wired into startup, so it never fires.

**Tracking**
- Each run is a `PipelineRun` row (`app/db/models.py:73-85`). Its columns are `run_id`, `status` (queued/running/success/partial/failed), `persisted_count`, `duplicate_count`, `error_log` (JSON), `started_at` and `finished_at`.
- `create_pipeline_run` inserts the row with `status="queued"` (`app/db/crud.py:107-118`). `update_pipeline_run` patches it (`crud.py:121-123`).
- `aggregator_node` computes the final status (`app/pipeline/aggregator.py:14-93`):
  - `success`: no errors.
  - `partial`: errors, but some articles were persisted.
  - `failed`: errors and nothing persisted.
- It writes that status and the counts through `update_pipeline_run` (`aggregator.py:98`).
- If the graph raises, `_run_pipeline_bg` marks the run `failed` and stores the error in `error_log` (`feed.py:59-72`).
- Clients poll `GET /api/feed/status/{run_id}` (`get_run_status`, `feed.py:76-88`). It returns the status, counts, timestamps and parsed errors, or 404 if the run is unknown.
