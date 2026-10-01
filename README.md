# Lavconta — Relatórios B2B

Aplicação interna da Lavandix para registrar os pedidos diários de cada
cliente-empresa e gerar a relação de valores do fechamento (PDF e Excel).

| Camada   | Tecnologia                 | Hospedagem             |
|----------|----------------------------|------------------------|
| Frontend | React + Vite (`frontend/`) | Netlify                |
| API      | FastAPI (`backend/`)       | Render (plano free)    |
| Banco    | PostgreSQL                 | Supabase               |
| Auth     | Supabase Auth (JWT)        | Supabase               |

Regras de negócio, arquitetura e convenções: `.kiro/steering/`.

## Desenvolvimento local

Backend (Python 3.14):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env   # preencher os valores
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend (Node 24):

```powershell
cd frontend
npm ci
copy .env.example .env   # preencher os valores
npm run dev
```

Testes:

```powershell
# backend: exige o Postgres de teste definido em backend/.env.teste
cd backend; $env:EXIGIR_BANCO_DE_TESTE = "1"; .\.venv\Scripts\python.exe -m pytest
# frontend
cd frontend; npm test
```

Banco de desenvolvimento com dados fictícios (Postgres local, nunca produção):
`python -m scripts_dev.preparar_banco --recriar` e `python -m scripts_dev.servidor`,
a partir de `backend/`.

## Deploy

A configuração fica versionada: `render.yaml` (API) e `netlify.toml` (frontend).
Nenhum dos dois contém segredo; os valores ficam no painel de cada plataforma.

Ordem (a API primeiro, porque o frontend precisa do endereço dela):

1. **Render** — New → Blueprint → este repositório. Preencher as variáveis
   pedidas (tabela abaixo). Conferir `https://<api>.onrender.com/api/saude`
   → `{"situacao":"ok"}`.
2. **Netlify** — importar o repositório (o `netlify.toml` define pasta, build e
   publicação) e preencher as variáveis `VITE_*`.
3. **Fechar o ciclo**:
   - Render: `CORS_ORIGENS` com o endereço do Netlify.
   - Supabase → Authentication → URL Configuration: *Site URL* = endereço do
     Netlify; em *Redirect URLs*, adicionar `https://<site>/redefinir-senha`
     (destino do link de recuperação de senha).

O Render só faz deploy automático de commit no `main` com o CI verde
(`autoDeployTrigger: checksPass`).

### Variáveis — Render (API)

| Variável                | Conteúdo                                                        | Sensível |
|-------------------------|-----------------------------------------------------------------|----------|
| `DATABASE_URL`          | Postgres do Supabase pelo **Session pooler** (porta 5432), prefixo `postgresql+psycopg://` | **Sim** |
| `SUPABASE_JWKS_URL`     | `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json`       | Não      |
| `SUPABASE_JWT_ISSUER`   | Emissor (`iss`) do JWT do projeto                               | Não      |
| `SUPABASE_JWT_AUDIENCE` | Audiência (`aud`), normalmente `authenticated`                  | Não      |
| `CORS_ORIGENS`          | Origens permitidas, separadas por vírgula, sem `*`              | Não      |

`PYTHON_VERSION` já vem definido no `render.yaml`. Detalhes de cada chave em
`backend/.env.example`. A API não sobe se faltar alguma: o erro nomeia a chave.

### Variáveis — Netlify (frontend)

| Variável                        | Conteúdo                                   |
|---------------------------------|--------------------------------------------|
| `VITE_SUPABASE_URL`             | `https://<ref>.supabase.co`                |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Chave publicável (`sb_publishable_...`)    |
| `VITE_API_URL`                  | Endereço da API no Render                  |

Toda variável `VITE_*` vai para o bundle e é **pública**. Nunca colocar aqui
segredo de servidor (senha do banco, `service_role`). Como entram no build,
alterar uma delas exige novo deploy no Netlify.

### Migrações

O plano free do Render não tem *pre-deploy command*. Quando houver migração
nova, aplicar a partir da máquina local **antes** de subir o código que depende
dela:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head   # usa DATABASE_URL do .env
```

Migração destrutiva (drop, troca de tipo com perda) exige plano de rollback antes.

### Limitações conhecidas do plano free

- **Cold start**: o Render hiberna a API após ~15 min sem uso; a primeira
  requisição depois disso leva de 30 s a 1 min. O frontend mostra um aviso
  enquanto a API acorda.
- **Rate limit**: o uvicorn só lê o `X-Forwarded-For` de proxies confiáveis
  (padrão: `127.0.0.1`). Atrás do proxy do Render, a API deve enxergar o IP do
  proxy, e o limite passa a ser compartilhado por todos os usuários (a confirmar
  após o primeiro deploy). Confiar em qualquer proxy (`--forwarded-allow-ips "*"`)
  faria o uvicorn adotar o primeiro IP do cabeçalho, que o cliente controla, e o
  limite poderia ser contornado; por isso não foi ativado. Os limites atuais
  (60/min em escrita, 30/min em exportação) folgam para a equipe da v1.
