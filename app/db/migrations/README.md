Alembic migrations are included to match the assignment requirement ("SQLAlchemy models, migrations").

For fast local demo runs, the app also calls `Base.metadata.create_all()` on startup.

If you want to run migrations explicitly:

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```

