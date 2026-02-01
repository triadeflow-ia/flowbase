# Modelos das tabelas do banco (cada classe = uma tabela)
from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.db import Base


class User(Base):
    """Tabela users: usuários do sistema (autenticação)."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class Job(Base):
    """Tabela jobs: um registro por arquivo enviado (um job = um processamento)."""
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    filename_original: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    output_csv_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    report_json_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
