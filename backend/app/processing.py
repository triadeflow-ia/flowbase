# Pipeline de processamento: lê planilha, mapeia colunas, normaliza, gera CSV GHL, report e preview
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import phonenumbers
from sqlalchemy.orm import Session

from app.config import OUTPUTS_DIR, REPORTS_DIR
from app.db import SessionLocal
from app.models import Job

# Colunas do CSV no padrão de importação do GoHighLevel (ordem fixa)
GHL_COLUMNS = [
    "Full Name",
    "Company Name",
    "Email",
    "Additional Emails",
    "Phone",
    "Additional Phone Numbers",
    "Website",
    "City",
    "State",
    "Tags",
    "Notes",
    "Source",
]

# Sinônimos PT/EN para encontrar colunas na planilha (chave = nome normalizado, valor = coluna GHL)
COLUMN_SYNONYMS = {
    "full name": "Full Name",
    "nome": "Full Name",
    "name": "Full Name",
    "nome completo": "Full Name",
    "contato": "Full Name",
    "company name": "Company Name",
    "company": "Company Name",
    "empresa": "Company Name",
    "razão social": "Company Name",
    "razao social": "Company Name",
    "email": "Email",
    "e-mail": "Email",
    "e-mail 1": "Email",
    "mail": "Email",
    "additional emails": "Additional Emails",
    "emails": "Additional Emails",
    "phone": "Phone",
    "telefone": "Phone",
    "celular": "Phone",
    "fone": "Phone",
    "mobile": "Phone",
    "additional phone numbers": "Additional Phone Numbers",
    "telefones": "Additional Phone Numbers",
    "website": "Website",
    "site": "Website",
    "url": "Website",
    "city": "City",
    "cidade": "City",
    "state": "State",
    "estado": "State",
    "uf": "State",
    "tags": "Tags",
    "notes": "Notes",
    "notas": "Notes",
    "observações": "Notes",
    "source": "Source",
    "origem": "Source",
}


def _normalize_col_name(s: str) -> str:
    """Remove acentos e deixa minúsculo para comparar com sinônimos."""
    if pd.isna(s) or not isinstance(s, str):
        return ""
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _find_column_mapping(df: pd.DataFrame) -> dict[str, str]:
    """Mapeia cada coluna GHL para o nome da coluna na planilha (ou vazio)."""
    mapping = {ghl: None for ghl in GHL_COLUMNS}
    for col in df.columns:
        key = _normalize_col_name(str(col))
        if key and key in COLUMN_SYNONYMS:
            ghl = COLUMN_SYNONYMS[key]
            if mapping[ghl] is None:
                mapping[ghl] = col
    return mapping


def _normalize_emails(val) -> str:
    """Lowercase, separar por , ; espaço, deduplicar."""
    if pd.isna(val) or val == "":
        return ""
    s = str(val).strip().lower()
    parts = re.split(r"[,;\s]+", s)
    seen = set()
    out = []
    for p in parts:
        p = p.strip()
        if p and "@" in p and p not in seen:
            seen.add(p)
            out.append(p)
    return ", ".join(out) if out else ""


