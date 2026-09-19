# Engenharia — Lavconta (decisões de arquitetura, DevOps e segurança)

> Fonte da verdade para **como** construímos o Lavconta. Complementa os steering de
> produto, regras de negócio, tech e estrutura. Estas são decisões fixas do projeto,
> a serem respeitadas durante todo o desenvolvimento.

## 0. Skills que reforçam este steering

Duas skills carregam as diretrizes operacionais em detalhe. Ativá-las quando o
contexto casar:

- **`boas-praticas`** — planejamento, código modular, qualidade, segurança geral e
  verificação antes de "pronto".
- **`gestao-segredos`** — cibersegurança aplicada a segredos: nenhuma chave,
  credencial, senha ou dado sensível no código-fonte ou versionado no Git.

O steering fixa as **decisões**; as skills detalham a **prática**. Em conflito,
o steering do projeto tem precedência.

## 1. Fronteiras de arquitetura (backend)

Camadas com responsabilidade única, sem vazamento entre elas:

- **`routers/`** — só transporte HTTP: validar entrada com Pydantic, chamar um
  `service`, mapear a saída. **Zero regra de negócio.**
- **`services/`** — única autoridade de negócio: cálculo de totais, congelamento de
  valor no lançamento, resolução de preço vigente por mês, validação de unicidade
  `(cliente, data)` e `(cliente, comanda)`, montagem de relatório e exportação.
- **Camada de dados (repositório):** o acesso ao banco fica isolado em uma camada de
  repositório. Os `services` dependem de repositórios, não do ORM diretamente. Isso
  mantém a regra de negócio testável sem banco e concentra as queries.
  - **Decisão v1:** camada de repositório explícita, mesmo simples. Concentra as
    consultas parametrizadas e facilita teste da regra sem I/O.
- **`schemas/`** — modelos Pydantic de entrada/saída, separados dos modelos ORM
  (`models/`). Nunca expor o modelo de banco direto na API.

Fluxo: `router → service → repositório → banco`. Nunca `router → banco`.

## 2. Migrações e banco

- **Alembic** para migrações versionadas do Postgres (padrão do ecossistema
  SQLAlchemy/FastAPI). Migração é código versionado; toda mudança de schema passa por
  migração — nada de alteração manual no banco.
- Constraints de integridade reforçam a regra crítica no nível do banco:
  - Unicidade `(cliente_id, data)` em lançamentos.
  - Unicidade **parcial** de comanda por cliente (ignora nulos):
    índice único em `(cliente_id, comanda)` com `WHERE comanda IS NOT NULL`.
  - Chaves estrangeiras: item → cliente, preço → (cliente, item), linha → lançamento.
- **Dinheiro:** `NUMERIC` no banco; `Decimal` no Python; serialização como string
  decimal. Arredondamento explícito e documentado. Nunca float binário.

## 3. Autenticação e autorização

- Frontend autentica no Supabase e recebe JWT; **FastAPI valida o JWT em cada rota
  de dados.**
- **Validação completa do JWT**, não só decode: verificar **assinatura** contra o
  JWKS do Supabase, e conferir `exp`, `iss` e `aud`. Token inválido/expirado → 401.
- Dependência de auth central (FastAPI `Depends`) aplicada a todas as rotas de dados.
  Nenhuma rota de dados pública.
- Menor privilégio: chave `service_role` do Supabase só no backend; nunca no
  frontend, nunca em URL, nunca versionada.

## 4. Segurança de borda (API)

- **CORS restrito** à origem do frontend (domínio Netlify + `localhost` de dev).
  Nunca `*` com credenciais.
- **Rate limiting** básico nas rotas de autenticação e de escrita de dados, para
  conter abuso. Implementação leve compatível com o free tier do Render.
- **Validação de entrada** em toda rota (Pydantic); tratar todo dado externo como não
  confiável. Consultas **parametrizadas** sempre.
- **Saída segura:** erros não vazam stack trace nem detalhe interno ao cliente;
  mensagens de erro referenciam o problema, não a implementação.
