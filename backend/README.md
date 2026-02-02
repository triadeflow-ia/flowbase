# FlowBase - Backend

Sistema para converter planilhas (XLSX/CSV) para o formato de importação do GoHighLevel. Autenticação JWT, processamento em background (RQ + Redis).

## Pré-requisitos

- Python 3.10 ou superior
- Docker Desktop instalado e rodando (para Postgres e Redis em dev)

## Como rodar (passo a passo)

### 1. Subir os serviços (Postgres + Redis)

Na raiz do projeto:

```bash
docker-compose up -d
```

### 2. Verificar se estão rodando

```bash
docker ps
```

Você deve ver dois containers: `ghl-postgres` e `ghl-redis`.

### 3. Variáveis de ambiente

Copie `.env.example` para `.env` na raiz e ajuste se necessário (DATABASE_URL, REDIS_URL, JWT_SECRET).

### 4. Criar ambiente virtual Python

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Rodar o servidor (FastAPI)

```bash
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Acesse:
- **Frontend:** http://localhost:8000
- **API (Swagger):** http://localhost:8000/docs

### 6. Rodar o worker (processamento em background)

Em **outro terminal**, com o venv ativado:

```bash
cd backend
.\venv\Scripts\activate
python -m app.worker
```

O worker processa os jobs enfileirados (conversão para CSV GHL, report e preview).  
No Windows é usado `SimpleWorker` (RQ não suporta fork no Windows).

### 7. Autenticação (endpoints protegidos)

- **Cadastro:** `POST /auth/register` com `{"email": "...", "password": "..."}`
- **Login:** `POST /auth/login` com `{"email": "...", "password": "..."}`
- Use o `access_token` retornado no header: `Authorization: Bearer <token>`
- Todos os endpoints `/jobs*` exigem autenticação.

## Produção (Render)

- Build: imagem Docker com `Dockerfile` na pasta backend.
- Variáveis no Render: `ENV=production`, `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `CORS_ORIGINS` (opcional).
- URL do backend em produção: configurar no frontend (ex.: `https://flowbase-y89b.onrender.com`).

## Estrutura

```
backend/
  app/
    main.py         # Servidor FastAPI, CORS, rotas raiz
    config.py       # Configurações (DB, Redis, JWT)
    db.py           # Conexão com banco
    models.py       # User, Job
    auth.py         # JWT, get_current_user, hash de senha
    routes_auth.py  # POST /auth/register, /auth/login
    routes_jobs.py  # Endpoints /jobs (upload, status, download, etc.)
    storage.py      # Upload e validação de arquivos
    processing.py   # Lógica de conversão para CSV GHL
    queue_rq.py     # Fila Redis (RQ)
    worker.py       # Processador de fila
  storage/
    uploads/        # Arquivos enviados
    outputs/        # CSVs gerados
    reports/        # preview.json, report.json
  Dockerfile        # Imagem para produção
```
