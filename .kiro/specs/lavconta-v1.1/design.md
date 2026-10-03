# Design — Lavconta v1.1

Base: `requirements.md` desta pasta e o steering (`business-rules.md` já atualizado).
Estado atual levantado no código em 02/10/2026; referências de arquivo indicam o que
muda. Onde algo **não foi verificado**, está marcado.

Prioridades: experiência do usuário, segurança, arquitetura modular. Fluxo de camadas
mantido: `router → service → repositório → banco`.

---

## 1. Preço por data (Req 1)

### 1.1 Modelo

Tabela `precos` (hoje: `vigencia_mes`, sempre dia 1, com `ck_precos_vigencia_primeiro_dia`
e `uq_precos_cliente_item_mes`).

| Coluna nova | Tipo | Regra |
|---|---|---|
| `vigencia_inicio` | `date NOT NULL` | Dia a partir do qual o preço vale. |

- Unicidade: `uq_precos_cliente_item_inicio (cliente_id, item_id, vigencia_inicio)`.
  Garante no banco a regra "duas alterações no mesmo dia: a segunda corrige".
- Índice de resolução: `ix_precos_resolucao_inicio (cliente_id, item_id, vigencia_inicio DESC)`.
- Mantidos: `ck_precos_valor_positivo`, FK composta `fk_precos_item_do_cliente`,
  `Numeric(10,2)`.

### 1.2 Regra de resolução (repositório)

Para cada item, na data do pedido `d`:

1. o preço com **maior `vigencia_inicio` ≤ d**;
2. se não houver, o preço com **menor `vigencia_inicio`** (o primeiro preço vale para
   datas anteriores, Req 1.7);
3. se o item não tiver nenhum preço: sem preço.

Uma consulta para todos os itens (sem N+1), mantendo o `DISTINCT ON` atual:

```sql
SELECT DISTINCT ON (item_id) item_id, valor_unitario, vigencia_inicio
FROM precos
WHERE cliente_id = :c AND item_id = ANY(:itens)
ORDER BY item_id,
         (vigencia_inicio <= :d) DESC,                                  -- vigentes primeiro
         CASE WHEN vigencia_inicio <= :d THEN vigencia_inicio END DESC,  -- o mais recente
         vigencia_inicio ASC                                             -- senão, o primeiro
```

O volume é pequeno (dezenas de preços por cliente); a ordenação por expressão não
usa o índice por completo, o que é aceitável. A regra fica **dentro do repositório**;
o serviço só passa a data.

`PrecoVigente.vigencia_origem` passa a se chamar `desde` (a data de início do preço
aplicado). Hoje ele não é persistido nem exposto fora da tela de Preços (que sai).

### 1.3 Relógio injetado

`ServicoPreco` recebe `hoje: Callable[[], date]` (padrão `hoje_sp`). A data de início
nunca vem do cliente HTTP (Req 1.2): o schema de entrada **não tem** campo de data, e
a API ignora campos extras. Nos testes, o relógio é fixado para provar véspera, dia e
dia seguinte.

### 1.4 Operações de escrita (serviço)

| Operação | Efeito | Req |
|---|---|---|
| `mudar_a_partir_de_hoje(cliente, item, valor)` | Upsert em `(cliente, item, hoje)`: se já existe preço com início hoje, atualiza o valor; senão insere. | 1.2, 1.4 |
| `corrigir_atual(cliente, item, valor)` | Atualiza o valor do preço vigente **hoje** (maior início ≤ hoje; ou o primeiro, pela regra 1.2). Não cria linha. Sem preço → erro "Este item ainda não tem preço." | 1.11–1.13 |
| `definir_primeiro(cliente, item, valor)` | Insere com início hoje. Usado na criação do item. | 3.1, 3.3 |
| `impacto(cliente, item, modo)` | Conta pedidos que **mantêm o valor anterior**: linhas do item com data ≥ início afetado (hoje, no modo "a partir de hoje"; início do preço atual, no modo "corrigir") e valor congelado igual ao valor atual. | 1.6, 1.13 |

