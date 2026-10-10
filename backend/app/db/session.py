import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool


def get_database_url() -> str | None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        return None
    # SQLAlchemy necesita indicar el driver (psycopg 3)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        return create_engine(url)
    # Una función serverless no mantiene conexiones entre requests: sin pool propio,
    # y sin prepared statements porque el pooler de Supabase (modo transacción) no los admite.
    return create_engine(url, poolclass=NullPool, connect_args={"prepare_threshold": None, "connect_timeout": 5})


def check_database() -> str:
    """Devuelve 'ok', 'no_configurada' o 'error'. Nunca expone el detalle del fallo."""
    url = get_database_url()
    if url is None:
        return "no_configurada"
    try:
        with make_engine(url).connect() as conn:
            conn.execute(text("select 1"))
        return "ok"
    except Exception:
        return "error"


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = get_database_url()
        if url is None:
            raise RuntimeError("DATABASE_URL no está configurada")
        _engine = make_engine(url)
    return _engine


def get_db():
    """Dependencia de FastAPI: una sesión por request."""
    from sqlalchemy.orm import Session

    with Session(get_engine(), expire_on_commit=False) as session:
        yield session
