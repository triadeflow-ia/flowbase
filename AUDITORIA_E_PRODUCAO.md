# Auditoria Completa e Roteiro para Produção — GHL Data SaaS

**Data:** 31/01/2026  
**Objetivo:** Documentar tudo que foi feito e o que falta para colocar em produção.

---

## Parte 1 — Auditoria Completa (O que foi feito)

### 1.1 Estrutura do Projeto

```
ghl-data-saas/
├── .env                    # Variáveis locais (não versionado)
├── .env.example            # Template de variáveis
├── docker-compose.yml      # Postgres + Redis
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py       # Configurações (DATABASE_URL, REDIS_URL, pastas)
│   │   ├── db.py           # SQLAlchemy + psycopg3
│   │   ├── main.py         # FastAPI, CORS, rotas raiz
│   │   ├── models.py       # Modelo Job
│   │   ├── processing.py   # Pipeline de conversão XLSX/CSV → GHL
│   │   ├── queue_rq.py     # Fila Redis (RQ)
│   │   ├── routes_jobs.py  # Endpoints de jobs
│   │   ├── storage.py      # Upload e validação de arquivos
│   │   └── worker.py       # Worker RQ (SimpleWorker para Windows)
│   ├── storage/
│   │   ├── uploads/        # Arquivos enviados
│   │   ├── outputs/        # CSVs gerados
│   │   └── reports/        # preview.json, report.json
│   ├── requirements.txt
│   ├── README.md
│   └── test_data.csv
└── frontend/
    └── index.html          # Interface única (HTML + CSS + JS)
```

### 1.2 Backend — API FastAPI

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Serve o frontend (index.html) |
| `/health` | GET | Health check `{"status":"ok"}` |
| `/debug/db` | GET | Debug: banco em uso, contagem de jobs |
| `/jobs` | GET | Lista jobs (limit, offset, status) |
| `/jobs` | POST | Upload de arquivo → cria job → enfileira |
| `/jobs/{id}` | GET | Status e metadados do job |
| `/jobs/{id}/preview` | GET | 20 linhas do CSV em JSON (status=done) |
| `/jobs/{id}/report` | GET | Métricas (total_rows, pct_with_email, pct_with_phone) |
| `/jobs/{id}/download` | GET | Download do CSV no padrão GHL |
| `/jobs/{id}/retry` | POST | Reprocessa job falho |
| `/docs` | GET | Swagger (OpenAPI) |

**Configurações:**
- CORS: `allow_origins=["*"]` (aberto para qualquer origem)
- Frontend servido na raiz (`/`)
- Tabela `jobs` criada automaticamente no startup

### 1.3 Banco de Dados (PostgreSQL)

**Tabela `jobs`:**

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | VARCHAR(36) | UUID, chave primária |
| status | VARCHAR(20) | queued, processing, done, failed |
| filename_original | VARCHAR(255) | Nome do arquivo enviado |
| file_path | VARCHAR(512) | Caminho absoluto do upload |
| output_csv_path | VARCHAR(512) | Caminho do CSV gerado (null se não feito) |
| report_json_path | VARCHAR(512) | Caminho do report (null se não feito) |
| created_at | TIMESTAMP | Data de criação |
| updated_at | TIMESTAMP | Última atualização |
| error_message | TEXT | Mensagem de erro (se failed) |

**Driver:** `postgresql+psycopg` (psycopg3)  
**Rejeição:** SQLite e `:memory:` bloqueados em `config.py`

### 1.4 Processamento (Worker RQ)

- **Fila:** Redis, nome `default`
- **Worker:** `SimpleWorker` (compatível com Windows; sem `os.fork()`)
- **Pipeline:** `process_job(job_id)` em `processing.py`
  1. Atualiza status para `processing`
  2. Lê arquivo (XLSX ou CSV)
  3. Mapeia colunas por sinônimos PT/EN
  4. Normaliza emails e telefones (E.164, BR +55)
  5. Gera CSV padrão GHL (12 colunas)
  6. Gera `report.json` (total_rows, pct_with_email, pct_with_phone)
  7. Gera `preview.json` (20 linhas)
  8. Atualiza status para `done` ou `failed`

### 1.5 Frontend

- **Arquivo único:** `frontend/index.html`
- **Tecnologias:** HTML, CSS, JavaScript (sem framework)
- **Funcionalidades:**
  - Upload por drag & drop ou clique
  - Polling de status do job
  - Lista de jobs recentes
  - Preview, report, download quando status=done
  - Retry para jobs falhos

### 1.6 Docker Compose

- **postgres:** imagem `postgres:15`, porta 5432, volumes persistentes
- **redis:** imagem `redis:7-alpine`, porta 6379, volumes persistentes
- **Backend e worker:** rodam fora do Docker (venv local)

### 1.7 Validações e Tratamento de Erros

- Validação de UUID em `job_id` (422 se inválido)
- Extensões permitidas: `.xlsx`, `.csv`
- Retorno de erros: 400, 404, 409, 422 conforme cenário
- Tratamento de exceção no worker (status `failed` em caso de erro)

---

## Parte 2 — O que Falta para Produção

### 2.1 Segurança (Crítico)

| Item | Situação Atual | O que fazer |
|------|----------------|-------------|
| **Autenticação** | Nenhuma | Implementar login (JWT, OAuth ou magic link) |
| **CORS** | `allow_origins=["*"]` | Restringir para o domínio do frontend em produção |
| **HTTPS** | Não configurado | Usar TLS (via proxy reverso ou provedor) |
| **Endpoint /debug/db** | Exposto | Desativar ou proteger em produção |
| **.env** | Na raiz | Garantir que não seja versionado; usar variáveis do ambiente em produção |
| **Secrets** | Em .env | Usar secrets do provedor (Railway, Render, etc.) |
| **Rate limiting** | Inexistente | Limitar requisições por IP/usuário |
| **Validação de arquivo** | Apenas extensão | Adicionar limite de tamanho (ex: 10 MB) |