Validação de valor (positivo, duas casas, `Decimal`) reaproveita `_validar_valor`.
Removidos: `vigencia_sugerida`, `listar_do_mes`, `obter_do_mes`, `existe_algum`
(substituídos por `obter_atual` e `listar_na_data`).

### 1.5 Preços com início no futuro (dado legado)

A v1 permitia programar preço para mês futuro. Se houver em produção preço com
`vigencia_mes > mês atual`, ele continua válido após a migração (passa a valer no
dia 1 daquele mês). **Verificação antes da migração** (consulta só de leitura):

```sql
SELECT count(*) FROM precos WHERE vigencia_mes > date_trunc('month', now() AT TIME ZONE 'America/Sao_Paulo');
```

Se for zero (esperado), nada a fazer. Se não for, a interface mostraria só o preço
de hoje e o futuro "apareceria" no dia 1 — nesse caso decidir com o usuário antes de
seguir (manter, ou apagar com confirmação).

---

## 2. Migração (Req 2)

### Fase 1 — revisão `v11_preco_por_data` (expand)

1. `ADD COLUMN vigencia_inicio date` (nula), `UPDATE precos SET vigencia_inicio = vigencia_mes`,
   `ALTER ... SET NOT NULL`.
2. Criar `uq_precos_cliente_item_inicio` e `ix_precos_resolucao_inicio`.
3. `DROP CONSTRAINT uq_precos_cliente_item_mes` e `ALTER COLUMN vigencia_mes DROP NOT NULL`
   — necessário porque o código novo grava início no meio do mês e não preenche mais
   `vigencia_mes`. O `CHECK` de dia 1 permanece (NULL passa no CHECK).
4. Nenhuma linha de `lancamento_linhas` é tocada (Req 2.3).

**Downgrade da fase 1:** recria `vigencia_mes NOT NULL` a partir de
`date_trunc('month', vigencia_inicio)` e a unicidade por mês. Só é seguro **antes**
de existir mais de um preço do mesmo item no mesmo mês; depois disso, o downgrade
falharia na unicidade. Por isso o rollback real, depois do uso, é **restaurar o
backup** (`pg_dump`). O downgrade é testado no banco de desenvolvimento logo após o
upgrade.

**Janela de compatibilidade:** entre aplicar a migração e o Render publicar o código
novo (alguns minutos), o código antigo ainda roda. Leituras funcionam (`vigencia_mes`
ainda existe). Gravar preço falharia (`vigencia_inicio` NOT NULL). Mitigação: não
editar preços nessa janela (usuário único, combinado antes).

### Fase 2 — revisão `v11_remove_vigencia_mes` (contract)

Separada, depois do código novo estável em produção: remove `ck_precos_vigencia_primeiro_dia`,
`ix_precos_resolucao` (antigo) e a coluna `vigencia_mes`. Destrutiva → confirmação
explícita antes, com backup.

### Procedimento (Req 2.5, 2.6)

1. `lavconta_dev`: `upgrade`, rodar suíte, `downgrade`, `upgrade` de novo.
2. Produção: consulta de leitura do §1.5 e contagem de preços (para comparar depois).
3. `pg_dump` do banco de produção para um arquivo **fora da pasta do projeto**
   (o `.gitignore` atual não cobre `*.dump`/`*.sql`; verificado em 02/10). Há
   `pg_dump` 16.15 local em `C:\Program Files\PostgreSQL\16\bin` (fora do PATH).
   O `pg_dump` precisa ser da mesma versão principal do servidor ou mais nova:
   **conferir a versão do Postgres do Supabase** (`SELECT version();`) antes; se for
   17, usar um `pg_dump` 17.
4. `alembic upgrade head` contra produção (a partir de `backend/`, usa o `.env`).
5. Conferir contagem de preços igual e `vigencia_inicio` preenchida.
6. Push do código → CI verde → deploy automático no Render.

