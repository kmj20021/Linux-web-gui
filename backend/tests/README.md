# Backend pytest suite

Run the maintained suite from the project root:

```text
python -m pytest backend/tests
```

The suite forces `DATABASE_URL` to an in-memory SQLite database before importing
the application. It must not use Docker, repository-tracked databases, real
users, or operational credentials.

The output-oriented scripts currently under `backend/test/` are legacy
diagnostics and are intentionally outside pytest discovery. A later,
separately-owned cleanup task can classify them under `backend/test/legacy/`
after equivalent assertions have been migrated here. QA-01 does not move,
delete, or modify those scripts.
