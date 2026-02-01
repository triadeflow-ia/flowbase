# Auditoria Completa — GHL Data SaaS (MVP Fase 1)

**Data:** 31/01/2026  
**Objetivo do documento:** Permitir análise por outra IA ou equipe técnica (estado atual do projeto, decisões e limitações).

---

## 1. Contexto e objetivo do MVP

### 1.1 Objetivo declarado (Fase 1)

- **Entrada:** Upload de planilha `.xlsx` ou `.csv`.
- **Processo:** Criação de um **Job** e processamento em **background** (fila).
- **Saídas geradas:**
  - CSV no padrão de importação do **GoHighLevel (GHL)**.
  - **Preview** (20 linhas) em JSON.
  - **report.json** com métricas.
- **Uso:** Consultar status do job, baixar o CSV final.

### 1.2 Fora do escopo (Fase 1)

- Stripe, OAuth, autenticação de usuário.
- Importação real no GHL (API ou integração).
- Frontend elaborado (MVP usa `/docs` do FastAPI para testes).

---

## 2. Stack técnica

| Componente | Tecnologia | Observação |
|------------|------------|------------|
| Linguagem | Python 3.x | Projeto testado com Python 3.14. |
| API HTTP | FastAPI | Servidor que expõe os endpoints. |
| Servidor ASGI | Uvicorn | Comando: `uvicorn app.main:app --host 0.0.0.0 --port 8000`. |
| Banco de dados | PostgreSQL 15 | Via Docker (container `ghl-postgres`). |
| Driver do banco | psycopg3 (`psycopg[binary]`) | Substitui psycopg2-binary (problemas de build no Windows). |
| ORM | SQLAlchemy >= 2.0.40 | Versão mínima por compatibilidade com Python 3.14. |
| Fila de tarefas | Redis + RQ | Redis via Docker (`ghl-redis`); RQ enfileira e processa jobs. |
| Processamento de planilhas | pandas + openpyxl | Leitura de XLSX/CSV. |
| Normalização de telefones | phonenumbers | Formato E.164 (default BR +55). |
| Variáveis de ambiente | python-dotenv + .env | `.env` na raiz do projeto; `config.py` carrega a partir de `ROOT_DIR`. |

---

## 3. Estrutura do repositório

```
ghl-data-saas/
├── .env                    # Variáveis locais (não versionado; criado a partir de .env.example)
├── .env.example            # Modelo de variáveis (Postgres, Redis)
├── docker-compose.yml      # Postgres + Redis (sem atributo version)
├── AUDITORIA_COMPLETA.md  # Este documento
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py       # DATABASE_URL, REDIS_URL, pastas de storage
│   │   ├── db.py           # Engine SQLAlchemy, SessionLocal, get_db, Base
│   │   ├── main.py         # FastAPI, lifespan (create_all), router de jobs, GET /health
│   │   ├── models.py       # Modelo Job (tabela jobs)
│   │   ├── processing.py   # Pipeline: leitura, mapeamento, normalização, CSV GHL, report, preview
│   │   ├── queue_rq.py     # Fila RQ (Redis) para enfileirar process_job
│   │   ├── routes_jobs.py  # POST /jobs, GET /jobs/{id}, /preview, /download, /report
│   │   ├── storage.py      # allowed_file, save_upload (uploads)
│   │   └── worker.py       # Worker RQ (SimpleWorker no Windows)
│   ├── storage/
│   │   ├── uploads/        # Arquivos enviados (nome: {job_id}.xlsx ou .csv)
│   │   ├── outputs/        # CSVs gerados no padrão GHL
│   │   └── reports/        # report.json e preview JSON por job
│   ├── requirements.txt
│   ├── README.md
│   └── test_data.csv       # CSV de exemplo para testes
└── frontend/
    └── .gitkeep            # Pasta vazia (previsto para fases futuras)
```

---

## 4. Checkpoints executados (A a G)

| Checkpoint | Descrição | Status |
|------------|-----------|--------|
| **A** | Docker Compose + subir Postgres e Redis | ✅ Concluído |
| **B** | Venv + requirements + GET /health | ✅ Concluído |
| **C** | Tabela jobs + conexão Postgres (db.py, models.py, create_all no startup) | ✅ Concluído |
| **D** | POST /jobs (upload, salvar arquivo, criar job no banco) | ✅ Concluído |
| **E** | Worker RQ + processamento (CSV GHL, report, preview) | ✅ Concluído |
| **F** | Endpoints GET status, preview, download, report | ✅ Concluído |
| **G** | Testes manuais com CSV real | ✅ Concluído (test_data.csv) |

---

## 5. Endpoints implementados

