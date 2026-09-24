# Design técnico — Lavconta v1

Deriva de `requirements.md` (11 requisitos, 20 decisões registradas), dos steering do
projeto e de `prototipo/avaliacao-v1.md`. Herda a direção visual da Parte A da avaliação
e **não** implementa nada da Parte B.

---

## 1. Princípios que guiam este design

Quatro decisões estruturais respondem por quase todo o resto:

1. **O valor cobrado é imutável.** O preço unitário é copiado para a linha do lançamento
   no momento da criação. Nenhuma leitura de relatório passado consulta a tabela de
   preços.
2. **Uma única fonte de verdade para cada total.** Calculado no backend, consumido
   igual por tela, PDF e Excel. É a correção do defeito B1 do protótipo.
3. **Data de negócio não tem fuso.** Tipo `DATE` ponta a ponta, sem conversão.
4. **O banco reforça o que é crítico.** Unicidade e integridade existem como constraint,
   não apenas como validação em Python.

---

## 2. Arquitetura

```
Navegador (React + Vite / Netlify)
        │  HTTPS + JWT no header Authorization
        ▼
FastAPI (Render)
  routers/     → transporte HTTP, validação Pydantic, mapeamento de erro
  services/    → regra de negócio (única autoridade)
  repositories/→ acesso ao banco, queries parametrizadas
  models/      → SQLAlchemy ORM
        ▼
PostgreSQL (Supabase)
```

Fluxo obrigatório: `router → service → repository → banco`. Nunca `router → banco`.

O Supabase é usado como **provedor de auth + Postgres gerenciado**. Não usamos RLS nem
as APIs auto-geradas para regra de negócio.

### Divisão de responsabilidades por camada

| Camada | Faz | Não faz |
|---|---|---|
| `routers/` | Valida entrada, chama service, traduz exceção de domínio em HTTP | Cálculo, query, decisão de negócio |
| `services/` | Congelamento, resolução de preço, unicidade, montagem de relatório | SQL direto, detalhe de HTTP |
| `repositories/` | Queries parametrizadas, transação | Regra de negócio |
| `exports/` | Renderiza PDF/Excel a partir do relatório já calculado | Recalcular qualquer total |

---

## 3. Modelo de dados

### 3.1 DDL

```sql
-- Clientes -------------------------------------------------------------------
create table clientes (
  id             uuid primary key default gen_random_uuid(),
  nome           text not null,
  ativo          boolean not null default true,
  criado_em      timestamptz not null default now(),
  atualizado_em  timestamptz not null default now(),
  constraint clientes_nome_nao_vazio check (btrim(nome) <> '')
);

-- Nome único ignorando caixa e espaços nas pontas (Req 2.5)
create unique index clientes_nome_unico
  on clientes (lower(btrim(nome)));

-- Itens ----------------------------------------------------------------------
create table itens (
  id             uuid primary key default gen_random_uuid(),
  cliente_id     uuid not null references clientes(id) on delete cascade,
  nome           text not null,
  ativo          boolean not null default true,
  criado_em      timestamptz not null default now(),
  atualizado_em  timestamptz not null default now(),
  constraint itens_nome_nao_vazio check (btrim(nome) <> ''),
  -- habilita a FK composta de precos (garante item pertencente ao cliente)
  constraint itens_id_cliente_unico unique (id, cliente_id)
);

create unique index itens_nome_unico_por_cliente
  on itens (cliente_id, lower(btrim(nome)));

-- Preços ---------------------------------------------------------------------
create table precos (
  id               uuid primary key default gen_random_uuid(),
  cliente_id       uuid not null,
  item_id          uuid not null,
  vigencia_mes     date not null,
  valor_unitario   numeric(10,2) not null,
  criado_em        timestamptz not null default now(),
  atualizado_em    timestamptz not null default now(),

  -- item precisa pertencer ao cliente do preço (engineering.md §2)
  constraint precos_item_do_cliente
    foreign key (item_id, cliente_id) references itens (id, cliente_id)
    on delete cascade,

  constraint precos_valor_positivo check (valor_unitario > 0),
  -- vigência é sempre o primeiro dia do mês (Req 4.1)
  constraint precos_vigencia_primeiro_dia check (extract(day from vigencia_mes) = 1),
  -- um preço por (cliente, item, mês) — Req 4.2
  constraint precos_unico_por_mes unique (cliente_id, item_id, vigencia_mes)
);

-- Índice que serve à resolução de preço vigente
create index precos_resolucao
  on precos (cliente_id, item_id, vigencia_mes desc);

-- Lançamentos ----------------------------------------------------------------
create table lancamentos (
  id             uuid primary key default gen_random_uuid(),
  -- restrict: cliente com lançamento não pode ser excluído (Req 2.11)
  cliente_id     uuid not null references clientes(id) on delete restrict,
  data           date not null,
  comanda        text,
  criado_em      timestamptz not null default now(),
  atualizado_em  timestamptz not null default now(),

  -- unicidade forte (cliente, data) — Req 5.2 e 5.3
  constraint lancamentos_cliente_data_unico unique (cliente_id, data),
  -- comanda só com espaços é nula, nunca string vazia (Req 5.8)
  constraint lancamentos_comanda_nao_vazia
    check (comanda is null or btrim(comanda) <> '')
);

-- Unicidade PARCIAL e insensível a caixa (Req 5.9 e 5.10)
create unique index lancamentos_comanda_unica_por_cliente
  on lancamentos (cliente_id, lower(btrim(comanda)))
  where comanda is not null;

create index lancamentos_cliente_periodo
  on lancamentos (cliente_id, data);

-- Linhas de lançamento -------------------------------------------------------
create table lancamento_linhas (
  id                        uuid primary key default gen_random_uuid(),
  lancamento_id             uuid not null
                              references lancamentos(id) on delete cascade,
  -- restrict: item com histórico não pode ser excluído (Req 3.12)
  item_id                   uuid not null references itens(id) on delete restrict,
  quantidade                integer not null,
  valor_unitario_congelado  numeric(10,2) not null,
  -- total derivado no banco: impossível divergir do congelado × quantidade
  total                     numeric(12,2)
                              generated always as
                              (valor_unitario_congelado * quantidade) stored,
  criado_em                 timestamptz not null default now(),

  constraint linhas_quantidade_positiva check (quantidade > 0),
  constraint linhas_valor_positivo check (valor_unitario_congelado > 0),
  -- mesmo item não repete no mesmo lançamento (Req 5.12)
  constraint linhas_item_unico_por_lancamento unique (lancamento_id, item_id)
);

create index linhas_por_lancamento on lancamento_linhas (lancamento_id);
```

