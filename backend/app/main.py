# Servidor principal: FastAPI (expõe os endpoints HTTP)
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import get_env_loaded_path
from app.db import Base, engine, get_db, get_driver_info, get_effective_url_masked, test_connection
from app import models  # Registra as tabelas no Base antes de create_all
from app.models import Job, User
from app.routes_auth import router as auth_router
from app.routes_jobs import router as jobs_router
from sqlalchemy import text

logger = logging.getLogger("uvicorn.error")

# Pasta do frontend (relativa à raiz do projeto)
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ao subir o servidor: cria as tabelas no Postgres e valida a conexão."""
    # Logs de diagnóstico no startup
    env_path = get_env_loaded_path()
    masked_url = get_effective_url_masked()
    driver = get_driver_info()

    logger.info(f"[STARTUP] .env carregado de: {env_path or '(nenhum .env encontrado)'}")
    logger.info(f"[STARTUP] DATABASE_URL (mascarada): {masked_url}")
    logger.info(f"[STARTUP] Driver: {driver}")

    try:
        conn_info = test_connection()
        logger.info(f"[STARTUP] Postgres conectado: db={conn_info['current_database']} user={conn_info['current_user']}")
    except Exception as e:
        logger.error(f"[STARTUP] ERRO ao conectar no Postgres: {e}")
        raise

    Base.metadata.create_all(bind=engine)
    logger.info("[STARTUP] Tabelas criadas/verificadas (create_all)")

    yield
    # Ao desligar: nada especial por enquanto


app = FastAPI(
    title="GHL Data SaaS",
    description="Converte planilhas para o formato de importação do GoHighLevel",
    lifespan=lifespan,
)

# CORS: permite frontend em produção (Vercel/v0) e dev
ENV = os.getenv("ENV", "development")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")
if ENV == "production":
    allow_origins = [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()]
    # Se CORS_ORIGINS não foi definido no Render, permite todas as origens para o frontend funcionar
    if not allow_origins:
        allow_origins = ["*"]
else:
    allow_origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)


@app.get("/jobs", summary="Listar jobs")
def list_jobs_root(
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista os jobs do usuário (ordenados por created_at decrescente). Parâmetros: limit, offset, status."""
    query = db.query(Job).filter(Job.user_id == current_user.id)
    if status:
        query = query.filter(Job.status == status)
    query = query.order_by(Job.created_at.desc())
    total = query.count()
    jobs = query.offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "jobs": [
            {
                "id": j.id,
                "status": j.status,
                "filename_original": j.filename_original,
                "created_at": j.created_at.isoformat(),
                "error_message": j.error_message,
            }
            for j in jobs
        ],
    }


app.include_router(jobs_router)


@app.get("/")
def index():
    """Serve a página principal do frontend."""
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        return {"message": "Frontend não encontrado. Adicione index.html em frontend/"}
    return FileResponse(index_path, media_type="text/html")


@app.get("/health")
def health():
    """Verifica se o servidor está no ar."""
    return {"status": "ok"}


if os.getenv("ENV", "development") != "production":
    @app.get("/debug/db")
    def debug_db():
        """
        Endpoint de debug (somente dev): mostra qual banco está em uso,
        resultado de SELECT current_database(), current_user; e contagem de jobs.
        """
        masked_url = get_effective_url_masked()
        try:
            conn_info = test_connection()
            with engine.connect() as conn:
                r = conn.execute(text("SELECT COUNT(*) FROM jobs"))
                jobs_count = r.scalar()
            return {
                "database_url_masked": masked_url,
                "current_database": conn_info["current_database"],
                "current_user": conn_info["current_user"],
                "jobs_count": jobs_count,
                "env_loaded_from": get_env_loaded_path(),
            }
        except Exception as e:
            return {
                "database_url_masked": masked_url,
                "error": str(e),
                "env_loaded_from": get_env_loaded_path(),
            }