| Método | Rota | Descrição | Observação |
|--------|------|-----------|------------|
| GET | /health | Health check do servidor | Retorna `{"status":"ok"}`. |
| POST | /jobs | Upload de arquivo .xlsx ou .csv | Cria job (status `queued`), salva arquivo, enfileira `process_job(job_id)`. Retorna `id`, `status`, `filename_original`, `created_at`. |
| GET | /jobs/{job_id} | Status e metadados do job | Retorna todos os campos do job (incl. paths e error_message). |
| GET | /jobs/{job_id}/preview | Primeiras 20 linhas do resultado em JSON | 409 se status ≠ done; 404 se arquivo de preview não existir. |
| GET | /jobs/{job_id}/download | Download do CSV no padrão GHL | Nome do arquivo: `ghl_import_{job_id}.csv`. 409 se status ≠ done. |
| GET | /jobs/{job_id}/report | report.json com métricas | 409 se status ≠ done. |

---

## 6. Banco de dados (PostgreSQL)

### 6.1 Tabela `jobs`

| Coluna | Tipo | Observação |
|--------|------|------------|
| id | VARCHAR(36) | UUID string, PK. |
| status | VARCHAR(20) | Valores: `queued`, `processing`, `done`, `failed`. |
| filename_original | VARCHAR(255) | Nome do arquivo enviado. |
| file_path | VARCHAR(512) | Caminho absoluto do arquivo salvo em `storage/uploads/`. |
| output_csv_path | VARCHAR(512) NULL | Caminho absoluto do CSV gerado (preenchido quando status=done). |
| report_json_path | VARCHAR(512) NULL | Caminho absoluto do report JSON (preenchido quando status=done). |
| created_at | TIMESTAMP | Preenchido na criação. |
| updated_at | TIMESTAMP | Atualizado em alterações. |
| error_message | TEXT NULL | Mensagem de erro quando status=failed. |

### 6.2 Criação das tabelas

- No **startup** do FastAPI (`lifespan` em `main.py`): `Base.metadata.create_all(bind=engine)`.
- URL de conexão: `DATABASE_URL` do `.env`. O `db.py` converte `postgresql://` para `postgresql+psycopg://` quando necessário (driver psycopg3).

---

## 7. Pipeline de processamento (processing.py)

### 7.1 Fluxo

1. **Leitura:** `read_file(path)` — pandas: `.xlsx` via openpyxl, `.csv` com encoding UTF-8 ou latin-1 (fallback).
2. **Mapeamento de colunas:** Sinônimos PT/EN (normalização de nome de coluna: minúsculo, espaços) mapeiam para colunas GHL. Primeira coluna que bater com o sinônimo é usada.
3. **Normalização:**
   - **Emails:** minúsculas, separadores `,`, `;`, espaço; deduplicação.
   - **Telefones:** biblioteca `phonenumbers`, formato E.164, região default BR (+55).
4. **Saída GHL:** DataFrame com colunas na ordem fixa (GHL_COLUMNS). Dados não mapeados vão para a coluna Notes.
5. **Arquivos gerados:**
   - CSV: `storage/outputs/{job_id}.csv` (encoding utf-8-sig).
   - Report: `storage/reports/{job_id}_report.json` (total_rows, rows_output, pct_with_email, pct_with_phone, created_at).
   - Preview: `storage/reports/{job_id}_preview.json` (primeiras 20 linhas do resultado em JSON).

### 7.2 Colunas GHL (ordem fixa)

Full Name, Company Name, Email, Additional Emails, Phone, Additional Phone Numbers, Website, City, State, Tags, Notes, Source.

### 7.3 Sinônimos de colunas (exemplos)

- Full Name: nome, name, nome completo, contato.
- Company Name: company, empresa, razão social, razao social.
- Email: email, e-mail, mail.
- Phone: telefone, phone, celular, fone, mobile.
- City/State: cidade, city, estado, state, uf.
- Website: site, website, url.
- Notes/Source: notas, observações, origem, source.

### 7.4 Execução do processamento

- Função `process_job(job_id)` em `processing.py`.
- Atualiza o job no banco (status `processing` → `done` ou `failed`, paths e `error_message`).
- Chamada via **RQ:** enfileirada em `routes_jobs.py` após criar o job (`queue.enqueue(process_job, job_id)`).
- Worker roda em **processo separado** do FastAPI (`python -m app.worker`).

---

## 8. Worker RQ e ambiente Windows

- **Problema:** RQ usa `os.fork()`, que não existe no Windows.
- **Solução adotada:** Uso de `SimpleWorker` (classe do RQ) em vez de `Worker` em `worker.py`. Tarefas são executadas no mesmo processo (sem fork).
- **Implicação:** No Windows o worker não usa processos filhos; em Linux pode-se trocar para `Worker` para isolamento por processo, se desejado.

---

## 9. Desvios em relação ao plano original