### 2.2 Infraestrutura

| Item | Situação Atual | O que fazer |
|------|----------------|-------------|
| **Backend em container** | Roda local (venv) | Criar Dockerfile e incluir no docker-compose |
| **Worker em container** | Roda local | Rodar worker como serviço separado ou no mesmo container com supervisor |
| **Postgres/Redis** | Docker local | Migrar para serviço gerenciado (ex: Railway Postgres, Redis Cloud) ou VPS |
| **Storage (uploads/outputs)** | Disco local | Usar volume persistente ou S3/storage externo |
| **Variáveis de ambiente** | .env local | Definir no painel do provedor de deploy |

### 2.3 Aplicação

| Item | Situação Atual | O que fazer |
|------|----------------|-------------|
| **Tamanho máximo de arquivo** | Sem limite | Definir limite (ex: 10 MB) no FastAPI e no upload |
| **Migrações de banco** | `create_all` | Avaliar uso de Alembic para migrações controladas |
| **Logs** | Básicos | Logs estruturados (JSON) para produção |
| **Health check** | Simples | Incluir checagem de Postgres e Redis no /health |
| **Múltiplos workers** | Um worker | Escalar workers conforme carga |

### 2.4 DevOps e Monitoramento

| Item | Situação Atual | O que fazer |
|------|----------------|-------------|
| **CI/CD** | Inexistente | GitHub Actions (testes, build, deploy) |
| **Testes** | Inexistente | Pytest para endpoints e processamento |
| **Monitoramento** | Nenhum | Logs centralizados, alertas (erros, fila parada) |
| **Backup** | Manual | Backup automático do Postgres e do storage |

### 2.5 Funcionalidades Futuras (não obrigatórias para MVP em produção)

| Item | Descrição |
|------|------------|
| Múltiplos usuários | Cada usuário vê só seus jobs |
| Integração GHL | Enviar CSV diretamente para o GoHighLevel |
| Stripe | Pagamentos e planos |
| Mapeamento de colunas | Usuário escolhe quais colunas mapear |
| Deleção de jobs | Endpoint DELETE /jobs/{id} |

---

## Parte 3 — Roteiro para Produção (Ordem sugerida)

### Fase 1 — Pré-produção (obrigatório)

1. **Criar `.gitignore` na raiz** (se não existir)
   - `.env`, `venv/`, `__pycache__/`, `*.pyc`, `storage/uploads/*`, `storage/outputs/*`, `storage/reports/*`

2. **Desativar ou proteger `/debug/db` em produção**
   - Ex: só ativar se `ENV=development` ou `DEBUG=true`

3. **Restringir CORS**
   - Variável `CORS_ORIGINS` em .env (ex: `https://seu-dominio.com`)

4. **Limite de tamanho de arquivo**
   - Ex: 10 MB no FastAPI e validação no upload

5. **Remover ou proteger dados sensíveis**
   - Garantir que `.env` não vá para o repositório

### Fase 2 — Containerização

6. **Dockerfile do backend**
   - Imagem Python, `pip install`, `uvicorn app.main:app`

7. **docker-compose.yml completo**
   - Serviços: postgres, redis, api, worker
   - Variáveis de ambiente via `env_file` ou `environment`

### Fase 3 — Autenticação

8. **Implementar login básico**
   - JWT ou sessão simples; tabela `users`; proteção dos endpoints de jobs

### Fase 4 — Deploy

9. **Escolher provedor**
   - Ex: Railway, Render, Fly.io, AWS, VPS

10. **Configurar serviços**
    - Postgres e Redis gerenciados ou em containers
    - Variáveis de ambiente no painel
    - Domínio e SSL (HTTPS)

11. **Executar deploy**
    - Push para branch principal ou CI/CD
    - Verificar health check e fluxo completo

### Fase 5 — Pós-deploy

12. **Monitoramento**
    - Logs, alertas, métricas

13. **Backup**
    - Postgres e storage conforme SLA

---

## Parte 4 — Resumo Executivo

### O que está pronto

- MVP Fase 1 funcional: upload → processamento em background → CSV GHL + preview + report + download
- Frontend integrado
- Docker para Postgres e Redis
- Validações e tratamento de erros básicos

### O que é crítico antes de produção

1. **Autenticação** — sem isso, qualquer pessoa acessa o sistema
2. **HTTPS** — obrigatório para dados em trânsito
3. **Desativar /debug/db** — evita expor informações sensíveis
4. **Restringir CORS** — reduz superfície de ataque
5. **Limite de tamanho de arquivo** — evita abuso

### Estimativa de esforço (relativa)

| Fase | Esforço | Observação |
|------|---------|------------|
| Pré-produção (itens 1–5) | Baixo | Ajustes pontuais |
| Containerização | Médio | Dockerfile + compose |
| Autenticação | Médio–Alto | Depende da abordagem |
| Deploy | Médio | Depende do provedor |
| Monitoramento | Baixo–Médio | Logs e alertas |

---

**Conclusão:** O MVP está completo para uso local. Para produção, é necessário tratar segurança (auth, CORS, HTTPS, /debug/db), containerizar a aplicação e escolher um provedor de deploy. A ordem acima garante que os riscos mais graves sejam endereçados primeiro.
