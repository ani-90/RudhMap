# without get_context: how does the pipeline run get triggered and tracked

**Trigger**
- A client calls `POST /api/feed/refresh` (`app/api/feed.py:20`).
- The handler first checks a 2-hour cooldown against the last successful run (`feed.py:27-42`, `_REFRESH_COOLDOWN_SECONDS` at `feed.py:17`). If the cooldown is active, it returns `status="skipped"` and doesn't start a run.
- Otherwise it generates a UUID `run_id` (`feed.py:45`) and adds `_run_pipeline_bg` as a FastAPI `BackgroundTask` (`feed.py:50`). The pipeline therefore runs in the same process after the HTTP response is sent.
- The response returns `status="running"` with the `run_id` (`feed.py:52`).
- `app/scheduler.py:27` also creates runs, but CLAUDE.md says it isn't wired into startup.

**Tracking**
- A `PipelineRun` row is the record of each run. `crud.create_pipeline_run` inserts it (`app/db/crud.py:107`), and the handler then sets `status="running"` (`feed.py:47-48`). The model is at `app/db/models.py:73`.
- `_run_pipeline_bg` calls `run_pipeline` (`feed.py:55-58`, defined at `app/pipeline/graph.py:69`).
- The aggregator updates the row when it finishes (`app/pipeline/aggregator.py:98`). Per CLAUDE.md, that update sets status (success, partial or failed), the persisted and duplicate counts, and the error log.
- If `run_pipeline` raises, `_run_pipeline_bg` catches it and marks the run `failed`. It stores the error in `error_log` and sets `finished_at` (`feed.py:59-70`).
- `crud.update_pipeline_run` (`crud.py:121`) does the updates.

**Polling**
- `GET /api/feed/status/{run_id}` reads the row via `crud.get_pipeline_run` (`feed.py:75-88`). It returns the status, the persisted and duplicate counts, the start and finish times, and the parsed errors. It returns 404 if the run doesn't exist.
- The Flutter client polls this endpoint, since there are no websockets.
