# Auditoria Completa — FlowBase MVP (Projeto completo até deploy em produção)

**Data:** 31/01/2026  
**Objetivo:** Documentar tudo que foi feito no projeto FlowBase (ex-GHL Data SaaS) para análise por IA e decisões de próximos passos.

---

## 1. Visão Geral do Projeto

**Nome:** FlowBase (anteriormente GHL Data SaaS)  
**Propósito:** SaaS que recebe planilhas (XLSX/CSV), processa em background, normaliza dados (emails, telefones) e gera CSV no padrão GoHighLevel com preview, report e download.  
**Stack:** Python, FastAPI, PostgreSQL, Redis, RQ, pandas, phonenumbers, JWT (auth), Docker.  
**Ambiente atual:** Backend em produção no Render, frontend em desenvolvimento no Vercel/v0.dev.

---

## 2. Estrutura do Projeto

```
ghl-data-saas/
├── .env                       # Variáveis locais (não versionado)
├── .env.example               # Template de variáveis
├── docker-compose.yml         # Postgres + Redis (para dev local)
├── backend/
│   ├── Dockerfile             # Imagem Docker do backend (produção)
│   ├── .dockerignore          # Evita copiar venv, .env, etc.
│   ├── requirements.txt       # Dependências Python
│   ├── README.md
│   ├── app/
│   │   ├── __init__.py
│   │   ├── auth.py            # Hash senha, JWT, get_current_user
│   │   ├── config.py          # DATABASE_URL, REDIS_URL, JWT_SECRET, CORS
│   │   ├── db.py              # SQLAlchemy, engine, SessionLocal
│   │   ├── main.py            # FastAPI, CORS, rotas raiz, lifespan
│   │   ├── models.py          # User, Job (tabelas do banco)
│   │   ├── processing.py      # Pipeline: lê XLSX/CSV, normaliza, gera GHL
│   │   ├── queue_rq.py        # Fila Redis (RQ)
│   │   ├── routes_auth.py     # POST /auth/register, /auth/login
│   │   ├── routes_jobs.py     # Endpoints /jobs (upload, status, download, etc.)
│   │   ├── storage.py         # Save upload, validação de extensão
│   │   └── worker.py          # Worker RQ (SimpleWorker para Windows)
│   └── storage/
│       ├── uploads/           # Arquivos enviados
│       ├── outputs/           # CSVs gerados
│       └── reports/           # preview.json, report.json
└── frontend/
    └── index.html             # Interface única (HTML + CSS + JS vanilla)
```

---

## 3. Checkpoints Concluídos (Histórico)

### Checkpoint A — Docker Compose (Postgres + Redis)
- Criado `docker-compose.yml` com Postgres 15 e Redis 7-alpine.
- Volumes persistentes (`postgres_data`, `redis_data`).
- Portas expostas: 5432 (Postgres), 6379 (Redis).

### Checkpoint B — Backend FastAPI + venv
- Criado `backend/requirements.txt` com FastAPI, uvicorn, SQLAlchemy, psycopg3, pandas, redis, rq, etc.
- Criado `backend/app/main.py` com FastAPI, GET `/health`.
- Resolvidos erros de dependências (psycopg2 → psycopg3, pandas wheels, SQLAlchemy >=2.0.40 para Python 3.14).

### Checkpoint C — Banco de Dados (Postgres)
- Modelo `Job` em `models.py` (id, status, filename_original, file_path, output_csv_path, report_json_path, created_at, updated_at, error_message).
- `Base.metadata.create_all()` no startup (lifespan).
- Testes de conexão (`test_connection`, endpoint `/debug/db`).

### Checkpoint D — POST /jobs (Upload)
- Endpoint `POST /jobs` em `routes_jobs.py`: upload de arquivo, criação de job com status `queued`, enfileiramento via RQ.
- Validação de extensão (.xlsx, .csv), UUID como job_id.

### Checkpoint E — Worker RQ + Processamento
- Worker em `worker.py` com `SimpleWorker` (compatível com Windows, sem `os.fork()`).
- Pipeline em `processing.py`: lê XLSX/CSV (pandas), mapeia colunas por sinônimos PT/EN, normaliza emails (lowercase, dedup), normaliza telefones (E.164, BR +55), gera CSV GHL (12 colunas), gera preview (20 linhas JSON), gera report (total_rows, pct_with_email, pct_with_phone).
- Atualização de status: `queued` → `processing` → `done` ou `failed`.