| Item | Plano original | Implementado | Motivo |
|------|----------------|--------------|--------|
| Driver Postgres | psycopg2-binary | psycopg[binary] (psycopg3) | Build do psycopg2-binary falhava no Windows (pg_config). |
| SQLAlchemy | 2.0.25 | >= 2.0.40 | Compatibilidade com Python 3.14 (TypingOnly/AssertionError em 2.0.25). |
| pandas | 2.2.0 fixo | >= 2.0.0 | Evitar compilação no Windows; uso de wheel disponível. |
| docker-compose | version "3.8" | Sem version | Aviso de obsoleto; removido. |
| Worker no Windows | Worker RQ | SimpleWorker | RQ não suporta fork no Windows. |

---

## 10. Dependências (requirements.txt)

- fastapi==0.109.2, uvicorn==0.27.1  
- python-multipart==0.0.9  
- sqlalchemy>=2.0.40, psycopg[binary]>=3.1.0  
- redis==5.0.1, rq==1.16.0  
- pandas>=2.0.0, openpyxl>=3.1.0  
- phonenumbers==8.13.29  
- python-dotenv==1.0.1  

---

## 11. Como rodar o projeto

### 11.1 Pré-requisitos

- Python 3.10+ (testado com 3.14).
- Docker Desktop (Postgres e Redis).

### 11.2 Comandos (Windows PowerShell, a partir da raiz do projeto)

1. **Variáveis de ambiente:**  
   `copy .env.example .env` (ajustar se necessário).

2. **Subir Postgres e Redis:**  
   `docker-compose up -d`

3. **Backend (venv já criado e dependências instaladas):**  
   - Terminal 1 (API):  
     `cd backend` → `.\venv\Scripts\Activate.ps1` → `uvicorn app.main:app --host 0.0.0.0 --port 8000`  
   - Terminal 2 (worker):  
     `cd backend` → `.\venv\Scripts\Activate.ps1` → `python -m app.worker`

4. **Testes:**  
   - Documentação interativa: http://localhost:8000/docs  
   - Health: http://localhost:8000/health  
   - Upload: POST /jobs com arquivo .xlsx ou .csv; em seguida GET /jobs/{id}, /preview, /report, /download quando status=done.

---

## 12. Arquivos criados ou alterados (resumo)

| Arquivo | Ação | Descrição breve |
|---------|------|------------------|
| docker-compose.yml | Criado | Postgres 15 + Redis 7. |
| .env.example | Criado | Modelo de DATABASE_URL e REDIS_URL. |
| backend/requirements.txt | Criado/ajustado | Dependências + SQLAlchemy >= 2.0.40, psycopg3. |
| backend/README.md | Criado/atualizado | Instruções e nota sobre SimpleWorker no Windows. |
| backend/app/config.py | Criado | ROOT_DIR, load_dotenv, DATABASE_URL, REDIS_URL, pastas de storage. |
| backend/app/db.py | Criado | Engine, SessionLocal, get_db, conversão postgresql+psycopg. |
| backend/app/models.py | Criado | Modelo Job (tabela jobs). |
| backend/app/main.py | Criado/alterado | FastAPI, lifespan (create_all), include_router(jobs), GET /health. |
| backend/app/storage.py | Criado | allowed_file, save_upload. |
| backend/app/processing.py | Criado | Leitura, mapeamento, normalização, CSV GHL, report, preview. |
| backend/app/queue_rq.py | Criado | Fila RQ (Redis). |
| backend/app/worker.py | Criado | SimpleWorker, run_worker. |
| backend/app/routes_jobs.py | Criado | POST /jobs, GET /jobs/{id}, /preview, /download, /report. |
| backend/storage/uploads|outputs|reports | Criados | Pastas com .gitkeep. |
| backend/test_data.csv | Criado | CSV de exemplo (nome, email, telefone, empresa, cidade, estado). |

---

## 13. Limitações e pontos de atenção

- **Windows:** Worker usa SimpleWorker (sem fork); adequado para desenvolvimento e MVP.
- **Preview/report:** Caminhos derivados por convenção (`{job_id}_preview.json`, `{job_id}_report.json`) em `REPORTS_DIR`; não há coluna `preview_json_path` na tabela.
- **Encoding CSV:** Leitura de CSV com UTF-8 e fallback para latin-1; escrita do CSV GHL em utf-8-sig.
- **Concorrência:** Um worker; para mais throughput pode-se rodar vários processos de worker (cada um consumindo da mesma fila).
- **Segurança/autenticação:** Nenhuma; MVP local sem auth.

---

## 14. Conclusão da auditoria

- **Escopo do MVP Fase 1:** Atendido (upload → job em background → CSV GHL + preview + report → status e download).
- **Checkpoints A–G:** Concluídos.
- **Stack e estrutura:** Conformes ao planejado, com os desvios documentados (psycopg3, SQLAlchemy, SimpleWorker no Windows).
- **Próximos passos possíveis (fora desta auditoria):** Fase 2/3 (frontend, autenticação), Fase 3/4 (Stripe, integração GHL), melhorias de mapeamento de colunas e tratamento de erros.

Este documento reflete o estado do repositório e das decisões técnicas na data indicada, para uso em análise por IA ou equipe técnica.
