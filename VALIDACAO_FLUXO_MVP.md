# Validação Técnica — Fluxo MVP Fase 1 (GHL Data SaaS)

**Data:** 31/01/2026  
**Tipo:** Diagnóstico estático + checklist manual

---

## 1. Diagnóstico técnico do fluxo

### A) Onde cada etapa acontece

| Etapa | Arquivo | Função/Linha | O que faz |
|-------|---------|--------------|-----------|
| **Job criado** | `routes_jobs.py` | `create_job` (L61–76) | `job_id = uuid`, `save_upload()`, `Job(...)`, `db.add()`, `db.commit()`, `db.refresh()` |
| **Job enfileirado** | `routes_jobs.py` | `create_job` (L79) | `queue.enqueue(process_job, job_id)` |
| **Fila Redis** | `queue_rq.py` | — | `Queue("default", Redis.from_url(REDIS_URL))` |
| **Worker consome** | `worker.py` | `run_worker` | `SimpleWorker([queue]).work()` — escuta a fila "default" |
| **Processamento** | `processing.py` | `process_job` | Lê arquivo, normaliza, gera CSV/report/preview, atualiza job |
| **Status atualizado** | `processing.py` | `process_job` | `job.status = "processing"` (L213), `"done"` (L255) ou `"failed"` (L219, L262) + `db.commit()` |

### B) API e Worker usam os mesmos recursos?

| Recurso | API | Worker | Mesmo? |
|---------|-----|--------|--------|
| **DATABASE_URL** | `config.py` via `db.py` | `config.py` via `processing` → `db.py` | Sim |
| **Redis** | `queue_rq.py` → `REDIS_URL` | `worker.py` → `REDIS_URL` | Sim |
| **Fila** | `Queue("default", Redis)` | `Queue("default", Redis)` | Sim |
| **SQLite** | Rejeitado em `config.py` (L28–31) | N/A | Não usa |

API e Worker importam `app.config`, que carrega o mesmo `.env` na raiz do projeto. Os dois usam o mesmo banco e o mesmo Redis.

### C) Estados do job

| Status | Onde é definido |
|--------|------------------|
| `queued` | `routes_jobs.py` L68 (criação) e L161 (retry) |
| `processing` | `processing.py` L213 |
| `done` | `processing.py` L255 |
| `failed` | `processing.py` L219 (erro em `read_file`), L262 (exceção geral) |

---

## 2. Pontos OK

| Item | Status |
|------|--------|
| POST /jobs cria job com status `queued` | OK |
| Job gravado na tabela `jobs` (Postgres) | OK |
| Enfileiramento via RQ na fila "default" | OK |
| Worker consome fila "default" | OK |
| API e Worker usam mesma `DATABASE_URL` | OK |
| API e Worker usam mesmo Redis | OK |
| Rejeição de SQLite em `config.py` | OK |
| Normalização de email e telefone | OK |
| Geração de CSV GHL, preview e report | OK |
| Atualização de status no banco pelo worker | OK |
| GET /jobs/{id}, /preview, /report, /download | OK |
| Validação de UUID em `job_id` | OK |
| Tratamento de exceção no worker (`db = None`) | OK |
| POST /jobs/{id}/retry para jobs falhos | OK |

---

## 3. Pontos de risco

| Risco | Onde | Impacto | Mitigação |
|-------|------|---------|-----------|
| Job não encontrado no worker | `processing.py` L211–214 | Job fica `queued` para sempre | Improvável; indica banco diferente. Usar GET /debug/db para conferir. |
| Falha ao marcar `failed` no `except` | `processing.py` L260–265 | Job pode ficar `processing` | `except Exception: pass` engole erros. Monitorar jobs em `processing` há muito tempo. |
| Worker parado | — | Jobs ficam sempre `queued` | Garantir que o worker está rodando. |
| Redis parado | — | `queue.enqueue()` pode falhar | Conferir `docker ps` e `redis-cli ping`. |
| Arquivo removido entre upload e processamento | `processing.py` L218 | `failed` com "Arquivo não encontrado" | Evitar apagar arquivos em `storage/uploads` manualmente. |

---

## 4. Logs esperados

### Terminal da API (uvicorn)