### Checkpoint F — Endpoints de consulta
- `GET /jobs/{id}`: status e metadados do job.
- `GET /jobs/{id}/preview`: 20 linhas em JSON (só quando done).
- `GET /jobs/{id}/download`: download do CSV GHL (só quando done).
- `GET /jobs/{id}/report`: métricas (só quando done).
- `POST /jobs/{id}/retry`: reprocessa job falho.
- `GET /jobs`: lista jobs com paginação (limit, offset, status).

### Checkpoint G — Testes manuais
- Fluxo completo testado: upload → worker → status done → preview/report/download.
- Correções: bug POST 201 / GET 404 (UUID validation, robust .env loading, debug endpoint).

---

## 4. Implementações de Segurança e Produção

### 4.1. Endpoint /debug/db (dev-only)
- Protegido: só disponível quando `ENV != "production"`.
- Mostra DATABASE_URL mascarada, current_database, current_user, contagem de jobs.

### 4.2. CORS restrito
- Em dev: `allow_origins=["*"]`.
- Em produção: lê `CORS_ORIGINS` (lista de URLs separadas por vírgula); se vazio, usa `["*"]` para não bloquear frontend.
- Permite `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]` (necessário para Bearer token).

### 4.3. Limite de tamanho de arquivo
- Upload limitado a **10 MB** (10 * 1024 * 1024 bytes).
- Se exceder: retorna 413 com mensagem "Arquivo excede o tamanho máximo permitido de 10 MB".

### 4.4. Autenticação (JWT)
- Tabela `users` (id, email único, password_hash, created_at).
- Hash de senha com `passlib[bcrypt]`.
- JWT com `PyJWT` (token válido por 7 dias).
- Endpoints:
  - `POST /auth/register`: cadastro (email + senha).
  - `POST /auth/login`: login (email + senha → retorna access_token).
- Proteção de endpoints `/jobs*`: todos requerem `Depends(get_current_user)`.
- Associação jobs ↔ user: `user_id` em `Job` (nullable); cada usuário vê só seus próprios jobs.

---

## 5. Docker e Deploy

### 5.1. Dockerfile
- Imagem: `python:3.11-slim`.
- WORKDIR: `/app`.
- Instalação de dependências: `pip install --no-cache-dir -r requirements.txt`.
- CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

### 5.2. .dockerignore
- Evita copiar `venv/`, `__pycache__/`, `.env`, `.git/`, etc.

### 5.3. Deploy no Render
- Backend hospedado em: `https://flowbase-y89b.onrender.com`.
- Variáveis de ambiente no Render:
  - `ENV=production`
  - `DATABASE_URL` (Postgres do Render)
  - `REDIS_URL` (Redis externo ou Render)
  - `JWT_SECRET` (string longa e aleatória)
  - `CORS_ORIGINS` (opcional; se vazio, usa `["*"]`)

---

## 6. Frontend

### 6.1. Interface local (index.html)
- Upload por drag & drop ou clique.
- Polling de status do job (a cada 2s, até 60 tentativas).
- Lista de jobs recentes (GET /jobs).
- Preview, report, download quando status=done.
- Retry para jobs failed.

### 6.2. Frontend em produção (Vercel/v0.dev)
- Next.js hospedado no Vercel/v0.
- Faz requisições para `https://flowbase-y89b.onrender.com/auth/register` e `/auth/login`.
- CORS corrigido: backend permite origens do frontend (via `CORS_ORIGINS` ou `["*"]`).

---

## 7. Banco de Dados

### 7.1. Tabela `users`
| Coluna         | Tipo         | Descrição                  |
|----------------|--------------|----------------------------|
| id             | VARCHAR(36)  | UUID, PK                   |
| email          | VARCHAR(255) | Único, índice              |
| password_hash  | VARCHAR(255) | Hash bcrypt                |
| created_at     | TIMESTAMP    | Data de criação            |

### 7.2. Tabela `jobs`
| Coluna            | Tipo         | Descrição                           |
|-------------------|--------------|-------------------------------------|
| id                | VARCHAR(36)  | UUID, PK                            |
| user_id           | VARCHAR(36)  | FK users.id, nullable, índice       |
| status            | VARCHAR(20)  | queued, processing, done, failed    |
| filename_original | VARCHAR(255) | Nome do arquivo enviado             |
| file_path         | VARCHAR(512) | Caminho absoluto do upload          |
| output_csv_path   | VARCHAR(512) | Caminho do CSV gerado (nullable)    |
| report_json_path  | VARCHAR(512) | Caminho do report (nullable)        |
| created_at        | TIMESTAMP    | Data de criação                     |
| updated_at        | TIMESTAMP    | Última atualização                  |
| error_message     | TEXT         | Mensagem de erro (nullable)         |