### 3.2 Por que `vigencia_mes` é uma coluna `date` e não `(ano, mes)`

A vigência é o **primeiro dia do mês**, com `CHECK` garantindo isso. Vantagens sobre dois
inteiros: a resolução do preço vigente vira uma comparação simples (`vigencia_mes <= X`)
que usa o índice diretamente, a ordenação é natural, e não há risco de comparar mês e ano
na ordem errada.

### 3.3 O que o banco garante e o que fica no service

Duas validações **não** podem ser constraint e ficam obrigatoriamente no service:

- **Data futura** (Req 5.15): um `CHECK` não pode usar `now()`, porque precisa ser
  imutável. Além disso, "hoje" é em America/Sao_Paulo, não no fuso do servidor.
- **Item sem preço** (Req 5.14): depende de consulta a outra tabela; regra de
  aplicação.

---

## 4. Precisão monetária: não existe arredondamento

Consequência das decisões já tomadas, e vale registrar porque elimina uma classe inteira
de bug:

- Preço unitário: `numeric(10,2)` — exato, duas casas (Req 4.12).
- Quantidade: `integer` (Req 5.11).
- Total da linha: `numeric(10,2) × integer` → exato, duas casas.
- Total do lançamento e do período: soma de exatos → exato.

**Nenhuma multiplicação ou soma da cadeia de cobrança produz dízima.** Não há política de
arredondamento a definir porque não há arredondamento. Isso satisfaz o Requisito 6.9 da
forma mais forte possível: por construção.

A única divisão do sistema é a **média diária de peças** do cartão de resumo, que é
métrica operacional de exibição. Ela é arredondada para inteiro na apresentação e **nunca
participa de valor cobrado**.

No Python, `Decimal` do início ao fim. Na API, valor monetário serializa como **string**
(`"1695.00"`), evitando que o JavaScript receba float binário.

---

## 5. Resolução de preço vigente

Algoritmo (Req 4.6 e 4.7): dado cliente, item e a **data do lançamento**, o preço vigente
é o preço mais recente cuja vigência seja igual ou anterior ao mês daquela data.

```sql
-- resolução em lote para todos os itens de um lançamento (evita N+1)
select distinct on (item_id) item_id, valor_unitario
from precos
where cliente_id = :cliente_id
  and item_id = any(:item_ids)
  and vigencia_mes <= date_trunc('month', :data_lancamento)::date
order by item_id, vigencia_mes desc;
```

Itens ausentes no resultado são os **sem preço**: o service compara o conjunto pedido com
o retornado e, se houver diferença, aborta informando os nomes (Req 5.14).

### Exemplo de comportamento

Preços cadastrados para (Hotel Aurora, Lençol): `2026-06-01 → 4,50` e `2026-10-01 → 4,80`.

