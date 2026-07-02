# Alembic migrations

Generate the initial Phase 2 migration once your `DATABASE_URL` points at a
reachable Postgres (Neon):

```bash
cd backend
alembic revision --autogenerate -m "phase 2 initial"
alembic upgrade head
```

`env.py` imports `app.models` so `Base.metadata` sees every table. Tests do NOT
use Alembic — they build the schema with `Base.metadata.create_all` on SQLite
(see `tests/conftest.py`).