---

## 8. Endpoints Disponíveis

| Método | Rota                       | Auth? | Descrição                                     |
|--------|----------------------------|-------|-----------------------------------------------|
| GET    | /                          | Não   | Serve index.html (frontend local)             |
| GET    | /health                    | Não   | Health check `{"status":"ok"}`                |
| GET    | /debug/db                  | Não   | Debug (só em dev; mostra info do banco)       |
| POST   | /auth/register             | Não   | Cadastro (email + senha → token)              |
| POST   | /auth/login                | Não   | Login (email + senha → token)                 |
| GET    | /jobs                      | Sim   | Lista jobs do usuário (paginação)             |
| POST   | /jobs                      | Sim   | Upload de arquivo → cria job                  |
| GET    | /jobs/{id}                 | Sim   | Status e metadados do job                     |
| GET    | /jobs/{id}/preview         | Sim   | 20 linhas do CSV em JSON (status=done)        |
| GET    | /jobs/{id}/download        | Sim   | Download do CSV GHL (status=done)             |
| GET    | /jobs/{id}/report          | Sim   | Métricas do processamento (status=done)       |
| POST   | /jobs/{id}/retry           | Sim   | Reprocessa job falho (status=failed)          |
| GET    | /docs                      | Não   | Swagger (OpenAPI)                             |

---

## 9. Dependências (requirements.txt)

```
fastapi==0.109.2
uvicorn==0.27.1
python-multipart==0.0.9
sqlalchemy>=2.0.40
psycopg[binary]>=3.1.0
redis==5.0.1
rq==1.16.0
pandas>=2.0.0
openpyxl>=3.1.0
phonenumbers==8.13.29
python-dotenv==1.0.1
passlib[bcrypt]==1.7.4
PyJWT==2.8.0
email-validator==2.1.0
```

---

## 10. Variáveis de Ambiente

### Dev (.env local)
```env
POSTGRES_USER=ghluser
POSTGRES_PASSWORD=ghlpass
POSTGRES_DB=ghldb
DATABASE_URL=postgresql://ghluser:ghlpass@localhost:5432/ghldb
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=altere-isso-em-producao-use-uma-string-longa-e-aleatoria
```

### Produção (Render)
```env
ENV=production
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
JWT_SECRET=string-longa-aleatoria
CORS_ORIGINS=  (opcional; vazio usa ["*"])
```

---

## 11. Fluxo Completo (MVP Validado)

1. **Usuário se cadastra:** `POST /auth/register` → recebe `access_token`.
2. **Usuário faz login:** `POST /auth/login` → recebe `access_token`.
3. **Usuário faz upload:** `POST /jobs` (com header `Authorization: Bearer <token>`) → recebe `job_id`, status `queued`.
4. **Worker processa:** Redis + RQ consome o job, lê arquivo, normaliza, gera CSV GHL, preview, report, atualiza status para `done`.
5. **Usuário consulta status:** `GET /jobs/{id}` → vê status `done`.
6. **Usuário baixa preview:** `GET /jobs/{id}/preview` → JSON com 20 linhas.
7. **Usuário baixa report:** `GET /jobs/{id}/report` → métricas (total_rows, pct_with_email, pct_with_phone).
8. **Usuário baixa CSV:** `GET /jobs/{id}/download` → CSV no padrão GHL.

---

## 12. Correções e Ajustes Críticos Feitos

| Issue | Correção |
|-------|----------|
| POST 201 / GET 404 | Validação de UUID, .env loading robusto, debug endpoint |
| Worker crash no Windows | SimpleWorker (em vez de Worker com fork) |
| Senha exposta em logs | Mascaramento de DATABASE_URL nos logs |
| CORS bloqueando frontend | Em produção, se CORS_ORIGINS vazio, usa ["*"] |
| Upload sem limite | Limite de 10 MB (413 se exceder) |
| /debug/db exposto em prod | Condicional: só disponível se ENV != production |
| Autenticação ausente | JWT, tabela users, proteção de todos /jobs* |
| Jobs sem owner | user_id em jobs; usuário só vê seus próprios jobs |