---

## 3. Preço no Catálogo (Req 3)

### 3.1 API

| Método e rota | Corpo / parâmetros | Resposta | Limite |
|---|---|---|---|
| `GET /api/clientes/{cliente_id}/itens` | `incluir_inativos` | `ItemResposta[]` com `preco_atual` | — |
| `POST /api/clientes/{cliente_id}/itens` | `{ nome, valor_unitario }` (ambos obrigatórios) | `ItemResposta` 201 | 60/min |
| `PATCH /api/itens/{item_id}` | `{ nome }` (renomear, como hoje) | `ItemResposta` | 60/min |
| `PUT /api/itens/{item_id}/preco` | `{ valor_unitario, modo: "a_partir_de_hoje" \| "corrigir_atual" }` | `PrecoAtual` | 60/min |
| `GET /api/itens/{item_id}/preco/impacto` | `modo` | `{ pedidos_com_valor_anterior: int }` | — |
| `GET /api/clientes/{cliente_id}/precos` | `data` (YYYY-MM-DD, obrigatória) | `PrecosNaData` — usado pelo formulário de lançamento | — |

- `PrecoAtual = { valor_unitario: "4.50", desde: "2026-10-02", e_hoje: bool }`.
  `e_hoje` permite à interface oferecer só uma ação quando o preço atual começou
  hoje (Req 1.14).
- `ItemResposta.preco_atual: PrecoAtual | null` — `null` = sem preço (Req 3.5).
  Resolvido em **uma** consulta para todos os itens da lista (`listar_na_data(hoje)`).
- Dinheiro como texto decimal, como na v1. `valor_unitario` validado por Pydantic
  (`gt=0, decimal_places=2`) e pelo serviço.
- Removidos: `GET .../precos?mes=`, `PUT .../precos`, `GET .../precos/vigencia-sugerida/{item}`.
- Rate limit nas escritas de item e preço: hoje elas **não têm** limite (encontrado no
  levantamento), contrariando `engineering.md` §4. Corrigido aqui.

### 3.2 Atomicidade (Req 3.3)

`ServicoCatalogo.criar_item_com_preco(cliente, nome, valor)` orquestra `ServicoItem.criar`
e `ServicoPreco.definir_primeiro` na **mesma sessão**. A sessão por requisição
(`core/banco.py`, `obter_sessao`) já faz `commit` no fim e `rollback` em exceção, então
falha no preço desfaz o item. Teste: forçar valor inválido e exigir que o item não
exista.

`ServicoItem` continua sem depender de preço (responsabilidade única); a orquestração
fica num serviço novo e fino.

### 3.3 Interface

- `FormularioItem` passa a ter **Nome** e **Preço por peça (R$)**.
  - Criar: os dois obrigatórios. Botão "Criar item".
  - Editar: nome e preço juntos. Se o preço mudou e `e_hoje` for falso, aparece a
    escolha (rádio), com textos simples:
    - **Mudar a partir de hoje** — "Pedidos de hoje em diante usam o novo preço.
      Pedidos anteriores continuam com o preço antigo."
    - **Corrigir o preço atual** — "Use se o preço foi digitado errado. Vale desde
      {dd/mm/aaaa}."
  - Antes de confirmar, chama `impacto` e, se > 0, mostra: "{n} pedidos já
    registrados continuam com {valor anterior}. Para mudar esses pedidos, edite cada
    um." (Req 1.6, 1.13).
  - Entrada de dinheiro aceita vírgula; conversão para texto decimal **sem** passar
    por `Number` (hoje `FormularioPreco` usa `Number(...).toFixed(2)`, ponto flutuante).
    Utilitário em `lib/dinheiro.ts`, com teste.
- `CartaoGestao` ganha linha de preço: "R$ 4,50 por peça". Sem preço: badge "Sem
  preço" (tom de alerta, não erro) e ação "Definir preço" no rodapé. Medir o rodapé
  de novo nas larguras de teste (skill `design-de-interface` §5).
