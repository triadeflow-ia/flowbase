# Relatório completo — GHL Data SaaS

**Data:** 31/01/2026  
**Objetivo:** Permitir análise por IA para recomendar os próximos passos do projeto.

---

## 1. Resumo executivo

- **Projeto:** GHL Data SaaS — SaaS local que converte planilhas (XLSX/CSV) para o formato de importação do GoHighLevel.
- **MVP Fase 1:** Implementado e testado (upload → job em background → CSV GHL + preview + report → status e download).
- **Stack:** Python, FastAPI, Postgres, Redis, RQ, pandas, phonenumbers. Tudo local (Docker para Postgres/Redis).
- **Plano original:** Fases 2/3 (frontend, auth) e Fase 3/4 (Stripe, integração GHL) ainda não implementadas.

---

## 2. Estado atual do projeto

### 2.1 O que está pronto

| Item | Status |
|------|--------|
| Docker Compose (Postgres + Redis) | OK |
| FastAPI com endpoints de jobs | OK |
| Upload de XLSX/CSV | OK |
| Job em background (RQ + SimpleWorker no Windows) | OK |
| Processamento: mapeamento PT/EN, normalização email/telefone | OK |
| CSV no padrão GHL | OK |
| Preview (20 linhas JSON) | OK |
| Report (total_rows, pct_with_email, pct_with_phone) | OK |
| Download do CSV | OK |
| Consulta de status do job | OK |
| Tabela `jobs` no Postgres | OK |
| Validação de UUID em job_id (422 se inválido) | OK |
| Endpoint de debug GET /debug/db (DATABASE_URL mascarada, current_database, current_user, jobs_count) | OK |
| Logs no startup (banco conectado, .env carregado) | OK |

### 2.2 Correções recentes (bug POST 201 / GET 404)

- **Problema:** POST /jobs retornava 201 com job_id, mas GET /jobs/{id} retornava 404.
- **Ajustes feitos:**
  - Carga mais robusta do `.env` (vários caminhos).
  - Endpoint GET /debug/db para inspeção do banco em uso.
  - Logs no startup (DATABASE_URL mascarada, driver, conexão).
  - Validação de `job_id` como UUID (422 se inválido, ex.: "GET /jobs/" concatenado).
  - Rejeição explícita de SQLite em DATABASE_URL.

---

## 3. O que NÃO existe ainda

| Item | Descrição |
|------|-----------|
| Frontend | Pasta `frontend/` vazia. MVP usa /docs do FastAPI. |
| Autenticação | Nenhum login, sessão ou JWT. |
| Múltiplos usuários | Apenas um “ambiente” local. |
| Stripe | Sem pagamentos. |
| Integração GHL | Sem chamada à API do GoHighLevel. |
| Listagem de jobs | Não há GET /jobs (lista). Apenas GET /jobs/{id}. |
| Deleção de jobs | Não há DELETE /jobs/{id}. |
| Retry de jobs falhos | Não há reprocessamento. |
| Testes automatizados | Sem pytest ou outros testes. |
| CI/CD | Sem GitHub Actions ou pipeline. |
| Dockerização do backend | Backend roda local (venv), não em container. |
| Logs estruturados | Apenas logs básicos no startup. |

---

## 4. Limitações e pontos de atenção

- **Windows:** Worker usa SimpleWorker (RQ sem fork); adequado para dev e MVP.
- **Segurança:** Sem auth; adequado apenas para uso local.
- **Concorrência:** Um worker; para mais throughput, rodar vários processos de worker.
- **Mapeamento de colunas:** Sinônimos fixos PT/EN; sem mapeamento customizável pelo usuário.
- **Encoding CSV:** Leitura UTF-8 e latin-1; escrita utf-8-sig.
- **Preview/report:** Caminhos por convenção; sem coluna `preview_json_path` na tabela.

---

## 5. Estrutura de arquivos atual

```
ghl-data-saas/
├── .env, .env.example
├── docker-compose.yml
├── AUDITORIA_COMPLETA.md      # Auditoria técnica detalhada
├── ROTEIRO_TESTE_BUG_FIX.md   # Roteiro de teste do bug POST/GET
├── RELATORIO_PROXIMOS_PASSOS.md  # Este documento
├── backend/
│   ├── app/
│   │   ├── config.py, db.py, main.py, models.py
│   │   ├── processing.py, queue_rq.py, routes_jobs.py
│   │   ├── storage.py, worker.py
│   ├── storage/uploads/, outputs/, reports/
│   ├── requirements.txt, README.md, test_data.csv
└── frontend/
    └── .gitkeep
```

---

## 6. Endpoints disponíveis

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | /health | Health check |
| GET | /debug/db | Debug: banco em uso, contagem de jobs |
| POST | /jobs | Upload e criação de job |
| GET | /jobs/{job_id} | Status e metadados do job |
| GET | /jobs/{job_id}/preview | Preview (20 linhas) |
| GET | /jobs/{job_id}/download | Download do CSV GHL |
| GET | /jobs/{job_id}/report | Métricas do processamento |

---

## 7. Perguntas para a IA decidir

1. **Ordem de prioridade:** Qual sequência faz mais sentido?
   - Frontend (React/HTML) vs autenticação vs listagem de jobs vs integração GHL vs Stripe?

2. **Frontend:** Qual abordagem?
   - Página HTML simples vs React/Vite vs outro framework?

3. **Autenticação:** O que é mínimo para um SaaS?
   - Login/senha vs OAuth (Google) vs magic link?
   - Onde armazenar usuários (Postgres, tabela nova)?

4. **Integração GHL:** Qual escopo inicial?
   - Apenas validação do formato CSV vs upload via API do GHL vs webhook?

5. **Deploy:** Onde hospedar?
   - VPS vs Railway/Render vs AWS/GCP vs outro?

6. **Testes:** Vale a pena adicionar pytest e cobertura de endpoints agora?

7. **Docker:** Vale a pena dockerizar o backend (Dockerfile + docker-compose completo)?

---

## 8. Informações adicionais para a IA

- **Usuário:** Não é desenvolvedor; precisa de orientação passo a passo.
- **Ambiente:** Windows, PowerShell, Cursor como IDE.
- **Repositório:** Projeto em OneDrive (`ghl-data-saas`).
- **Documentação de referência:** AUDITORIA_COMPLETA.md com detalhes técnicos.
- **Restrições conhecidas:** Manter FastAPI + SQLAlchemy + psycopg3 + RQ; não alterar stack de forma disruptiva.

---

## 9. Solicitação à IA

Com base neste relatório, pede-se à IA que:

1. **Analise** o estado atual e as lacunas listadas.
2. **Priorize** os próximos passos (top 5–10 itens) com breve justificativa.
3. **Proponha** uma ordem de execução (checkpoints ou sprints).
4. **Indique** o que fazer primeiro e o que pode esperar.
5. **Sugira** estimativas (se possível) de esforço relativo (baixo/médio/alto) para cada item.
6. **Identifique** riscos ou dependências entre os itens.

Este relatório pode ser usado como prompt para a IA responder com um plano de próximos passos.