---

## 13. Documentação Criada

| Arquivo | Conteúdo |
|---------|----------|
| AUDITORIA_COMPLETA.md | Auditoria técnica até o MVP |
| ROTEIRO_TESTE_BUG_FIX.md | Roteiro de teste do bug POST/GET |
| RELATORIO_PROXIMOS_PASSOS.md | Relatório para IA recomendar próximos passos |
| VALIDACAO_FLUXO_MVP.md | Checklist de validação do fluxo MVP |
| VALIDACAO_MELHORIAS.md | Instruções para validar melhorias opcionais |
| VALIDACAO_MVP_FASE1.md | Confirmação do MVP Fase 1 |
| AUDITORIA_E_PRODUCAO.md | Auditoria e roteiro para produção |
| VALIDACAO_FLOWBASE_MVP.md | Validação aderente à especificação MVP |

---

## 14. Estado Atual (31/01/2026)

### O que está pronto
- MVP Fase 1 funcional: upload → processamento → CSV GHL + preview + report + download.
- Autenticação com JWT.
- Backend em produção no Render.
- Frontend em desenvolvimento no Vercel/v0.
- CORS configurado (permite frontend em produção).
- Limite de upload (10 MB).
- Proteção de /debug/db em produção.
- Docker (Dockerfile, .dockerignore) para deploy.

### O que NÃO foi implementado (fora do escopo MVP)
- OAuth (Google, GitHub).
- Refresh token.
- Roles/permissões avançadas.
- Integração direta com GoHighLevel (enviar CSV via API).
- Stripe (pagamentos).
- Múltiplos workspaces/organizações.
- Deleção de jobs (DELETE /jobs/{id}).
- Testes automatizados (pytest).
- CI/CD (GitHub Actions).
- Logs estruturados (JSON).
- Health check avançado (Postgres + Redis).

---

## 15. Observações Importantes

### Limitações conhecidas
- **Windows:** Worker usa SimpleWorker (sem fork); adequado para dev e MVP, mas em Linux/produção poderia usar Worker padrão para melhor performance.
- **Mapeamento de colunas:** Sinônimos fixos PT/EN; sem interface para usuário customizar.
- **Jobs antigos:** Jobs com `user_id=NULL` (criados antes da auth) ficam invisíveis para todos os usuários.
- **CORS em produção:** Se `CORS_ORIGINS` não for definido, usa `["*"]` (aceita qualquer origem); para segurança, definir com URLs exatas do frontend.

### Próximos passos sugeridos (fora do escopo atual)
1. Testes automatizados (pytest para endpoints e processamento).
2. Logs estruturados (JSON) para monitoramento.
3. Health check avançado (verificar Postgres e Redis).
4. Integração com GoHighLevel (enviar CSV via API).
5. Stripe para monetização.
6. Frontend completo (React/Next.js) com autenticação e gestão de jobs.
7. CI/CD (deploy automático, testes antes do merge).
8. Backup automático do Postgres.
9. Rate limiting (evitar abuso de API).
10. Validação avançada de arquivos (não só extensão, mas conteúdo/magic bytes).

---

## 16. Comandos Úteis

### Dev local
```powershell
# Subir Postgres + Redis
docker-compose up -d

# Ativar venv e instalar dependências
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Rodar API
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Rodar worker (outro terminal)
python -m app.worker
```

### Deploy (Render)
```powershell
# Adicionar mudanças e fazer commit
git add .
git commit -m "mensagem"
git push origin main
```

### Build Docker local
```powershell
docker build -t flowbase-backend ./backend
docker run -p 8000:8000 --env-file .env flowbase-backend
```

---

## 17. Conclusão

O projeto **FlowBase** está completo para o **MVP Fase 1**:
- Upload de planilhas → processamento em background → CSV GHL + preview + report + download.
- Autenticação com JWT.
- Backend em produção (Render).
- CORS configurado para frontend em produção (Vercel/v0).
- Segurança básica: limite de upload, /debug/db restrito, JWT, user_id em jobs.

Para produção em escala, recomenda-se:
- Testes automatizados.
- Logs estruturados.
- Health check avançado.
- CI/CD.
- Backup automático.
- Rate limiting.
- Integração com GoHighLevel e Stripe (Fases 2/3).

Todos os arquivos estão no repositório, com commits documentados. O backend responde em `https://flowbase-y89b.onrender.com`.
