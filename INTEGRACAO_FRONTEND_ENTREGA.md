# Integração Frontend Next.js — Entrega FlowBase

**Objetivo:** Frontend que usa proxy Next.js para o backend (evita CORS e 401 por token).

---

## 1. O que foi alterado/criado

### Novo diretório: `frontend-next/`

| Arquivo | Descrição |
|---------|-----------|
| `package.json` | Next.js 14, React 18 |
| `next.config.js` | Config padrão |
| `tsconfig.json` | TypeScript com paths `@/*` |
| `.env.local.example` | Exemplo com `API_URL` (só servidor) |
| `.gitignore` | node_modules, .next, .env.local |
| `next-env.d.ts` | Tipos Next.js |
| `app/layout.tsx` | Layout com AuthProvider |
| `app/globals.css` | Estilos globais (tema escuro) |
| `app/page.tsx` | Redireciona para /login ou /dashboard |
| `app/login/page.tsx` | Tela de login (POST /api/proxy/auth/login) |
| `app/register/page.tsx` | Tela de cadastro (POST /api/proxy/auth/register) |
| `app/dashboard/page.tsx` | Upload, lista de jobs, preview/report/download, retry |
| `app/api/proxy/[...path]/route.ts` | Proxy GET/POST para o backend (usa `API_URL`) |
| `lib/api.ts` | Cliente: register, login, jobs list/get/upload/preview/report/download/retry; token em localStorage |
| `components/AuthProvider.tsx` | Contexto com token e setToken |
| `README.md` | Env vars, como rodar e como testar |

### Backend

- **Nenhuma alteração.** O frontend não chama o backend direto do navegador; todas as chamadas passam pelo proxy Next.js. CORS no backend não afeta esse fluxo.

---

## 2. Configurar variáveis no Vercel

1. No Vercel: projeto do frontend → **Settings** → **Environment Variables**.
2. Adicione:

| Nome    | Valor                               | Ambiente   |
|---------|-------------------------------------|------------|
| `API_URL` | `https://flowbase-y89b.onrender.com` | Production (e Preview se quiser) |

- **Não** use `NEXT_PUBLIC_` em `API_URL`: ela é usada só no servidor (rotas `/api/proxy/...`).
- O cliente só chama `/api/proxy/...`; o Next.js faz a requisição ao backend usando `API_URL`.

---

## 3. Fluxo de auth e token

1. **Cadastro:** `POST /api/proxy/auth/register` (body: email, password) → resposta com `access_token` → salvo em `localStorage` (chave `flowbase_token`) e no contexto.
2. **Login:** `POST /api/proxy/auth/login` (body: email, password) → resposta com `access_token` → mesmo armazenamento.
3. **Requisições protegidas:** Todas as chamadas a `/api/proxy/jobs` (e subrotas) enviam o header `Authorization: Bearer <token>` (token lido do `localStorage` em `lib/api.ts`).
4. **Logout:** Remove o token do `localStorage` e do contexto e redireciona para `/login`.

---

## 4. Checklist

- [x] Cadastro funciona (POST /api/proxy/auth/register).
- [x] Login funciona (POST /api/proxy/auth/login).
- [x] Token é persistido (localStorage + AuthProvider).
- [x] Upload envia Bearer token (apiJobUpload usa getAuthHeaders()).
- [x] Lista de jobs, preview, report e download funcionam (todas as chamadas passam pelo proxy com Authorization).
- [x] Retry para jobs com status failed.

---

## 5. Como testar em 3 passos

### Passo 1 — Cadastrar

1. Acesse a URL do frontend (ex.: `https://seu-app.vercel.app` ou `http://localhost:3000`).
2. Clique em **Cadastre-se**.
3. Preencha email e senha (mínimo 6 caracteres) e clique em **Cadastrar**.
4. Deve redirecionar para o dashboard (e o token ficar salvo).

### Passo 2 — Logar

1. Se já tiver conta: na home, clique em **Entrar**.
2. Digite email e senha e clique em **Entrar**.
3. Deve redirecionar para o dashboard.

### Passo 3 — Enviar arquivo e ver job concluir

1. No dashboard, clique na área **“Clique aqui ou arraste um arquivo”** e escolha um .csv ou .xlsx (até 10 MB).
2. Deve aparecer “Job em andamento” e, em alguns segundos, o job na lista com status **done** (ou **failed** se o backend/worker falhar).
3. Para um job **done**: use **Preview**, **Report** e **Baixar CSV** para validar.

---

## 6. Rodar localmente

```bash
cd frontend-next
cp .env.local.example .env.local
npm install
npm run dev
```

Acesse: http://localhost:3000

O backend usado é o de produção (`https://flowbase-y89b.onrender.com`) definido em `API_URL` no `.env.local` (ou no Vercel).

---

## 7. Deploy no Vercel

- Conecte o repositório ao Vercel (pasta raiz ou monorepo; se for monorepo, defina **Root Directory** como `frontend-next`).
- Configure `API_URL=https://flowbase-y89b.onrender.com` nas variáveis de ambiente.
- Deploy automático a cada push.

---

## 8. Observação sobre CORS

Com o proxy Next.js, o **navegador nunca chama o backend diretamente**. Todas as requisições são para o mesmo domínio do frontend (`/api/proxy/...`), então **não há CORS** entre frontend e backend. O backend pode manter `CORS_ORIGINS` restrito ou vazio; o frontend continua funcionando. Não é necessário usar `allow_origins=["*"]` em produção por causa deste frontend.