- Tela de Preços removida: `features/precos/` (tela, formulário, CSS) apagado;
  `pages/Precos.tsx` removida; `App.tsx` troca a rota por `<Navigate to="/catalogo" replace />`;
  item "Preços" sai de `Sidebar.tsx` (`ITENS_NAV`).
- O hook de preços usado pelo lançamento (`usePrecosDoMes`) vira `usePrecosNaData(clienteId, data)`
  em `features/catalogo/hooks.ts`.

---

## 4. Textos (Req 4)

Inventário levantado (arquivo:linha no levantamento de 02/10). Mudanças:

| Onde | Hoje | Passa a ser |
|---|---|---|
| Lançamento, título da seção | "Peças do pedido · preços de outubro/2026" | "Peças do pedido" (o preço por peça aparece em cada linha) |
| Lançamento, linha | "Sem preço neste mês" | "Sem preço" |
| Lançamento, aviso | "Sem preço para o mês desta data. Defina o preço em Preços antes de salvar." | "Este item ainda não tem preço. Defina o preço no Catálogo para salvar o pedido." |
| API `itens_sem_preco` (`core/erros.py`) | "...não tem preço cadastrado para setembro/2026." | "Não foi possível salvar: {item} ainda não tem preço. Defina o preço no Catálogo." |
| Catálogo, subtítulo | "Tipos de peça que cada cliente envia, cobrados por peça." | "Tipos de peça que cada cliente envia e o preço de cada uma. O preço vale até você mudar." |
| Formulário de item | — | Ajuda do campo preço: "O preço vale a partir de hoje e continua valendo até você mudar." |

- `ITENS_SEM_PRECO` deixa de enviar `mes_referencia` em `detalhes`; `itens` continua
  (o frontend usa para marcar as linhas). Ajustar `logica.test.ts` e `api.test.ts`.
- Revisão final: busca por "vigência", "vigente", "mês" em `frontend/src` e nas
  mensagens de `backend/app` exibidas ao operador.

---

## 5. Relatório geral (Req 5)

### 5.1 Domínio (`app/dominio.py`)

```python
LinhaResumoItem(item_id, item_nome, valor_unitario: Decimal, quantidade: int, subtotal: Decimal)
SecaoDoCliente(cliente_id, cliente_nome, linhas: tuple[LinhaResumoItem, ...],
               total_pecas: int, total_valor: Decimal)
RelatorioGeral(inicio, fim, secoes: tuple[SecaoDoCliente, ...],
               total_pecas: int, total_valor: Decimal)
```

O mesmo `LinhaResumoItem` alimenta o **resumo por item** do relatório por cliente
(Req 6.4): `Relatorio` ganha `resumo_por_item: tuple[LinhaResumoItem, ...]`, derivado
das `LinhaDeFechamento` que o serviço já carrega (sem consulta nova).

### 5.2 Consulta (repositório)

`RepositorioLancamento.buscar_resumo_geral(inicio, fim)` — uma consulta agrupada:

```sql
SELECT c.id, c.nome, i.id, i.nome, l.valor_unitario_congelado,
       sum(l.quantidade), sum(l.total)
FROM lancamentos la
JOIN lancamento_linhas l ON l.lancamento_id = la.id
JOIN itens i ON i.id = l.item_id
JOIN clientes c ON c.id = la.cliente_id
WHERE la.data BETWEEN :inicio AND :fim
GROUP BY c.id, c.nome, i.id, i.nome, l.valor_unitario_congelado
```

- Cliente inativo com pedido aparece; cliente sem pedido não aparece (Req 5.5) —
  consequência natural do `JOIN`.
- Item com dois valores no período: duas linhas (Req 5.4).
- Ordenação no serviço com a mesma chave sem acento já usada (`_chave_alfabetica`).
- Totais somados no serviço em `Decimal` a partir das somas agrupadas.

