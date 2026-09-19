---
inclusion: always
---

# Estrutura e convenções — Lavconta

> **Aplicação:** Lavconta — Relatórios B2B.
> Estrutura de referência. Será materializada quando começarmos a implementação.
> Ajustar conforme decisões de design detalhado.

## Slugs técnicos (convenção)

As camadas do repositório usam slugs diretos, e os schemas que escrevermos seguem
essa nomenclatura:

- `frontend` — aplicação React + Vite.
- `backend` — API FastAPI (Python); inclui os schemas e as migrações do Postgres.
- `database` — nome lógico usado nos schemas que escrevermos (os arquivos ficam
  dentro do `backend`).

## Organização do repositório (proposta)

```
relatório-custos-empresas/
├─ backend/            # API FastAPI (Python)
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ core/         # config, segurança/JWT Supabase, dependências
│  │  ├─ models/       # modelos ORM / schema do banco
│  │  ├─ schemas/      # modelos Pydantic (entrada/saída da API)
│  │  ├─ routers/      # endpoints (clientes, itens, precos, lancamentos, relatorio)
│  │  ├─ services/     # regras de negócio (cálculo, congelamento, relatório)
│  │  └─ exports/      # geração de PDF e Excel
│  ├─ migrations/      # migrações versionadas do Postgres
│  └─ tests/
├─ frontend/           # React + Vite
│  ├─ src/
│  │  ├─ pages/
│  │  ├─ components/
│  │  ├─ features/     # clientes, catálogo, preços, lançamentos, relatório
│  │  ├─ lib/          # cliente de API, cliente Supabase (auth)
│  │  └─ types/
│  └─ index.html
└─ .kiro/
   └─ steering/        # documentos de escopo/regras (fonte da verdade)
```

## Entidades principais (visão de domínio, não schema final)

- **Cliente** — empresa atendida.
- **Item** — tipo de item do catálogo, **pertence a um cliente**.
- **Preço** — preço de um item para um **cliente** em um **mês/ano** (vigência mensal).
- **Lançamento** — pedido diário de um cliente numa data. Único por (cliente, data).
  Tem comanda opcional. Contém as linhas de item.
- **Linha de lançamento** — item + quantidade + **valor unitário congelado** + total.

## Convenções

- **Idioma:** documentação, mensagens ao usuário e nomes de domínio em **português**.
  Identificadores de código podem seguir a convenção usual de cada linguagem.
- **Backend:** Python com type hints; schemas Pydantic separados dos modelos de banco;
  regra de negócio em `services/`, nunca nos routers.
- **Frontend:** componentes por feature; chamadas à API centralizadas em `lib/`;
  a UI exibe valores calculados pela API, não recalcula regra de negócio.
- **Valores monetários:** representar com precisão adequada (evitar float binário para
  dinheiro; usar tipo decimal/numeric no banco e na serialização).
- **Datas:** entrada/exibição no formato dd/mm/yyyy; armazenamento em formato de data
  padrão do Postgres.
- **Testes:** escrever ao adicionar features/correções; priorizar cálculo de totais,
  resolução de preço vigente, congelamento de valor e regras de unicidade.

## Grounding (anti-alucinação) — regra de trabalho

- Não afirmar comportamento sem ter lido o código/arquivo ou verificado a fonte.
- Não deduzir regra de negócio de imagem/planilha sem confirmação do cliente.
- Distinguir claramente **fato observado** de **proposta de design**.
- Fixar versões de dependências e conferir a documentação da versão em uso.
- Verificar (build/testes) antes de declarar algo "pronto".
