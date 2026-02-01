# Validação FlowBase (ex-GHL Data SaaS) — MVP para Produção

**Data:** 31/01/2026  
**Base:** Análise estática do código atual

---

## 1. Resumo rápido do estado real do projeto

O projeto está **funcional e aderente à especificação** em ~95%. Todos os endpoints existem e funcionam conforme descrito. O worker processa corretamente e persiste status/paths. O frontend cobre upload, polling, listagem, preview/report/download e retry. Há **5 ajustes críticos** antes de produção (principalmente segurança e robustez).

---

## 2. Checklist de conformidade

### 1️⃣ API FastAPI

| Item | Status | Observação |
|------|--------|------------|
| `/health` | OK | Retorna `{"status":"ok"}` |
| `/debug/db` | **Ajustar** | Exposto sempre; deve ficar só em dev |
| GET `/jobs` (lista com paginação) | OK | limit, offset, status; ordenação por created_at desc |
| POST `/jobs` | OK | 201, valida extensão, enfileira |
| GET `/jobs/{id}` | OK | Validação de UUID (422), 404 se não existir |
| GET `/jobs/{id}/preview` | OK | 409 se não done, 404 se arquivo não existir |
| GET `/jobs/{id}/report` | OK | 409 se não done, 404 se arquivo não existir |
| GET `/jobs/{id}/download` | OK | 409 se não done, 404 se arquivo não existir |
| POST `/jobs/{id}/retry` | OK | 409 se não failed, 202 enfileira |
| Validação UUID | OK | Regex em `_validate_job_id` |
| Tratamento de erro 400/404/422/409 | OK | Coberto nos endpoints |

### 2️⃣ Banco de Dados

| Item | Status | Observação |
|------|--------|------------|
| Colunas e tipos | OK | id, status, filename_original, file_path, output_csv_path, report_json_path, created_at, updated_at, error_message |
| Nullables | OK | output_csv_path, report_json_path, error_message nullable |
| Status possíveis | OK | queued, processing, done, failed (usados na app) |
| `create_all()` no MVP | OK | Aceitável; em produção maior, considerar Alembic |
| Risco em produção | Atenção | Sem CHECK em status; sem índice em created_at para paginação pesada |

### 3️⃣ Worker (RQ)

| Item | Status | Observação |
|------|--------|------------|
| Transição de status | OK | queued → processing → done/failed |
| Erros em `error_message` | OK | Persistidos em falha de leitura e exceção geral |
| Paths de output/report/preview | OK | Salvos no job; preview por convenção `{id}_preview.json` |
| Retry | OK | Reseta status, limpa paths e error; reutiliza arquivo original |

### 4️⃣ Frontend

| Item | Status | Observação |
|------|--------|------------|
| Upload | OK | Drag & drop + clique |
| Polling | OK | A cada 2s, até 60 tentativas |
| Listagem de jobs | OK | GET /jobs?limit=10 |
| Preview / report / download | OK | Botões quando status=done |
| Retry | OK | Botão para jobs failed |

### 5️⃣ Segurança

| Item | Status | Observação |
|------|--------|------------|
| CORS | **Ajustar** | `allow_origins=["*"]` — restringir em produção |
| /debug/db | **Ajustar** | Sempre exposto — deve ser apenas em dev |
| Autenticação | Falta | Nenhuma — bloqueador para produção |

### 6️⃣ Infra / Docker

| Item | Status | Observação |
|------|--------|------------|
| Separação atual (backend local + docker postgres/redis) | OK | Aceitável para dev |
| Dockerfile | Falta | Necessário para produção |
| docker-compose completo | Ajustar | Só postgres/redis; falta api e worker |

---

## 3. Top 5 correções obrigatórias antes de produção

1. **Desativar `/debug/db` em produção**
   - **Arquivo:** `backend/app/main.py`
   - **O quê:** Condicionar a rota a `ENV != "production"` ou `DEBUG=true`
   - **Exemplo:** `if os.getenv("ENV") != "production":` → registrar rota

2. **Restringir CORS**
   - **Arquivo:** `backend/app/main.py`
   - **O quê:** Usar variável `CORS_ORIGINS` (ex: `https://seu-dominio.com`); em prod, não usar `["*"]`

3. **Limite de tamanho de arquivo**
   - **Arquivos:** `backend/app/main.py` e `backend/app/routes_jobs.py`
   - **O quê:** Limitar upload a 10 MB (ex: `max_size=10*1024*1024` em `File()` ou middleware)
   - **Risco:** Sem limite, uploads grandes podem derrubar o servidor

4. **`.gitignore` na raiz**
   - **O quê:** Incluir `.env`, `venv/`, `__pycache__/`, `*.pyc`, `storage/uploads/*`, `storage/outputs/*`, `storage/reports/*`
   - **Risco:** `.env` e arquivos sensíveis no repositório

5. **Autenticação mínima**
   - **O quê:** Proteger endpoints de jobs (POST, GET, etc.) com JWT ou similar
   - **Risco:** Sem auth, qualquer um usa o sistema

---

## 4. Ajustes recomendados (não obrigatórios agora)

| Item | Arquivo | O quê |
|------|---------|-------|
| Tratar `detail` em 422 | `frontend/index.html` | `data.detail` pode ser array; converter para string antes de exibir |
| Renomear para FlowBase | `main.py`, `index.html` | `title` e `h1` ainda como "GHL Data SaaS" |
| Health check completo | `main.py` | Incluir checagem de Postgres e Redis em `/health` |
| Validação de `limit` | `main.py` `list_jobs_root` | Limitar `limit` máximo (ex: 100) |
| Índice em `created_at` | Migração/Alembic | Para paginação eficiente em muitos registros |

---

## 5. Riscos se subir em produção do jeito atual

| Risco | Severidade | Descrição |
|-------|------------|-----------|
| Acesso público | Crítico | Qualquer um faz upload, lista e baixa jobs |
| Vazamento de dados | Alto | `/debug/db` expõe info de banco e caminhos |
| Abuso de upload | Alto | Sem limite de tamanho; arquivos grandes podem derrubar o servidor |
| CORS aberto | Médio | Permite requisições de qualquer origem |
| `.env` versionado | Alto | Senhas e credenciais no Git |
| Storage local | Médio | Sem volume persistente, perde dados ao reiniciar container |

---

## 6. Próximo passo único recomendado (o que fazer amanhã)

**Criar `.gitignore` e desativar `/debug/db` em produção.**

1. Adicionar `.gitignore` na raiz com as entradas acima.
2. No `main.py`, envolver a rota `/debug/db` em condição: só registrar se `os.getenv("ENV", "development") != "production"`.
3. Garantir que `.env` não esteja versionado e que `ENV=production` seja definido no ambiente de produção.

---

## 7. Estrutura mínima sugerida para Docker (produção)

```yaml
# docker-compose.prod.yml (exemplo)
services:
  postgres:
    # ... (igual ao atual)
  redis:
    # ... (igual ao atual)
  api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379/0
      - ENV=production
    depends_on: [postgres, redis]
    volumes:
      - storage_data:/app/storage
  worker:
    build: ./backend
    command: python -m app.worker
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379/0
    depends_on: [postgres, redis]
    volumes:
      - storage_data:/app/storage
volumes:
  storage_data:
```

```dockerfile
# backend/Dockerfile (exemplo)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

**Conclusão:** O MVP está aderente à especificação e funcional. Para produção, priorizar as 5 correções obrigatórias (principalmente auth, CORS, /debug/db, limite de arquivo e .gitignore), depois containerização e variáveis de ambiente.
