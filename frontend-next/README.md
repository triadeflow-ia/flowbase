# FlowBase — Frontend Next.js

Frontend Next.js que se comunica com o backend FlowBase via **proxy API** (evita CORS e não expõe o backend no cliente).

## Variáveis de ambiente (Vercel)

No painel do Vercel → **Settings** → **Environment Variables**, adicione:

| Nome     | Valor                               | Ambiente  |
|----------|-------------------------------------|-----------|
| `API_URL` | `https://flowbase-y89b.onrender.com` | Production (e Preview se quiser) |

- **Não** use `NEXT_PUBLIC_` para `API_URL`: a URL do backend é usada apenas no servidor (rotas de proxy).
- O frontend chama sempre `/api/proxy/...`; o Next.js encaminha para `API_URL` no servidor.

## Desenvolvimento local

```bash
cd frontend-next
cp .env.local.example .env.local
# Edite .env.local se precisar (API_URL já aponta para o backend em produção)
npm install
npm run dev
```

Acesse: http://localhost:3000

## Build e deploy (Vercel)

- Conecte o repositório ao Vercel.
- Defina `API_URL=https://flowbase-y89b.onrender.com` nas variáveis de ambiente.
- Deploy automático a cada push na branch configurada.

## Fluxo de autenticação e token

1. **Cadastro** (`/register`): `POST /api/proxy/auth/register` → retorna `access_token` → salvo em `localStorage` (chave `flowbase_token`).
2. **Login** (`/login`): `POST /api/proxy/auth/login` → retorna `access_token` → salvo em `localStorage`.
3. **Requisições protegidas**: o cliente envia `Authorization: Bearer <token>` em todas as chamadas a `/api/proxy/jobs` e subrotas.
4. **Logout**: remove o token do `localStorage` e redireciona para `/login`.

## Como testar (3 passos)

1. **Cadastrar**  
   Acesse a URL do frontend (ex.: https://seu-app.vercel.app) → clique em "Cadastre-se" → informe email e senha (mín. 6 caracteres) → Cadastrar.  
   Deve redirecionar para o dashboard.

2. **Logar**  
   Se já tiver conta: "Entrar" → email e senha → Entrar.  
   Deve redirecionar para o dashboard.

3. **Enviar arquivo e ver job concluir**  
   No dashboard: clique na área de upload ou arraste um arquivo .csv ou .xlsx (até 10 MB).  
   Deve aparecer "Job em andamento" e, em alguns segundos, o job na lista com status "done".  
   Use "Preview", "Report" e "Baixar CSV" para validar.

## Estrutura

- `app/api/proxy/[...path]/route.ts`: proxy GET/POST para o backend (usa `API_URL`).
- `lib/api.ts`: funções que chamam `/api/proxy/...` e incluem `Authorization: Bearer <token>`.
- `components/AuthProvider.tsx`: contexto com token (localStorage).
- `app/login/page.tsx`, `app/register/page.tsx`: telas de login e cadastro.
- `app/dashboard/page.tsx`: upload, lista de jobs, preview/report/download e retry.
