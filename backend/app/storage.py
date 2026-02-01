# Funções para salvar e localizar arquivos (uploads, CSVs gerados, reports)
from pathlib import Path

from app.config import UPLOADS_DIR

ALLOWED_EXTENSIONS = {".xlsx", ".csv"}


def allowed_file(filename: str) -> bool:
    """Verifica se o arquivo tem extensão permitida (.xlsx ou .csv)."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def save_upload(job_id: str, filename_original: str, content: bytes) -> str:
    """
    Salva o arquivo enviado na pasta de uploads.
    Nome no disco: job_id + extensão do arquivo original.
    Retorna o caminho absoluto do arquivo salvo (para guardar no banco).
    """
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(filename_original).suffix.lower() or ".bin"
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".csv"
    path = UPLOADS_DIR / f"{job_id}{ext}"
    path.write_bytes(content)
    return str(path.resolve())