```
[STARTUP] .env carregado de: ...\.env
[STARTUP] DATABASE_URL (mascarada): postgresql+psycopg://ghluser:****@localhost:5432/ghldb
[STARTUP] Driver: postgresql+psycopg
[STARTUP] Postgres conectado: db=ghldb user=ghluser
[STARTUP] Tabelas criadas/verificadas (create_all)
INFO:     Application startup complete.
INFO:     127.0.0.1:xxx - "POST /jobs HTTP/1.1" 201
INFO:     127.0.0.1:xxx - "GET /jobs/xxx HTTP/1.1" 200
```

### Terminal do worker

```
Worker rq:worker:xxx started with PID xxx
*** Listening on default...
default: app.processing.process_job('uuid-do-job') (job-id)
Job OK (uuid-do-job)
```

Se o job falhar:

```
default: app.processing.process_job('uuid') (job-id)
Traceback ...
```

---

## 5. Checklist final de validação manual

Execute nesta ordem.

### Pré-requisitos

- [ ] Docker rodando (Postgres + Redis)
- [ ] `.env` na raiz com `DATABASE_URL` e `REDIS_URL`

### Passo 1 — Subir serviços

```powershell
cd "c:\Users\Alex Campos\OneDrive\ghl-data-saas"
docker-compose up -d
```

- [ ] `docker ps` mostra `ghl-postgres` e `ghl-redis` como "Up"

### Passo 2 — Subir API

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- [ ] Mensagem `Application startup complete`
- [ ] Sem traceback em vermelho
- [ ] `http://localhost:8000/health` retorna `{"status":"ok"}`

### Passo 3 — Subir worker (outro terminal)

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m app.worker
```

- [ ] Mensagem `Listening on default...`
- [ ] Nenhum erro na inicialização

### Passo 4 — POST /jobs

Via Swagger (http://localhost:8000/docs) ou curl:

```powershell
curl.exe -s -X POST -F "file=@backend/test_data.csv" http://localhost:8000/jobs
```

- [ ] Resposta 201 com `id`, `status`, `filename_original`, `created_at`
- [ ] Copiar o `id` (UUID) retornado

### Passo 5 — Aguardar processamento

- [ ] Esperar cerca de 5–10 segundos
- [ ] No terminal do worker, ver mensagem tipo: `default: app.processing.process_job('...')`
- [ ] Sem traceback no worker

### Passo 6 — GET /jobs/{id}

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/jobs/SEU-UUID-AQUI" -UseBasicParsing
```

- [ ] Status 200
- [ ] `status` = `"done"` (ou `"failed"` se houve erro)
- [ ] Se `done`: `output_csv_path` e `report_json_path` preenchidos

### Passo 7 — GET /jobs/{id}/preview (se status=done)

- [ ] Status 200
- [ ] JSON com até 20 linhas

### Passo 8 — GET /jobs/{id}/report (se status=done)

- [ ] Status 200
- [ ] JSON com `total_rows`, `pct_with_email`, `pct_with_phone`

### Passo 9 — GET /jobs/{id}/download (se status=done)

- [ ] Status 200
- [ ] Download do CSV GHL

### Passo 10 — Conferir banco (opcional)

```powershell
docker exec ghl-postgres psql -U ghluser -d ghldb -c "SELECT id, status, filename_original FROM jobs ORDER BY created_at DESC LIMIT 5;"
```

- [ ] Job aparece com `status` correto

---

## 6. Conclusão

### MVP Fase 1 validado

O fluxo está implementado corretamente no código:

1. POST /jobs cria o job e enfileira.
2. Worker processa e atualiza status no banco.
3. API e Worker usam o mesmo Postgres e Redis.
4. GETs de status, preview, report e download funcionam como esperado.
5. Estados `queued`, `processing`, `done` e `failed` estão cobertos.

Para considerar o MVP validado na prática, é necessário:

1. API e worker rodando.
2. Docker com Postgres e Redis ativos.
3. Pelo menos um fluxo completo (POST → esperar → GET status → GET preview/report/download) executado com sucesso.

Se todos os itens do checklist forem marcados sem erro, o MVP Fase 1 está validado em operação.