def _normalize_phone(val, default_region="BR") -> str:
    """Tenta converter para E.164 (default BR +55). Retorna vazio se inválido."""
    if pd.isna(val) or val == "":
        return ""
    s = str(val).strip()
    s = re.sub(r"[\s\-\(\)]", "", s)
    if not s or not s.replace("+", "").isdigit():
        return str(val).strip()
    try:
        parsed = phonenumbers.parse(s, default_region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        pass
    return str(val).strip()


def _normalize_phones_field(val) -> str:
    """Vários telefones separados por , ; espaço -> E.164 separados por vírgula."""
    if pd.isna(val) or val == "":
        return ""
    s = str(val)
    parts = re.split(r"[,;\n]+", s)
    out = []
    for p in parts:
        n = _normalize_phone(p.strip())
        if n and n not in out:
            out.append(n)
    return ", ".join(out) if out else ""


def _row_to_ghl(row: pd.Series, mapping: dict, unmapped_cols: list) -> dict:
    """Converte uma linha da planilha para um dicionário com colunas GHL."""
    ghl_row = {c: "" for c in GHL_COLUMNS}
    notes_parts = []

    for ghl_col, source_col in mapping.items():
        if source_col is None:
            continue
        val = row.get(source_col)
        if pd.isna(val):
            val = ""
        val = str(val).strip() if val else ""

        if ghl_col == "Email" or ghl_col == "Additional Emails":
            ghl_row[ghl_col] = _normalize_emails(val)
        elif ghl_col == "Phone" or ghl_col == "Additional Phone Numbers":
            ghl_row[ghl_col] = _normalize_phones_field(val)
        else:
            ghl_row[ghl_col] = val

    for col in unmapped_cols:
        val = row.get(col)
        if pd.notna(val) and str(val).strip():
            notes_parts.append(f"{col}: {val}")
    if notes_parts:
        ghl_row["Notes"] = (ghl_row["Notes"] + " | " + " | ".join(notes_parts)).strip(" | ")

    return ghl_row


def read_file(path: str) -> pd.DataFrame:
    """Lê XLSX ou CSV com pandas."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    suf = p.suffix.lower()
    if suf == ".xlsx":
        return pd.read_excel(path)
    if suf == ".csv":
        try:
            return pd.read_csv(path, encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="latin-1")
    raise ValueError("Aceito apenas .xlsx ou .csv")


def process_to_ghl(df: pd.DataFrame) -> pd.DataFrame:
    """Mapeia e normaliza o DataFrame para as colunas GHL."""
    mapping = _find_column_mapping(df)
    unmapped = [c for c in df.columns if not any(mapping[ghl] == c for ghl in GHL_COLUMNS if mapping[ghl])]

    rows = []
    for _, row in df.iterrows():
        rows.append(_row_to_ghl(row, mapping, unmapped))

    return pd.DataFrame(rows, columns=GHL_COLUMNS)


def process_job(job_id: str) -> None:
    """
    Processa um job: lê o arquivo, gera CSV GHL, report.json e preview.
    Atualiza o registro do job no banco (status, paths, error_message).
    Roda no worker RQ (processo separado do FastAPI).
    """
    db: Session | None = None
    try:
        db = SessionLocal()
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        job.status = "processing"
        db.commit()

        try:
            df = read_file(job.file_path)
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            db.commit()
            return

        ghl_df = process_to_ghl(df)

        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        output_csv_path = OUTPUTS_DIR / f"{job_id}.csv"
        ghl_df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")

        total_rows = len(df)
        rows_output = len(ghl_df)
        with_email = (ghl_df["Email"].astype(str).str.strip() != "").sum()
        with_phone = (ghl_df["Phone"].astype(str).str.strip() != "").sum()
        pct_email = round(100 * with_email / rows_output, 1) if rows_output else 0
        pct_phone = round(100 * with_phone / rows_output, 1) if rows_output else 0

        report = {
            "total_rows": total_rows,
            "rows_output": rows_output,
            "pct_with_email": pct_email,
            "pct_with_phone": pct_phone,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        report_path = REPORTS_DIR / f"{job_id}_report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        preview_df = ghl_df.head(20)
        preview_data = preview_df.to_dict(orient="records")
        preview_path = REPORTS_DIR / f"{job_id}_preview.json"
        preview_path.write_text(json.dumps(preview_data, ensure_ascii=False, indent=2), encoding="utf-8")

        job.status = "done"
        job.output_csv_path = str(output_csv_path.resolve())
        job.report_json_path = str(report_path.resolve())
        job.error_message = None
        db.commit()
    except Exception as e:
        if db is not None:
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = "failed"
                    job.error_message = str(e)
                    db.commit()
            except Exception:
                pass
    finally:
        if db is not None:
            db.close()
