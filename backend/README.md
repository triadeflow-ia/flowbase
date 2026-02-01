# GHL Data SaaS - Backend

Sistema para converter planilhas para o formato de importação do GoHighLevel.

## Pré-requisitos

- Python 3.10 ou superior
- Docker Desktop instalado e rodando

## Como rodar (passo a passo)

### 1. Subir os serviços (Postgres + Redis)

```bash
docker-compose up -d
```

### 2. Verificar se estão rodando

```bash
docker ps
```

Você deve ver dois containers: `ghl-postgres` e `ghl-redis`.

### 3. Criar ambiente virtual Python

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Rodar o servidor (FastAPI)

```bash
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Acesse:
- **Frontend:** http://localhost:8000
- **API (Swagger):** http://localhost:8000/docs

### 5. Rodar o worker (processamento em background)

Em **outro terminal**, com o venv ativado:

```bash
cd backend
.\venv\Scripts\activate
python -m app.worker
```

O worker processa os jobs enfileirados (conversão para CSV GHL, report e preview).  
No Windows é usado `SimpleWorker` (RQ não suporta fork no Windows).

## Estrutura

```
backend/
  app/
    main.py         # Servidor FastAPI
    config.py       # Configurações
    db.py           # Conexão com banco
    models.py       # Tabelas do banco
    storage.py      # Gerencia arquivos
    routes_jobs.py  # Endpoints de jobs
    processing.py   # Lógica de conversão
    worker.py       # Processador de fila
  storage/
    uploads/        # Arquivos enviados
    outputs/        # CSVs gerados
    reports/        # Relatórios JSON
```
