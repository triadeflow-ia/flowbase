# Conexão com o Postgres (banco de dados)
# Usa SQLAlchemy para falar com o banco e psycopg3 como driver
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL


def _mask_url(url: str) -> str:
    """Mascara senha na URL para logs."""
    match = re.match(r"(postgresql(?:\+psycopg)?://[^:]+:)([^@]+)(@.+)", url)
    if match:
        return f"{match.group(1)}****{match.group(3)}"
    return "****"


# SQLAlchemy com psycopg3 precisa da URL no formato postgresql+psycopg://
# Se o .env tiver postgresql://, trocamos para o driver correto
_db_url = DATABASE_URL
if _db_url.startswith("postgresql://") and "+" not in _db_url.split("?")[0]:
    _db_url = _db_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(_db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Retorna uma sessão do banco. Usado nos endpoints que precisam ler/escrever."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """
    Testa a conexão com o Postgres e retorna current_database, current_user.
    Usado no startup e em GET /debug/db.
    """
    with engine.connect() as conn:
        r = conn.execute(text("SELECT current_database(), current_user"))
        row = r.fetchone()
        return {"current_database": row[0], "current_user": row[1]}


def get_effective_url_masked() -> str:
    """Retorna a URL efetiva (com driver psycopg) mascarada."""
    return _mask_url(_db_url)


def get_driver_info() -> str:
    """Retorna o driver usado (postgresql+psycopg ou postgresql)."""
    return "postgresql+psycopg" if "+psycopg" in _db_url else "postgresql"
