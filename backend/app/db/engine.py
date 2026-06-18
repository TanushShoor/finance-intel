from sqlmodel import SQLModel, create_engine, Session
from app.config import settings

_engine = None


def make_engine(url: str | None = None):
    return create_engine(url or f"sqlite:///{settings.db_path}",
                         connect_args={"check_same_thread": False})


def init_db(engine=None):
    global _engine
    # Idempotent: an explicit engine (tests) always wins; the FastAPI startup
    # call (engine=None) must NOT clobber an already-configured engine.
    if engine is not None:
        _engine = engine
    elif _engine is None:
        _engine = make_engine()
    SQLModel.metadata.create_all(_engine)
    return _engine


def get_session():
    global _engine
    if _engine is None:
        init_db()
    with Session(_engine) as session:
        yield session
