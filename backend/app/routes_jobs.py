# Endpoints de jobs: upload, status, preview, download, report
import json
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import REPORTS_DIR
from app.db import get_db
from app.models import Job, User
from app.processing import process_job
from app.queue_rq import queue
from app.storage import allowed_file, save_upload

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Regex para validar UUID (rejeita "GET /jobs/", espaços, paths, etc.)
UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _validate_job_id(job_id: str) -> None:
    """Valida que job_id é um UUID válido. Levanta 422 se inválido (ex: 'GET /jobs/' concatenado)."""
    if not job_id or not isinstance(job_id, str):
        raise HTTPException(status_code=422, detail="job_id é obrigatório")
    job_id_stripped = job_id.strip()
    if not UUID_PATTERN.match(job_id_stripped):
        raise HTTPException(
            status_code=422,
            detail=f"job_id inválido: deve ser um UUID (ex: 550e8400-e29b-41d4-a716-446655440000). Recebido: {repr(job_id)[:80]}",
        )


def _get_job_or_404(job_id: str, db: Session, current_user: User) -> Job:
    _validate_job_id(job_id)
    job = db.query(Job).filter(
        Job.id == job_id.strip(),
        Job.user_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job


@router.post("", status_code=201)
def create_job(
    file: UploadFile = File(..., description="Planilha .xlsx ou .csv"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recebe o upload de um arquivo, salva no disco, cria o job no banco e enfileira o processamento.
    Retorna o id do job para consultar status e baixar o resultado depois.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome do arquivo é obrigatório")
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Aceito apenas .xlsx ou .csv",
        )

    job_id = str(uuid.uuid4())
    content = file.file.read()

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Arquivo excede o tamanho máximo permitido de 10 MB",
        )

    file_path = save_upload(job_id, file.filename, content)

    job = Job(
        id=job_id,
        user_id=current_user.id,
        status="queued",
        filename_original=file.filename,
        file_path=file_path,
        output_csv_path=None,
        report_json_path=None,
        error_message=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    queue.enqueue(process_job, job_id)

    return {
        "id": job.id,
        "status": job.status,
        "filename_original": job.filename_original,
        "created_at": job.created_at.isoformat(),
    }


@router.get("/{job_id}")
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna o status e metadados do job."""
    job = _get_job_or_404(job_id, db, current_user)
    return {
        "id": job.id,
        "status": job.status,
        "filename_original": job.filename_original,
        "output_csv_path": job.output_csv_path,
        "report_json_path": job.report_json_path,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "error_message": job.error_message,
    }


@router.get("/{job_id}/preview")
def get_preview(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna as primeiras 20 linhas do CSV gerado em JSON. Só disponível quando status=done."""
    job = _get_job_or_404(job_id, db, current_user)
    if job.status != "done":
        raise HTTPException(status_code=409, detail="Preview só disponível quando o job estiver concluído")
    preview_path = REPORTS_DIR / f"{job.id}_preview.json"
    if not preview_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de preview não encontrado")
    data = json.loads(preview_path.read_text(encoding="utf-8"))
    return data


@router.get("/{job_id}/download")
def download_csv(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Faz o download do CSV no padrão GHL. Só disponível quando status=done."""
    job = _get_job_or_404(job_id, db, current_user)
    if job.status != "done":
        raise HTTPException(status_code=409, detail="Download só disponível quando o job estiver concluído")
    path = Path(job.output_csv_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo CSV não encontrado")
    return FileResponse(
        path,
        filename=f"ghl_import_{job.id}.csv",
        media_type="text/csv",
    )


@router.get("/{job_id}/report")
def get_report(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna o report.json com métricas do processamento. Só disponível quando status=done."""
    job = _get_job_or_404(job_id, db, current_user)
    if job.status != "done":
        raise HTTPException(status_code=409, detail="Report só disponível quando o job estiver concluído")
    path = Path(job.report_json_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de report não encontrado")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


@router.post("/{job_id}/retry", status_code=202)
def retry_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reprocessa um job que falhou. Só disponível quando status=failed.
    Reseta status para queued, limpa error_message e enfileira novamente.
    """
    job = _get_job_or_404(job_id, db, current_user)
    if job.status != "failed":
        raise HTTPException(
            status_code=409,
            detail="Retry só disponível para jobs com status=failed",
        )
    job.status = "queued"
    job.error_message = None
    job.output_csv_path = None
    job.report_json_path = None
    db.commit()

    queue.enqueue(process_job, job.id)

    return {
        "id": job.id,
        "status": job.status,
        "message": "Job enfileirado para reprocessamento",
    }
