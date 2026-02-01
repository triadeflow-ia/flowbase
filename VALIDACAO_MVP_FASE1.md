# Validação MVP Fase 1 — GHL Data SaaS

**Data:** 31/01/2026  
**Tipo:** Análise estática de código (QA + Backend Engineer)  
**Objetivo:** Confirmar se o fluxo completo funciona do início ao fim.

---

## Checklist do fluxo esperado

| # | Etapa | Status | Detalhe |
|---|-------|--------|---------|
| 1 | POST /jobs — upload CSV/XLSX, retorna 201 com job_id (UUID) | ✅ | `routes_jobs.py` create_job: valida arquivo, gera UUID, salva no banco, enfileira, retorna id |
| 2 | Job salvo na tabela `jobs` do Postgres | ✅ | `db.add(job)` + `db.commit()` — usa SessionLocal vinculado ao engine |
| 3 | Worker RQ processa o job em background | ✅ | `queue.enqueue(process_job, job_id)` → Redis → SimpleWorker executa `process_job` |
| 4 | Status muda: queued → processing → done (ou failed) | ✅ | `processing.py` process_job: atualiza status e faz commit em cada etapa |
| 5 | GET /jobs/{job_id} retorna status e metadados | ✅ | `_get_job_or_404` busca no banco e retorna o job |
| 6 | GET /jobs/{job_id}/preview retorna até 20 linhas (status=done) | ✅ | Lê `{job_id}_preview.json` em REPORTS_DIR; 409 se status≠done |
| 7 | GET /jobs/{job_id}/report retorna métricas | ✅ | Lê `report_json_path` do job; 409 se status≠done |
| 8 | GET /jobs/{job_id}/download faz download do CSV GHL | ✅ | FileResponse com `output_csv_path`; 409 se status≠done |

---

## Verificações técnicas

### POST e GET usam o mesmo banco e a mesma Session?

**✅ Sim.**

- **db.py:** Um único `engine` e um único `SessionLocal` criados a partir de `DATABASE_URL` (carregada de `.env`).
- **POST /jobs:** Usa `Depends(get_db)` → `SessionLocal()`.
- **GET /jobs/{id}, /preview, /download, /report:** Usam o mesmo `Depends(get_db)` → `SessionLocal()`.
- **Conclusão:** Todas as requisições da API usam o mesmo engine e o mesmo banco.

---

### O worker grava no mesmo banco?

**✅ Sim.**

- **processing.py** importa `SessionLocal` de `app.db`.
- `SessionLocal` usa o mesmo `engine` definido em `db.py`.
- O worker carrega `app.processing`, que usa `app.db` e `app.config`.
- O worker também chama `load_dotenv(ROOT_DIR / ".env")` com o mesmo `ROOT_DIR` do projeto.
- **Conclusão:** FastAPI e worker usam o mesmo `DATABASE_URL` e o mesmo banco.

---

### POST em banco A e GET em banco B?

**❌ Não há esse cenário.**

- Existe apenas um `engine` (em `db.py`).
- Existe apenas um `DATABASE_URL` (em `config.py`, vindo do `.env`).
- Não há fallback para SQLite ou outro banco (config rejeita `sqlite` e `:memory:`).
- **Conclusão:** Não existe bifurcação entre banco A e B.

---

### Swagger usa os paths corretos?

**✅ Sim.**

- FastAPI gera o Swagger a partir das rotas definidas.
- Router com `prefix="/jobs"`:
  - POST `""` → POST `/jobs`
  - GET `"/{job_id}"` → GET `/jobs/{job_id}`
  - GET `"/{job_id}/preview"` → GET `/jobs/{job_id}/preview`
  - GET `"/{job_id}/download"` → GET `/jobs/{job_id}/download`
  - GET `"/{job_id}/report"` → GET `/jobs/{job_id}/report`
- O parâmetro `{job_id}` é um path parameter; o usuário deve informar só o UUID.
- **Conclusão:** Paths estão corretos.

---

### Validação de UUID em `job_id`?

**✅ Sim.**

- **routes_jobs.py:** `_validate_job_id(job_id)` usa regex para UUID.
- Se inválido (ex.: "GET /jobs/" concatenado, espaços, etc.) → **422 Unprocessable Entity**.
- Chamada em `_get_job_or_404`, usada por todos os endpoints GET que recebem `job_id`.

---

### Códigos HTTP de erro?

**✅ Sim.**

| Código | Onde |
|--------|------|
| 404 | Job não encontrado; arquivo de preview/report não encontrado |
| 422 | `job_id` inválido (não é UUID) |
| 409 | Preview/download/report quando status ≠ done |
| 400 | Nome do arquivo vazio; extensão diferente de .xlsx/.csv |

---

## Resumo da validação

### Conclusão

**O MVP Fase 1 está funcional.**

O código cobre o fluxo esperado:

1. Upload → job criado no Postgres e enfileirado.
2. Worker processa e atualiza o status no mesmo banco.
3. GETs de status, preview, report e download retornam o esperado quando o job está concluído.

Não foi encontrado problema que impeça o fluxo de funcionar.

---

## Melhorias opcionais (não obrigatórias)

| Item | Descrição |
|------|-----------|
| Tratamento de exceção no worker | Se `SessionLocal()` falhar no início de `process_job`, o `except` pode falhar ao acessar `db`. Caso raro; pode ser tratado depois. |
| GET /jobs (listagem) | Hoje não existe listagem de jobs; útil para UX futura. |
| Retry de jobs falhos | Reprocessar jobs com status `failed` pode ser adicionado depois. |

---

## Como testar na prática

1. Subir Docker (Postgres + Redis).
2. Subir API: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
3. Subir worker: `python -m app.worker`
4. Fazer POST /jobs com `backend/test_data.csv`.
5. Aguardar alguns segundos.
6. Fazer GET /jobs/{id} com o UUID retornado.
7. Com status=done: testar /preview, /report, /download.

Se tudo responder conforme esperado, o MVP está operando corretamente.