- Cabeçalhos de segurança e `content-type` corretos nas respostas.

## 5. Gestão de segredos (resumo — detalhe na skill `gestao-segredos`)

- Nenhum segredo hardcoded; nenhum arquivo de segredo versionado.
- `.gitignore` cobre `.env`, `.env.*` (exceto `.env.example`), `*.pem`, `*.key`,
  `*.p12`, `*.pfx`, `secrets/` — configurado **antes** de criar arquivos sensíveis.
- **`.env.example` versionado** com as chaves sem valores reais.
- Config lida em um ponto (Pydantic `Settings`), validada na inicialização; falta de
  variável obrigatória → erro claro pelo nome da chave, sem default inseguro.
- **Frontend Vite:** só variáveis `VITE_*` vão ao bundle e **são públicas** — nunca
  colocar segredo de servidor ali.
- Nunca logar valor de segredo; mascarar em logs e respostas.

## 6. Prevenção contra dependências e scripts maliciosos (supply chain)

Cadeia de suprimentos é vetor de ataque real. Postura obrigatória ao adicionar ou
atualizar qualquer dependência (npm ou PyPI):

- **Verificar o nome com atenção a typosquatting.** Pacotes maliciosos se disfarçam
  imitando libs legítimas com nomes quase idênticos (ex.: um pacote falso imitando
  `bcrypt`, `python-jose`, `requests`). Conferir o nome exato, o autor/mantenedor, o
  repositório oficial e a popularidade antes de instalar. Na dúvida, confirmar a
  fonte oficial.
- **Fixar versões.** Sem faixas abertas. `requirements.txt`/`pyproject` com versão
  pinada; `package.json` com versão exata e **lockfile** (`package-lock.json`)
  sempre versionado. Instalar com `npm ci` (respeita o lockfile) em CI.
- **Preferir pacotes conhecidos e mantidos.** Evitar dependências obscuras, sem
  manutenção ou com pouquíssimo uso para tarefas triviais.
- **Scripts de instalação (`postinstall`/`preinstall`) são risco.** Executam código
  arbitrário na máquina/CI ao instalar. Desconfiar de dependências novas que rodam
  scripts na instalação; auditar antes de aceitar.
- **Auditar regularmente.** `npm audit` e checagem de vulnerabilidades no Python
  (`pip-audit`) no fluxo de CI. Tratar alertas de severidade alta antes de mergear.
- **Scanner de segredos no CI** (ex.: gitleaks) para impedir que credencial escape
  para o histórico via dependência ou config.
- **Não confiar em código de terceiros cegamente.** Não copiar/colar snippets que
  executam comandos de shell, baixam e rodam scripts remotos (`curl ... | sh`) ou
  pedem credenciais sem entender o que fazem.

## 7. DevOps e verificação

- **CI (GitHub Actions):** em cada push/PR — lint, testes e build do backend e do
  frontend; `npm audit`/`pip-audit`; scanner de segredos. PR não mergeia com CI
  vermelho.
- **Deploy como configuração versionada:** `netlify.toml` (frontend) e `render.yaml`
  (API) no repositório, sem segredo embutido — os valores sensíveis ficam nas env
  vars de cada plataforma.
- **Testes priorizados** (conforme regra de negócio): cálculo de totais, resolução de
  preço vigente por mês, congelamento de valor, unicidade `(cliente, data)` e
  unicidade parcial de comanda, e validação de JWT.
- **"Compilou" não é "funciona":** validar contra o critério de sucesso definido. Se
  algo não pôde ser verificado (ambiente/dependência ausente), dizer explicitamente.

## 8. Operações (blast radius)

- Escalar cautela ao impacto: edição local reversível → agir; ação destrutiva,
  produção ou de alcance amplo → explicar risco e confirmar antes.
- Migrações destrutivas (drop de coluna/tabela, alteração de tipo com perda) exigem
  confirmação e plano de rollback.
- Reescrita de histórico do Git (para remover segredo vazado) é destrutiva:
  confirmar antes, coordenar force-push, e **rotacionar a credencial primeiro**.
