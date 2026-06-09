from app.db.base import Base
from app.db.session import engine


def init_db() -> None:
    # For this take-home we keep it simple: create tables on startup if missing.
    # Alembic is included for production-style migrations, but this makes local/demo runs frictionless.
    Base.metadata.create_all(bind=engine)

