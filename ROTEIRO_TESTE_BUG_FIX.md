# Roteiro de teste — Bug POST 201 / GET 404

Execute estes comandos **na ordem**, no PowerShell, a partir da raiz do projeto.

---

## Pré-requisitos

- Docker rodando (Postgres + Redis)
- Backend com venv ativado
- API rodando em http://localhost:8000
- Worker RQ rodando

---

## Passo 1 — Verificar banco conectado

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/debug/db" -UseBasicParsing | Select-Object -ExpandProperty Content
```

**Resultado esperado:** JSON com `current_database`, `current_user` e `jobs_count`. Deve ser `ghldb` e `ghluser`.

---

## Passo 2 — POST /jobs com test_data.csv

```powershell
cd "c:\Users\Alex Campos\OneDrive\ghl-data-saas"
$response = curl.exe -s -X POST -F "file=@backend/test_data.csv" http://localhost:8000/jobs
$response
```

**Resultado esperado:** 201 com JSON como:
```json
{"id":"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx","status":"queued","filename_original":"test_data.csv","created_at":"..."}
```

**Copie o `id` (UUID) da resposta para o próximo passo.**

---

## Passo 3 — GET /jobs/{id} com o UUID retornado

**Opção A — Automático (extrai o id da resposta do POST):**

```powershell
$jobId = ($response | ConvertFrom-Json).id
Invoke-WebRequest -Uri "http://localhost:8000/jobs/$jobId" -UseBasicParsing | Select-Object -ExpandProperty Content
```

**Opção B — Manual (substitua SEU_JOB_ID_AQUI pelo UUID copiado do Passo 2):**

```powershell
$jobId = "SEU_JOB_ID_AQUI"
Invoke-WebRequest -Uri "http://localhost:8000/jobs/$jobId" -UseBasicParsing | Select-Object -ExpandProperty Content
```

**Resultado esperado:** 200 com JSON do job (status, filename_original, etc.), **não** 404.

---

## Passo 4 — Verificar job no Postgres via Docker

```powershell
docker exec ghl-postgres psql -U ghluser -d ghldb -c "SELECT id, status, filename_original, created_at FROM jobs ORDER BY created_at DESC LIMIT 5;"
```

**Resultado esperado:** Lista com o job criado no Passo 2.

---

## Passo 5 — Teste de validação (job_id inválido → 422)

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/jobs/GET%20/jobs/550e8400-e29b-41d4-a716-446655440000" -UseBasicParsing
```

**Resultado esperado:** 422 com mensagem de job_id inválido.

---

## Checklist de diagnóstico

Se GET ainda retornar 404:

1. **GET /debug/db** — Confirme `current_database` = `ghldb` e `current_user` = `ghluser`.
2. **docker exec psql** — O job aparece na lista? Se sim, a API pode estar conectada em outro banco.
3. **Logs do uvicorn** — No startup deve aparecer `[STARTUP] Postgres conectado: db=ghldb user=ghluser`.
4. **.env** — Verifique se existe na raiz e se `DATABASE_URL=postgresql://ghluser:ghlpass@localhost:5432/ghldb`.
