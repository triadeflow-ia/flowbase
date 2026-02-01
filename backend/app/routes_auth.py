# Endpoints de autenticação: registro e login
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Senha deve ter no mínimo 6 caracteres")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", status_code=201)
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Cria uma nova conta com email e senha.
    Retorna 400 se o email já existir.
    """
    existing = db.query(User).filter(User.email == body.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    user = User(
        id=str(uuid.uuid4()),
        email=body.email.lower(),
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer", "user_id": user.id}


@router.post("/login")
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Faz login com email e senha.
    Retorna token JWT se as credenciais forem válidas.
    """
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer", "user_id": user.id}
