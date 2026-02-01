# Validação das melhorias

## Melhorias implementadas

1. **Tratamento de exceção no worker** (`processing.py`) — OK  
2. **GET /jobs — listagem** (`main.py`) — use GET /jobs  
3. **POST /jobs/{id}/retry** (`routes_jobs.py`) — OK  

---

## Como validar

**Importante:** Reinicie o servidor (uvicorn) para garantir que todas as alterações foram carregadas.

### 1. Reinicie o servidor

No terminal do uvicorn, pressione **Ctrl+C** e rode novamente:

```powershell
cd "c:\Users\Alex Campos\OneDrive\ghl-data-saas\backend"
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. GET /jobs (listagem)

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/jobs" -Method Get -UseBasicParsing | Select-Object -ExpandProperty Content
```

**Esperado:** 200 com JSON `{ total, limit, offset, jobs: [...] }`.

### 3. POST /jobs (upload) + GET /jobs/{id}

```powershell
$r = curl.exe -s -X POST -F "file=@backend/test_data.csv" http://localhost:8000/jobs
$jobId = ($r | ConvertFrom-Json).id
Invoke-WebRequest -Uri "http://localhost:8000/jobs/$jobId" -UseBasicParsing | Select-Object -ExpandProperty Content
```

**Esperado:** 201 no POST, 200 no GET com dados do job.

### 4. POST /jobs/{id}/retry (só para status=failed)

Crie um job que falhe (ex.: arquivo .txt) ou use um job existente com status=failed:

```powershell
$jobId = "UUID-DE-JOB-FALHADO"
Invoke-WebRequest -Uri "http://localhost:8000/jobs/$jobId/retry" -Method Post -UseBasicParsing | Select-Object -ExpandProperty Content
```

**Esperado:** 202 com `{ id, status: "queued", message: "..." }`.  
Para job que não está `failed`: 409.

---

## Nota sobre GET /jobs

O GET /jobs está definido em `main.py` (antes do router). Se continuar retornando 405 após reiniciar, use **GET /jobs-list** como alternativa — essa rota está em `main.py` e não conflita com o router.