### 5.3 API

`GET /api/relatorio/geral`, `GET /api/relatorio/geral/pdf`, `GET /api/relatorio/geral/excel`
— parâmetros `inicio`, `fim`; autenticação do router; 30/min nas exportações (Req 5.9).
Rotas separadas em vez de `cliente_id` opcional: o formato da resposta é outro e
contratos distintos evitam ambiguidade. Nome do arquivo:
`fechamento-todos-os-clientes-{inicio}-a-{fim}.{ext}`.

### 5.4 Interface

- `Selecao` de cliente na tela de relatório ganha a primeira opção "Todos os clientes"
  (`?cliente=todos` na URL).
- Componente `RelatorioGeral` na feature de relatório: uma seção por cliente (tabela
  item · peças · por peça · subtotal), total do cliente, e cartão de total geral.
  Reusa `Pagina.module.css` e `TabelaDados`.
- Exportar PDF/Excel chama as rotas `/geral/*`.
- Estado vazio: "Nenhum pedido no período escolhido."

### 5.5 Exportação

- PDF: um bloco por cliente; cabeçalho de seção com o nome; quebra de página só se o
  bloco não couber (`KeepTogether` para blocos pequenos). Termina com o bloco
  "Total geral" (cliente · peças · total R$, como a aba "Resumo"), sem forçar
  página nova.
