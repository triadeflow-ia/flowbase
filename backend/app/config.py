# Configurações do projeto (lê variáveis do .env na raiz)
import re
from pathlib import Path
import os
from dotenv import load_dotenv

# Carrega .env da raiz do projeto (pasta acima de backend/)
# Garante que funciona tanto rodando de backend/ quanto de ghl-data-saas/
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent

_env_paths = [
    ROOT_DIR / ".env",
    BACKEND_DIR.parent / ".env",
    Path.cwd() / ".env",
    Path.cwd().parent / ".env",
]
_env_loaded = None
for _p in _env_paths:
    if _p.exists():
        load_dotenv(_p)
        _env_loaded = str(_p)
        break

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ghluser:ghlpass@localhost:5432/ghldb")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
JWT_SECRET = os.getenv("JWT_SECRET", "altere-isso-em-producao-use-uma-string-longa-e-aleatoria")
JWT_ALGORITHM = "HS256"

# Rejeita qualquer fallback para SQLite ou banco em memória
if "sqlite" in DATABASE_URL.lower() or ":memory:" in DATABASE_URL:
    raise ValueError(
        "DATABASE_URL não pode ser SQLite. Use Postgres. Exemplo: postgresql://ghluser:ghlpass@localhost:5432/ghldb"
    )

# Pastas de armazenamento (relativas ao backend/)
STORAGE_DIR = BACKEND_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
OUTPUTS_DIR = STORAGE_DIR / "outputs"
REPORTS_DIR = STORAGE_DIR / "reports"


def get_masked_database_url() -> str:
    """Retorna DATABASE_URL com senha mascarada (para logs/debug)."""
    url = DATABASE_URL
    # Máscara senha em postgresql://user:password@host:port/db
    match = re.match(r"(postgresql(?:\+psycopg)?://[^:]+:)([^@]+)(@.+)", url)
    if match:
        return f"{match.group(1)}****{match.group(3)}"
    return "****" if url else "(vazio)"


def get_env_loaded_path() -> str | None:
    """Retorna o caminho do .env que foi carregado (para debug)."""
    return _env_loaded