| Data do lançamento | Preço resolvido | Motivo |
|---|---|---|
| 15/09/2026 | 4,50 | Junho é a vigência mais recente até setembro |
| 03/10/2026 | 4,80 | Outubro tem vigência própria |
| 20/12/2026 | 4,80 | Outubro se propaga (Req 4.4) |
| 10/05/2026 | **sem preço** | Nada vigente antes de junho → bloqueia (Req 5.14) |

---

## 6. Datas e fuso horário

Implementação do Requisito 11.

- **Banco:** `date` para data de negócio; `timestamptz` para auditoria.
- **API:** string `YYYY-MM-DD`. Pydantic usa `datetime.date`, que serializa nesse formato
  sem hora nem offset.
- **Backend:** `hoje_sp()` em `core/datas.py` é a **única** fonte de "hoje":
  ```python
  from datetime import date
  from zoneinfo import ZoneInfo
  from datetime import datetime

  FUSO_NEGOCIO = ZoneInfo("America/Sao_Paulo")

  def hoje_sp() -> date:
      return datetime.now(FUSO_NEGOCIO).date()
  ```
- **Frontend:** a data trafega e é guardada como string `YYYY-MM-DD`. **Proibido**
  passar por `new Date()` para formatar. A conversão para dd/mm/yyyy é manipulação de
  texto:
  ```ts
  export const paraExibicao = (iso: string) => iso.split('-').reverse().join('/');
  export const paraIso = (br: string) => br.split('/').reverse().join('-');
  ```
  Para obter "hoje" no fuso de negócio sem contaminar com o fuso do navegador:
  ```ts
  export const hojeSp = () =>
    new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo' })
      .format(new Date()); // já retorna YYYY-MM-DD
  ```

Regra de revisão de código: qualquer `new Date(...)` aplicado a data de negócio é bug.

---

## 7. Autenticação

### 7.1 Pré-requisito de configuração no Supabase