- Excel: aba "Resumo" (cliente, peças, total R$, mais o total geral) e uma aba por
  cliente. Nome de aba: até 31 caracteres, sem `[]:*?/\`, com sufixo numérico se
  repetir.

### 5.6 Paridade (Req 5.7)

- Tela = PDF = Excel, como na v1.
- Prova cruzada: total geral = soma dos totais do relatório por cliente de cada
  cliente no mesmo período.

---

## 6. PDF (Req 6)

### 6.1 Organização do módulo

`exports/pdf.py` (uma função de ~200 linhas) vira o pacote `exports/pdf/`:

| Arquivo | Responsabilidade |
|---|---|
| `estilo.py` | Cores, fontes, tamanhos, `formatar_moeda`. |
| `marca.py` | Logo com proporção real. |
| `pagina.py` | Moldura de página: cabeçalho, rodapé "Página X de Y". |
| `colunas.py` | Cálculo de larguras (função pura, testável). |
| `fechamento.py` | `gerar_pdf(relatorio)` — por cliente. |
| `geral.py` | `gerar_pdf_geral(relatorio_geral)`. |

`gerar_pdf` mantém a assinatura, para os testes de paridade existentes continuarem
valendo.

### 6.2 Logo (Req 6.1)

- Hoje: `Image(lavandix-marca.png, width=110, height=28)` sobre um arquivo de
  348×300 px → achatado.
- Novo asset: gerado **uma vez** a partir de `assets/marca/lavandix-marca-original.png`
  (861×742 px), recortando a margem transparente com Pillow (já presente como
  dependência do reportlab). O PNG resultante é versionado em `exports/assets/`.
- Desenho: largura fixa (**80 pt**; 120 pt deixava o cabeçalho com ~1/5 da página,
  porque o emblema é quase quadrado), altura = largura × (altura/largura reais),
  lidas do arquivo. Nada de proporção fixa no código.
- **A verificar:** se o original contém só a marca ou também texto/fundo; ver a
  imagem antes de recortar.

### 6.3 Tabela por dia (Req 6.2, 6.3, 6.5)

- Larguras: cada coluna de item com largura natural (maior texto entre título e
  valores, medido com `stringWidth`) + padding, limitada a **48–96 pt**. Data e
  Comanda com largura natural. Se sobrar espaço, a tabela **não estica**: fica com
  a largura natural, alinhada à esquerda. Função pura em `colunas.py`, com teste.
- Quando não cabe (muitos itens; 18 itens × 48 pt já passam da página): todas as
  colunas encolhem por igual até a largura mínima de cada uma, que é a maior
  **palavra** do título ou o maior valor; o título quebra entre palavras, nunca
  no meio. O padding lateral também diminui com a fonte. Só se nem isso couber,
  os itens encolhem além da mínima.
- Alinhamento: Data e Comanda à esquerda (título e valor), números à direita (título
  e valor).
- `repeatRows=1`: cabeçalho da tabela repetido em cada página.
- Degradação de fonte com muitos itens: mantida.

### 6.4 Resumo por item e moldura

- Após a tabela por dia: bloco "Resumo por item" — item · por peça · peças ·
  subtotal (mesma ordem da tela e do Excel geral), e o total. Consome
  `relatorio.resumo_por_item` (nada recalculado).
- Rodapé em todas as páginas: "Página X de Y" à direita, "Lavandix · Relação de
  valores" à esquerda. "de Y" exige duas passadas: canvas que guarda os estados de
  página e escreve o total no fim (padrão documentado do reportlab — **conferir a
  documentação da versão 5.0.1 em uso**).

### 6.5 Verificação

- Testes: PDF válido; texto extraído (`pypdf`, já em `requirements-dev.txt`) contém
  "Página 1 de", o resumo por item e os totais; larguras calculadas dentro dos
  limites para 1, 3 e 20 itens.
- Visual: gerar PDF com dados do `lavconta_dev` (poucos itens, muitos itens, várias
  páginas) e conferir a imagem renderizada antes de declarar pronto.

---

## 7. Testes prioritários

| Área | Casos |
|---|---|
| Resolução | véspera / dia / dia seguinte a uma mudança; primeiro preço vale para trás; item sem nenhum preço; isolamento entre clientes |
| Escrita | duas mudanças no mesmo dia = uma linha; corrigir atual altera só o vigente; corrigir sem preço → erro; data de início vinda do cliente é ignorada |
| Congelamento | mudar e corrigir não alteram pedido gravado; pedido retroativo novo usa o preço da sua data; impacto conta certo |
| Constraint | `uq_precos_cliente_item_inicio` recusa duplicata (violar e exigir recusa) |
| Migração | upgrade preserva contagem e valores; `vigencia_inicio = vigencia_mes`; downgrade funciona antes de uso |
| Catálogo | criar item com preço inválido não cria item; listagem traz `preco_atual` em uma consulta |
| Relatório geral | inativo com pedido aparece; sem pedido não aparece; dois valores = duas linhas; paridade tela/PDF/Excel; total geral = soma dos por cliente |
| PDF | larguras; "Página X de Y"; resumo por item |
| Frontend | conversão de dinheiro sem float; textos sem "vigência"/"mês" (busca) |
| Rate limit | escritas de item e preço respondem 429 acima do limite |

Testes da v1 que deixam de valer (mês, vigência sugerida, dia 1) são **reescritos**
para a regra nova, não apagados sem substituto. `RepositorioPrecoFalso` acompanha o
protocolo novo.

---

## 8. Seed de desenvolvimento

`scripts_dev/preparar_banco.py` usa `definir(..., JUNHO)`. Passa a criar preços com
relógio fixo (o `hoje` injetado do §1.3) para gerar histórico: preço inicial em
junho e reajuste do "Lençol" do Hotel Aurora em 15/09 (meio do mês, para exercitar
a regra nova). Mantém o "Edredom" sem preço.

---

## 9. Riscos

| Risco | Mitigação |
|---|---|
| Migração em banco com dados reais | Expand/contract, `pg_dump` antes, ensaio no dev, contagem antes/depois |
| Código antigo grava preço na janela de deploy | Não editar preços na janela (usuário único) |
| Preço futuro legado | Consulta do §1.5 antes de migrar |
| Remoção de rotas usadas por algum cliente HTTP | Único consumidor é o frontend, publicado junto |
| Regressão visual nos cartões com a linha de preço | Medição nas larguras de teste |