O `engineering.md` exige validação de assinatura contra JWKS. O Supabase oferece dois
sistemas de assinatura: o **legado**, com JWT secret simétrico (HS256), e o de **Signing
Keys assimétricas**, cuja chave pública é publicada em JWKS
([documentação](https://www.supabase.com/docs/guides/auth/signing-keys)).

**Decisão:** usar o sistema de **chaves assimétricas**, verificando pelo JWKS. Vantagem
de segurança concreta: o backend nunca precisa guardar um segredo capaz de *emitir*
tokens — só a chave pública, que valida. Se o projeto estiver no sistema legado, migrar
antes de implementar a auth.

*Verificar na implementação:* endpoint JWKS do projeto, algoritmo (RS256/ES256), e os
valores exatos de `iss` e `aud` emitidos.

### 7.2 Dependência de autenticação

`core/seguranca.py` expõe `usuario_atual` usado via `Depends` em **todas** as rotas de
dados:

1. Extrai o Bearer token; ausente → `401`.
2. Lê o `kid` do header e busca a chave no JWKS.
3. Valida assinatura, `exp`, `iss` e `aud` (PyJWT).
4. Falha em qualquer etapa → `401` com mensagem genérica, sem detalhe da validação
   (Req 1.5).

**Cache do JWKS** em memória com TTL (ex.: 10 min) e recarga sob `kid` desconhecido —
evita uma chamada externa por requisição, o que seria péssimo com cold start. Chave
desconhecida após recarga → `401`.

O router é montado com a dependência aplicada no nível do `APIRouter`, não rota a rota:
esquecer um `Depends` deixaria uma rota pública, e essa é uma falha que não pode depender
de disciplina individual.

---

## 8. Contratos da API

Prefixo `/api`. Todas as rotas exigem JWT, exceto `GET /api/saude`.

### 8.1 Envelope de erro

```json
{
  "erro": {
    "codigo": "ITENS_SEM_PRECO",
    "mensagem": "Os itens Roupão e Tapete não têm preço cadastrado para setembro/2026.",
    "detalhes": { "itens": ["Roupão", "Tapete"] }
  }
}
```

| Código | HTTP | Situação |
|---|---|---|
| `NAO_AUTENTICADO` | 401 | JWT ausente, inválido ou expirado |
| `VALIDACAO` | 422 | Entrada malformada (Pydantic) |
| `LANCAMENTO_DUPLICADO` | 409 | Já existe lançamento para (cliente, data) |
| `COMANDA_DUPLICADA` | 409 | Comanda já usada para o cliente |
| `ITENS_SEM_PRECO` | 422 | Itens sem preço vigente para o mês |
| `ITEM_DUPLICADO_NO_LANCAMENTO` | 422 | Mesmo item repetido |
| `DATA_FUTURA` | 422 | Data posterior a hoje (SP) |
| `PERIODO_INVALIDO` | 422 | Data inicial após a final |
| `NOME_DUPLICADO` | 409 | Nome de cliente ou de item já existe |
| `EXCLUSAO_COM_HISTORICO` | 409 | Registro com histórico; sugerir inativação |
| `NAO_ENCONTRADO` | 404 | Recurso inexistente |

Erro não tratado → `500` com mensagem genérica. Stack trace só no log do servidor
(Req 9.7).

### 8.2 Endpoints

**Clientes**

| Método | Rota | Observação |
|---|---|---|
| GET | `/api/clientes?incluir_inativos=false` | Ordenado por nome (Req 2.4) |
| POST | `/api/clientes` | `{ "nome": "Hotel Aurora" }` |
| PATCH | `/api/clientes/{id}` | Renomear |
| POST | `/api/clientes/{id}/inativar` | |
| POST | `/api/clientes/{id}/reativar` | |
| DELETE | `/api/clientes/{id}` | Só sem lançamentos |

**Itens**

| Método | Rota |
|---|---|
| GET | `/api/clientes/{cliente_id}/itens?incluir_inativos=false` |
| POST | `/api/clientes/{cliente_id}/itens` |
| PATCH | `/api/itens/{id}` |
| POST | `/api/itens/{id}/inativar` · `/reativar` |
| DELETE | `/api/itens/{id}` |

**Preços**

| Método | Rota | Observação |
|---|---|---|
| GET | `/api/clientes/{cliente_id}/precos?mes=2026-09` | Preço vigente resolvido por item, marcando os sem preço |
| PUT | `/api/clientes/{cliente_id}/precos` | Upsert de `{ item_id, vigencia_mes, valor_unitario }` |

Resposta do GET:

```json
{
  "mes": "2026-09",
  "itens": [
    { "item_id": "…", "nome": "Lençol", "valor_unitario": "4.50",
      "vigencia_origem": "2026-06", "sem_preco": false },
    { "item_id": "…", "nome": "Roupão", "valor_unitario": null,
      "vigencia_origem": null, "sem_preco": true }
  ]
}
```

`vigencia_origem` mostra de qual mês o preço foi herdado — dá transparência à regra de
propagação (Req 4.4) em vez de deixar o operador adivinhar.

**Lançamentos**

| Método | Rota |
|---|---|
| GET | `/api/lancamentos?cliente_id=&inicio=&fim=` |
| POST | `/api/lancamentos` |
| POST | `/api/lancamentos/previa` |
| GET | `/api/lancamentos/{id}` |
| PUT | `/api/lancamentos/{id}` |
| DELETE | `/api/lancamentos/{id}` |

POST:

```json
{
  "cliente_id": "…",
  "data": "2026-09-01",
  "comanda": "1201",
  "linhas": [
    { "item_id": "…", "quantidade": 40 },
    { "item_id": "…", "quantidade": 30 }
  ]
}
```

O cliente **não envia valor**. O preço é resolvido e congelado pelo servidor — enviar
preço pelo cliente seria permitir que o navegador defina quanto custa.

Resposta inclui os valores congelados e os totais calculados.

**Prévia de totais — `POST /api/lancamentos/previa`**

Calcula os valores de um lançamento **sem persistir nada**, para alimentar a barra de
totais animada enquanto o operador digita. Mantém a autoridade de cálculo no backend
(Req 6.8) sem sacrificar a interação.

Requisição idêntica ao POST de criação (sem a comanda, que não afeta valor):

```json
{
  "cliente_id": "…",
  "data": "2026-09-01",
  "linhas": [
    { "item_id": "a2", "quantidade": 40 },
    { "item_id": "a1", "quantidade": 30 }
  ]
}
```

Resposta:

```json
{
  "linhas": [
    { "item_id": "a2", "valor_unitario": "4.50", "total": "180.00" },
    { "item_id": "a1", "valor_unitario": "3.50", "total": "105.00" }
  ],
  "total_pecas": 70,
  "total_valor": "285.00",
  "itens_sem_preco": []
}
```

Três características deliberadas:

1. **Não é destrutiva nem persistente.** Só leitura de preços e aritmética. Pode ser
   chamada com qualquer frequência sem efeito colateral.
2. **Não falha por item sem preço.** Devolve `itens_sem_preco` como lista e calcula o
   total com os itens que têm preço. Erro `422` no meio da digitação seria hostil; a
   tela usa a lista para avisar em linha. A recusa dura continua no POST/PUT de salvar
   (Req 5.14).
3. **Não valida unicidade de (cliente, data) nem comanda.** Prévia trata de valor.
   Conflito é verificado no salvamento.

Usa **o mesmo** código de resolução de preço e de cálculo dos serviços de criação — não
uma segunda implementação. É o ponto central: existe uma só regra de cálculo no sistema.

Quanto ao rate limiting, esta rota recebe limite próprio, mais permissivo que as de
escrita, porque é chamada com debounce durante a digitação e não altera estado.

**Relatório**

`GET /api/relatorio?cliente_id=&inicio=2026-09-01&fim=2026-09-30`

```json
{
  "cliente": { "id": "…", "nome": "Hotel Aurora" },
  "periodo": { "inicio": "2026-09-01", "fim": "2026-09-30" },
  "colunas_itens": [
    { "item_id": "a1", "nome": "Fronha" },
    { "item_id": "a2", "nome": "Lençol" },
    { "item_id": "a3", "nome": "Toalha" }
  ],
  "linhas": [
    { "lancamento_id": "…", "data": "2026-09-01", "comanda": "1201",
      "quantidades": { "a2": 40, "a1": 30, "a3": 20 },
      "total_pecas": 90, "total_valor": "395.00" },
    { "lancamento_id": "…", "data": "2026-09-03", "comanda": null,
      "quantidades": { "a2": 50, "a1": 40 },
      "total_pecas": 90, "total_valor": "365.00" }
  ],
  "totais": {
    "por_item": { "a1": 130, "a2": 190, "a3": 70 },
    "total_pecas": 390,
    "total_valor": "1695.00"
  },
  "resumo": {
    "total_pecas": 390,
    "total_valor": "1695.00",
    "quantidade_lancamentos": 5,
    "media_diaria_pecas": 78
  }
}
```

Dois pontos importantes nesse contrato:

**`resumo` e `totais` vêm do mesmo cálculo.** Os cartões do topo da tela leem `resumo`, a
linha de rodapé da tabela lê `totais`, e ambos derivam da mesma agregação em memória. É
estruturalmente impossível divergirem — a correção do defeito B1.

**`quantidades` é mapa de `item_id`, não lista posicional.** Item ausente no mapa significa
célula vazia (Req 7.8), sem precisar enviar zeros e sem risco de desalinhamento entre
colunas e valores.

**Exportação**

| Método | Rota |
|---|---|
| GET | `/api/relatorio/pdf?cliente_id=&inicio=&fim=` |
| GET | `/api/relatorio/excel?cliente_id=&inicio=&fim=` |

Respondem com `Content-Disposition: attachment` e nome descritivo
(`fechamento-hotel-aurora-2026-09-01-a-2026-09-30.pdf`), `content-type` correto
(Req 8.4).

---

## 9. Serviços (regra de negócio)

### 9.1 `servico_lancamento.criar`

```
1. valida cliente existe
2. valida data <= hoje_sp()                      → DATA_FUTURA
3. normaliza comanda (btrim; vazia → None)
4. valida itens: pertencem ao cliente, sem repetição  → ITEM_DUPLICADO_NO_LANCAMENTO
5. resolve preços em lote pelo mês de `data`
6. se faltar preço para algum item              → ITENS_SEM_PRECO (com nomes)
7. dentro de UMA transação:
   7.1 insere lancamento
   7.2 insere linhas com valor_unitario_congelado
8. traduz violação de constraint:
   lancamentos_cliente_data_unico          → LANCAMENTO_DUPLICADO
   lancamentos_comanda_unica_por_cliente   → COMANDA_DUPLICADA
9. retorna lançamento com totais
```

O passo 8 merece destaque: a validação da unicidade acontece **duas vezes**, por
consulta prévia (mensagem amigável) e por constraint (garantia real). Só a consulta
prévia seria sujeita a condição de corrida; só a constraint daria mensagem ruim. As duas
juntas resolvem.

### 9.2 `servico_lancamento.editar`

```
1. carrega lançamento e linhas atuais
2. se cliente/data mudaram → revalida unicidade e data futura (Req 5.20)
3. para cada linha:
   - existente → mantém valor_unitario_congelado, só atualiza quantidade (Req 5.18)
   - nova      → congela pelo preço vigente do MÊS DA DATA DO LANÇAMENTO (Req 5.19)
   - removida  → exclui
4. transação única
```

O congelamento da linha nova usa o mês da **data do lançamento**, não o mês corrente. Um
pedido de agosto editado em outubro recebe preço de agosto na linha nova.

### 9.3 `servico_lancamento.calcular_previa`

Compartilha com `criar` as funções de resolução de preço e de cálculo, extraídas para
`servico_lancamento._resolver_e_calcular`. A diferença é só o que se faz com o resultado:

```
1. valida cliente existe
2. resolve preços em lote pelo mês de `data`
3. calcula valor por linha e totais com os itens que TÊM preço
4. devolve totais + lista de itens sem preço (não levanta erro)
5. não abre transação de escrita, não persiste
```

Não valida data futura, unicidade nem comanda: prévia trata de valor. Isso mantém a rota
barata e sem efeito colateral.

### 9.4 `servico_relatorio.gerar`

```
1. valida inicio <= fim                          → PERIODO_INVALIDO
2. busca lançamentos do cliente no período, com linhas e nomes de item (1 query)
3. colunas_itens = itens distintos presentes, ordem alfabética
4. monta linhas (mapa item_id → quantidade)
5. agrega: por_item, total_pecas, total_valor
6. resumo derivado da MESMA agregação
7. retorna estrutura única
```

Consulta:

```sql
select l.id, l.data, l.comanda,
       li.item_id, i.nome as item_nome,
       li.quantidade, li.valor_unitario_congelado, li.total
from lancamentos l
join lancamento_linhas li on li.lancamento_id = l.id
join itens i on i.id = li.item_id
where l.cliente_id = :cliente_id
  and l.data between :inicio and :fim
order by l.data, i.nome;
```

Volume máximo: 31 lançamentos por mês por cliente (um por dia). Sem paginação, sem cache,
sem otimização — a simplicidade aqui é escolha informada, não descuido.

A ordenação alfabética das colunas é decisão de previsibilidade: dois fechamentos do
mesmo cliente com os mesmos itens sempre saem na mesma ordem.

### 9.5 `servico_preco.definir`

Upsert por `(cliente_id, item_id, vigencia_mes)`. `vigencia_mes` normalizado para o dia 1.
Sugestão de mês padrão é do **frontend** (Req 4.15/4.16) — o backend aceita o mês que
receber, apenas validando o formato.

---

## 10. Exportação

Ambos os formatos consomem **a mesma estrutura** retornada por `servico_relatorio.gerar`.
Os módulos de export não recalculam nada; se recalculassem, criariam a possibilidade de
divergência entre tela e documento enviado ao cliente.

### Excel — `openpyxl`

- Cabeçalho com cliente e período.
- Quantidades como **número inteiro**; valores como **número com formato
  `R$ #,##0.00`** — células numéricas de verdade, para o destinatário conferir e somar
  (Req 8.6).
- Linha de totais com negrito e borda superior.
- Largura de coluna ajustada ao conteúdo; primeira linha congelada.

### PDF — `reportlab`

Escolha com trade-off explícito. As alternativas eram:

| Opção | A favor | Contra |
|---|---|---|
| **reportlab** | Sem dependência de biblioteca de sistema; tabelas maduras (`platypus`) | Layout programático, não HTML/CSS |
| WeasyPrint | Reaproveitaria HTML/CSS do relatório | Exige Cairo/Pango no sistema — risco no free tier do Render |

**Decisão: reportlab.** O ambiente de hospedagem é restrito e não vale trocar
previsibilidade de deploy por conveniência de layout.

Layout: **A4 paisagem**, porque o número de colunas de item é variável. Se as colunas não
couberem, reduzir o tamanho da fonte e comprimir as colunas de item, preservando
legibilidade de Data, Total de peças e Total R$ (as três que sempre importam).

**Tipografia do PDF:** registrar a TTF do **Inter** (pesos 400 e 600) via
`pdfmetrics.registerFont`, em vez de usar a Helvetica padrão do reportlab. O documento é
o artefato que chega ao cliente-empresa; usar a mesma família da interface mantém a
relação de valores reconhecível como saída do Lavconta. Como a identidade agora é de
**família única** (`id-visual.md` §2), é um arquivo de fonte para registrar, não dois.

### Nota de supply chain

Ao pesquisar essas bibliotecas apareceram pacotes imitando as legítimas:
`reportlab-enhanced`, `reportlab-x`, `openpyxl-fast`, `paper-xlsx`, `xpyxl`. Os nomes
corretos são exatamente **`reportlab`** e **`openpyxl`**. Conferir o nome no PyPI oficial
e fixar a versão na instalação (`engineering.md` §6).

---

## 11. Frontend

### Estrutura

```
frontend/src/
├─ lib/
│  ├─ api.ts            # cliente HTTP, injeta JWT, traduz envelope de erro
│  ├─ supabase.ts       # cliente de auth
│  ├─ datas.ts          # paraExibicao, paraIso, hojeSp — SEM new Date()
│  └─ dinheiro.ts       # formatação a partir de string decimal
├─ features/
│  ├─ auth/  clientes/  catalogo/  precos/  lancamentos/  relatorio/
├─ components/          # Botao, Campo, Tabela, Modal, Toast, Skeleton, Sidebar
├─ pages/
└─ types/
```

### Decisões

**Estado de servidor: TanStack Query.** Justificativa concreta: cache e revalidação
automáticos reduzem chamadas ao backend que hiberna, e o estado de carregamento por
query alimenta diretamente os skeletons e o painel de "servidor acordando".

**Nenhum cálculo de negócio.** Os campos de valor unitário, total de linha e totais são
somente leitura, preenchidos pela resposta da API (Req 6.8). A barra de totais animada
exibe o que o servidor devolveu.

Isso tem uma consequência de UX resolvida por decisão de arquitetura: a barra de totais
**não recalcula localmente**. Ao alterar quantidade, o formulário chama
`POST /api/lancamentos/previa` com **debounce de 400ms**, e anima os números com o
resultado. A autoridade de cálculo permanece no backend e o momento de deleite é
preservado.

Comportamento do formulário em relação à prévia:

- Debounce de 400ms após a última alteração de quantidade.
- Requisições em voo são canceladas quando uma nova é disparada (`AbortController`),
  para que uma resposta atrasada não sobrescreva um valor mais novo.
- Enquanto a prévia está em voo, os números anteriores permanecem visíveis, sem
  piscar para zero.
- Falha da prévia não bloqueia o formulário: mostra os totais como indisponíveis e
  permite salvar (o salvamento recalcula e é a fonte final).
- `itens_sem_preco` da resposta marca as linhas envolvidas com aviso em linha, antes
  de o operador tentar salvar.

O último item é ganho real de usabilidade: o operador descobre que falta preço **enquanto
monta o pedido**, não ao clicar em salvar.

**Dinheiro** chega como string e é formatado com `Intl.NumberFormat('pt-BR')`. Nunca
convertido para `Number` antes de exibir.

**Cold start:** o cliente de API mede o tempo da requisição; passando de 3s, expõe um
sinal que a UI usa para mostrar o painel de reativação (Req 10.6).

---

## 12. Segurança de borda

| Item | Implementação |
|---|---|
| CORS | Lista explícita: domínio Netlify + `http://localhost:5173`. Sem coringa (Req 9.5) |
| Rate limiting | `slowapi` nas rotas de escrita e de exportação |
| Validação | Pydantic em toda entrada; `Decimal` para dinheiro, `date` para datas |
| SQL | Sempre parametrizado via SQLAlchemy; nenhuma concatenação |
| Erros | Handler global: domínio → código HTTP; inesperado → 500 genérico + log |
| Headers | `content-type` correto; `X-Content-Type-Options: nosniff` |

**Limitação honesta do rate limiting:** no free tier o contador fica em memória de uma
única instância e zera quando o serviço hiberna ou reinicia. Serve para conter abuso
acidental, não ataque distribuído. Aceitável na v1 (uso interno, usuário único);
registrado como dívida consciente.

---

## 13. Configuração e segredos

`core/config.py` com Pydantic `Settings`, validado na inicialização (Req 9.2):

| Variável | Onde vive | Sensível |
|---|---|---|
| `DATABASE_URL` | Render env | **Sim** |
| `SUPABASE_JWKS_URL` | Render env | Não |
| `SUPABASE_JWT_ISSUER` | Render env | Não |
| `SUPABASE_JWT_AUDIENCE` | Render env | Não |
| `CORS_ORIGENS` | Render env | Não |
| `VITE_SUPABASE_URL` | Netlify env | Não (vai ao bundle) |
| `VITE_SUPABASE_ANON_KEY` | Netlify env | Não (pública por design) |
| `VITE_API_URL` | Netlify env | Não |

A chave `service_role` **não aparece nesta tabela porque não é usada**. O backend fala com
o Postgres por `DATABASE_URL` e valida JWT por chave pública. Menor privilégio aplicado:
não guardamos o que não precisamos.

`.gitignore` configurado **antes** de qualquer arquivo de ambiente; `.env.example`
versionado apenas com os nomes das chaves.

---

## 14. Estrutura do backend

```
backend/
├─ app/
│  ├─ main.py                  # app, CORS, handlers de erro, routers
│  ├─ core/
│  │  ├─ config.py             # Settings
│  │  ├─ seguranca.py          # JWKS, usuario_atual
│  │  ├─ datas.py              # hoje_sp, FUSO_NEGOCIO
│  │  └─ erros.py              # exceções de domínio + códigos
│  ├─ models/                  # clientes, itens, precos, lancamentos, linhas
│  ├─ schemas/                 # Pydantic de entrada/saída
│  ├─ repositories/            # cliente_repo, item_repo, preco_repo, lancamento_repo
│  ├─ services/
│  │  ├─ servico_cliente.py
│  │  ├─ servico_item.py
│  │  ├─ servico_preco.py      # resolução de vigência
│  │  ├─ servico_lancamento.py # congelamento e unicidade
│  │  └─ servico_relatorio.py  # agregação única
│  ├─ exports/
│  │  ├─ excel.py
│  │  └─ pdf.py
│  └─ routers/
├─ migrations/                 # Alembic
└─ tests/
```

---

## 15. Dependências

Nomes canônicos. **Versões fixadas na instalação**, conferidas na página oficial do PyPI
ou npm no momento da implementação — não reproduzo números aqui para não registrar
versão desatualizada.

**Backend:** `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg` (driver Postgres),
`pydantic`, `pydantic-settings`, `pyjwt` (com suporte a criptografia), `httpx` (busca do
JWKS), `slowapi`, `openpyxl`, `reportlab`.
**Testes:** `pytest`, `pytest-asyncio`.

**Frontend:** `react`, `react-dom`, `vite`, `typescript`, `@supabase/supabase-js`,
`@tanstack/react-query`, `react-router-dom`, `lucide-react`.

`pyjwt` escolhido em vez de `python-jose`: mais ativo e com menos superfície. Atenção ao
nome — `pyjwt` é o pacote, `jwt` é o módulo importado, e existem pacotes de terceiros
ocupando nomes parecidos.

Gráfico de volume diário: **CSS puro**, sem biblioteca. São barras com altura
proporcional; não justifica dependência (decisão já alinhada).

---

## 16. Estratégia de testes

Prioridade definida pelo `engineering.md` §7. Testes de regra rodam sem banco, contra
repositórios falsos; os de constraint precisam de Postgres.

**Resolução de preço vigente** — propagação entre meses, mês com vigência própria,
lançamento retroativo, ausência total de preço, e a fronteira exata (dia 1 e último dia
do mês).

**Congelamento** — criação grava o vigente; alteração posterior de preço não muda o
lançamento; edição preserva o congelado da linha existente; linha nova em edição congela
pelo mês da data do lançamento, não do mês corrente.

**Cálculo** — total de linha, total de lançamento, total de peças; e a verificação de que
`resumo` e `totais` do relatório **coincidem sempre** (regressão direta do defeito B1).

**Prévia** — os totais de `previa` são idênticos aos do lançamento efetivamente salvo com
a mesma entrada. É o teste que impede as duas rotas de divergirem. Também: prévia com item
sem preço devolve `itens_sem_preco` e **não** levanta erro, enquanto o salvamento da mesma
entrada é recusado.

**Unicidade** — segunda tentativa de (cliente, data) barrada pela constraint; comanda
repetida com caixa diferente (`a100` vs `A100`) barrada; múltiplos lançamentos sem comanda
permitidos no mesmo cliente; item repetido no mesmo lançamento barrado.

**Datas** — lançamento em 31 e em 01 não muda de mês; data futura recusada; "hoje"
calculado em São Paulo.

**JWT** — token válido passa; expirado, assinatura inválida, `aud` errado, `iss` errado e
ausente resultam em 401; rota de dados sem `Depends` é detectada por um teste que varre
as rotas registradas e exige a dependência de auth em todas.

Esse último é um teste estrutural, não de comportamento: garante que ninguém publique uma
rota de dados sem auth por esquecimento.

**Relatório** — colunas só de itens presentes; célula vazia para item ausente no dia;
período cruzando meses somando valores congelados distintos; período vazio com totais
zerados.

---

## 17. Trade-offs registrados

| Decisão | Alternativa | Por que |
|---|---|---|
| reportlab | WeasyPrint | Sem dependência de sistema no free tier |
| Repositório explícito | Service falando com ORM | Regra testável sem banco (`engineering.md` §1) |
| `vigencia_mes date` | `(ano, mes)` inteiros | Comparação e índice mais simples |
| Coluna `total` gerada | Cálculo em Python | Impossível divergir de `congelado × qtd` |
| Rate limit em memória | Redis | Sem infraestrutura extra na v1; limitação registrada |
| Sem paginação | Paginar lançamentos | Máximo 31 registros por fechamento |
| Chaves assimétricas | JWT secret legado | Backend não guarda segredo capaz de emitir token |
| CSS puro no gráfico | Recharts | Evita dependência para barras simples |

---

## 18. Pendências de implementação

Itens que exigem verificação no ambiente real, registrados para não serem esquecidos:

1. **Configuração do Supabase** — confirmar sistema de chaves assimétricas ativo, URL do
   JWKS, algoritmo e valores de `iss`/`aud`.
2. **Versões das dependências** — fixar conferindo a fonte oficial.
3. **Largura do PDF** — validar com um cliente de muitos itens no período, para calibrar
   o ponto de redução de fonte.
4. **Limite da rota de prévia** — calibrar o rate limit com o uso real, considerando o
   debounce de 400ms durante a digitação.
